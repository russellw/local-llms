from collections import OrderedDict

_MISSING = object()


class LRUCache:
    def __init__(self, capacity):
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self.capacity = capacity
        self.data = OrderedDict()

    def get(self, key, default=None):
        value = self.data.get(key, _MISSING)
        if value is _MISSING:
            return default
        self.data.move_to_end(key)
        return value

    def put(self, key, value):
        if key in self.data:
            self.data[key] = value
            self.data.move_to_end(key)
            return
        if len(self.data) >= self.capacity:
            self.data.popitem(last=False)
        self.data[key] = value

    def __len__(self):
        return len(self.data)
