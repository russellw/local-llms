The `LRUCache` class below is meant to be a fixed-capacity cache that evicts
the **least recently used** entry when it is full. It has several bugs.

```python
class LRUCache:
    def __init__(self, capacity):
        self.capacity = capacity
        self.data = {}
        self.order = []

    def get(self, key, default=None):
        if key not in self.data:
            return default
        return self.data[key]

    def put(self, key, value):
        if len(self.data) >= self.capacity:
            oldest = self.order[-1]
            del self.data[oldest]
            self.order.remove(oldest)
        self.data[key] = value
        self.order.append(key)

    def __len__(self):
        return len(self.data)
```

Fix it. The corrected class must satisfy all of the following:

- `get(key)` returns the stored value and counts as a **use**, making that key
  the most recently used. Missing keys return `default` and do not change
  recency.
- `put(key, value)` on a key that is already present updates the value and
  marks it most recently used, without growing the cache and without evicting
  anything.
- Eviction removes the least recently used key, and only happens when inserting
  a *new* key into a cache that is already at capacity.
- `len(cache)` never exceeds `capacity`.
- A `capacity` of 0 or less raises `ValueError` from `__init__`.

Keep the class name `LRUCache` and the method signatures unchanged. Reply with
the complete corrected class.
