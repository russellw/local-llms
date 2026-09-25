"""Rebuilding state after a crash. See SPEC.md."""

from .codec import decode_records
from .store import apply_record


def recover(checkpoint, blob):
    """The state to come back up with, from a checkpoint and a journal."""
    # A copy: recovering must not mutate the checkpoint, and must give the
    # same answer when run again from the same one.
    state = dict(checkpoint.state)
    for lsn, key, delta in decode_records(blob):
        # The record *at* the checkpoint's lsn is already in the snapshot.
        # Applying is not idempotent, so replaying it silently doubles it.
        if lsn <= checkpoint.lsn:
            continue
        apply_record(state, key, delta)
    return state
