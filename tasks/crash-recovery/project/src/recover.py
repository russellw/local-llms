"""Rebuilding state after a crash. See SPEC.md."""

from .codec import decode_records
from .store import apply_record


def recover(checkpoint, blob):
    """The state to come back up with, from a checkpoint and a journal."""
    state = checkpoint.state
    for lsn, key, delta in decode_records(blob):
        if lsn < checkpoint.lsn:
            continue
        apply_record(state, key, delta)
    return state
