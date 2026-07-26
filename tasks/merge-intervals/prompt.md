Write a function:

```python
def merge_intervals(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]
```

Each input tuple `(start, end)` is a **closed** interval with `start <= end`.
The input list is not necessarily sorted and may be empty.

Merge every group of intervals that overlap or touch, and return the merged
intervals as a list of tuples sorted by start. Touching counts as overlapping:
`(1, 3)` and `(3, 5)` merge into `(1, 5)`, and so do `(1, 3)` and `(4, 6)` —
because the closed intervals `[1,3]` and `[4,6]` cover adjacent integers with
no gap between them, they merge into `(1, 6)`. Two intervals only stay separate
if at least one integer lies strictly between them.

Return a list of `tuple` objects, not lists. Do not modify the input list.
