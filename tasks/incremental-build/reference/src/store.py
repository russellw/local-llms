"""What the last build left behind. See docs/design.md."""

from .fingerprint import digest


class Record:
    def __init__(self, fingerprint, output):
        self.fingerprint = fingerprint
        self.output = output
        self.output_hash = digest(output)


class Store:
    def __init__(self):
        self._records = {}

    def get(self, name):
        """The record of `name`'s last successful run, or None."""
        return self._records.get(name)

    def put(self, name, fingerprint, output):
        self._records[name] = Record(fingerprint, output)

    def output(self, name):
        rec = self._records.get(name)
        return rec.output if rec else None
