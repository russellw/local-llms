Write a function:

```python
def insert_position(seq, x, side: str = "left") -> int
```

`seq` is a sequence sorted in non-decreasing order. Return the index at which
`x` should be inserted to keep `seq` sorted.

- With `side="left"`, return the **lowest** such index — every element before
  the returned index is strictly less than `x`.
- With `side="right"`, return the **highest** such index — every element before
  the returned index is less than or equal to `x`.
- Any other value of `side` raises `ValueError`.

Requirements:

- Your function must run in O(log n) time. It may only access `seq` through
  `len(seq)` and integer indexing `seq[i]`. It must not iterate over `seq`,
  call `list(seq)`, slice it, or use the `bisect` module — the sequence passed
  in is a lazy object where indexing is the only supported operation and a
  linear scan of a large sequence will be detected and rejected.
- Handle the empty sequence, and values below or above every element.
