The `MinHeap` class below is meant to be an array-backed binary min-heap. It is
buggy: `push` sometimes leaves the heap out of order, and `pop` is worse.

```python
class MinHeap:
    def __init__(self):
        self.items = []

    def push(self, value):
        self.items.append(value)
        i = len(self.items) - 1
        parent = i // 2
        if self.items[i] < self.items[parent]:
            self.items[i], self.items[parent] = self.items[parent], self.items[i]

    def pop(self):
        top = self.items[0]
        self.items[0] = self.items[-1]
        i = 0
        while 2 * i + 1 < len(self.items):
            child = 2 * i + 1
            self.items[i], self.items[child] = self.items[child], self.items[i]
            i = child
        return top

    def peek(self):
        return self.items[0]

    def __len__(self):
        return len(self.items)
```

Fix it so that:

- `push(value)` sifts the new element all the way up to its correct position.
- `pop()` removes and returns the smallest element, restores the heap property
  by sifting down through the *smaller* child, and shrinks the heap by one.
- `peek()` returns the smallest element without removing it.
- `pop()` and `peek()` on an empty heap raise `IndexError`.
- Both operations are O(log n) — do not fix this by sorting the list.

Keep the class name `MinHeap`, the attribute name `items`, and the method
signatures unchanged. Reply with the complete corrected class.
