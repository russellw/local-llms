"""Appending to the journal. See SPEC.md."""

from .codec import encode_record


class Journal:
    def __init__(self):
        self._buf = bytearray()
        self._last_lsn = 0

    @property
    def bytes(self):
        return bytes(self._buf)

    def append(self, key, delta):
        """Write one record. Returns the lsn it was given."""
        self._last_lsn += 1
        self._buf += encode_record(self._last_lsn, key, delta)
        return self._last_lsn
