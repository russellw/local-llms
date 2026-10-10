"""An in-memory filesystem that can lose power.

Files live in one flat directory. A name is a non-empty string with no "/" in
it. Reads see every change made so far, exactly as you would expect. What is
not as you might expect is what is left after a power loss:

- A file's contents survive as of its last `fsync`. Anything written since
  may come back as the old contents, the new contents, or a mixture of the
  two. A file that has never been fsynced has, as its old contents, nothing.
- Writing to a name that already exists changes that file's contents in
  place. It does not create a new file.
- Creating a file, `rename` and `remove` are changes to the directory. The
  directory survives as of the last `fsync_dir`. Of the changes made since
  then, any number may survive, but always the earliest ones: if a later
  change survived, every change before it did too. A `rename` is a single
  change, never half done, and it replaces the target if there is one.
- `fsync(name)` makes a file's contents survive. It does not make the file's
  name survive; only `fsync_dir` does that.

`after_power_loss` and `power_loss_outcomes` are how a caller finds out what a
power loss would leave behind. `fail_after` makes a later change fail as if
the power went out at that moment.
"""

class PowerLoss(Exception):
    """The power went out. Nothing after this point happened."""


class _File:
    def __init__(self):
        self.current = b""
        self.durable = b""


class FakeFS:
    def __init__(self):
        self._names = {}      # name -> _File, as reads see it
        self._durable = {}    # name -> _File, as of the last fsync_dir
        self._pending = []    # directory changes since the last fsync_dir
        self._changes = 0
        self._fail_at = None
        self.bytes_written = 0

    # -- reading ---------------------------------------------------------

    def listdir(self):
        return sorted(self._names)

    def exists(self, name):
        return name in self._names

    def read(self, name):
        if name not in self._names:
            raise FileNotFoundError(name)
        return self._names[name].current

    # -- changing --------------------------------------------------------

    def _change(self):
        if self._fail_at is not None and self._changes >= self._fail_at:
            raise PowerLoss(f"power lost at change {self._changes}")
        self._changes += 1

    @staticmethod
    def _check(name):
        if not isinstance(name, str) or not name or "/" in name:
            raise ValueError(f"bad file name {name!r}")

    def write(self, name, data):
        """Replace the contents of `name`, creating it if it does not exist."""
        self._check(name)
        self._change()
        f = self._names.get(name)
        if f is None:
            f = _File()
            self._names[name] = f
            self._pending.append(("link", name, f))
        f.current = bytes(data)
        self.bytes_written += len(data)

    def fsync(self, name):
        if name not in self._names:
            raise FileNotFoundError(name)
        self._change()
        f = self._names[name]
        f.durable = f.current

    def rename(self, src, dst):
        self._check(dst)
        if src not in self._names:
            raise FileNotFoundError(src)
        self._change()
        f = self._names.pop(src)
        self._names[dst] = f
        self._pending.append(("rename", src, dst, f))

    def remove(self, name):
        if name not in self._names:
            raise FileNotFoundError(name)
        self._change()
        del self._names[name]
        self._pending.append(("unlink", name))

    def fsync_dir(self):
        self._change()
        self._durable = dict(self._names)
        self._pending = []

    # -- losing power ----------------------------------------------------

    def fail_after(self, n):
        """Let `n` more changes happen; the one after that raises PowerLoss."""
        self._fail_at = self._changes + n

    def after_power_loss(self, survived=0, contents="old"):
        """The filesystem as it comes back after a power loss now.

        `survived` is how many of the directory changes since the last
        fsync_dir survived. `contents` is what files written since their last
        fsync hold: "old", "new", or "mixed".
        """
        names = dict(self._durable)
        for change in self._pending[:survived]:
            if change[0] == "link":
                names[change[1]] = change[2]
            elif change[0] == "rename":
                names.pop(change[1], None)
                names[change[2]] = change[3]
            else:
                names.pop(change[1], None)
        out = FakeFS()
        for name, f in names.items():
            g = _File()
            if f.current == f.durable:
                g.current = f.current
            elif contents == "old":
                g.current = f.durable
            elif contents == "new":
                g.current = f.current
            else:
                g.current = f.current[:len(f.current) // 2] + f.durable[len(f.current) // 2:]
            g.durable = g.current
            out._names[name] = g
        out._durable = dict(out._names)
        return out

    def power_loss_outcomes(self):
        """Every filesystem a power loss now could leave behind."""
        return [
            self.after_power_loss(survived, contents)
            for survived in range(len(self._pending) + 1)
            for contents in ("old", "new", "mixed")
        ]
