"""A key-value store kept in files. See docs/design.md."""

from .layout import MANIFEST, MANIFEST_TMP, data_name, decode_manifest, encode_manifest


class Store:
    """The manifest is the store: it names the file holding each key's value,
    and replacing it with a rename is the one step that switches from the old
    contents to the new. Everything it names is made durable before it is
    renamed into place, and nothing the old one names is removed until the
    rename itself is durable.
    """

    def __init__(self, fs, generation, files):
        self._fs = fs
        self._generation = generation
        self._files = files      # key -> data file name

    @classmethod
    def open(cls, fs):
        if fs.exists(MANIFEST):
            generation, files = decode_manifest(fs.read(MANIFEST))
        else:
            generation, files = 0, {}
        # Anything else is left over from a commit that never took effect.
        # Removing it is safe at any point: nothing current refers to it.
        keep = set(files.values()) | {MANIFEST}
        stale = [name for name in fs.listdir() if name not in keep]
        for name in stale:
            fs.remove(name)
        if stale:
            fs.fsync_dir()
        return cls(fs, generation, files)

    def get(self, key):
        name = self._files.get(key)
        return None if name is None else self._fs.read(name).decode("utf-8")

    def keys(self):
        return sorted(self._files)

    def commit(self, changes):
        """Apply `changes`: a string sets a key, None deletes it."""
        fs = self._fs
        generation = self._generation + 1
        files = dict(self._files)
        for key, value in changes.items():
            if value is None:
                files.pop(key, None)
                continue
            name = data_name(key, generation)
            fs.write(name, value.encode("utf-8"))
            # Before the manifest that names it can survive: otherwise a
            # power loss can keep the name and lose the contents.
            fs.fsync(name)
            files[key] = name

        fs.write(MANIFEST_TMP, encode_manifest(generation, files))
        fs.fsync(MANIFEST_TMP)
        fs.rename(MANIFEST_TMP, MANIFEST)
        # Until this, the rename may not survive; the commit is not done.
        fs.fsync_dir()

        # Only now can the old files go: before the rename was durable, a
        # power loss could bring back the old manifest without them.
        old = set(self._files.values()) - set(files.values())
        for name in sorted(old):
            fs.remove(name)

        self._generation = generation
        self._files = files
