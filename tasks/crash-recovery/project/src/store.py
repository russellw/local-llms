"""The state a journal rebuilds. See SPEC.md."""


class Checkpoint:
    def __init__(self, state=None, lsn=0):
        self.state = dict(state or {})
        self.lsn = lsn

    def __repr__(self):
        return f"Checkpoint(lsn={self.lsn}, state={self.state})"


def apply_record(state, key, delta):
    """Add `delta` to `key`'s running total."""
    state[key] = state.get(key, 0) + delta
