"""A key-value store kept in files. See docs/design.md."""

from .layout import data_name, key_of


class Store:
    def __init__(self, fs, data):
        self._fs = fs
        self._data = data

    @classmethod
    def open(cls, fs):
        data = {}
        for name in fs.listdir():
            key = key_of(name)
            if key is not None:
                data[key] = fs.read(name).decode("utf-8")
        return cls(fs, data)

    def get(self, key):
        return self._data[key]

    def keys(self):
        return sorted(self._data)

    def commit(self, changes):
        """Apply `changes`: a string sets a key, None deletes it."""
        for key, value in changes.items():
            if value is None:
                self._data.pop(key, None)
                continue
            name = data_name(key)
            self._fs.write(name, value.encode("utf-8"))
            self._fs.fsync(name)
            self._data[key] = value
