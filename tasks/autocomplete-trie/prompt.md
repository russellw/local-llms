Implement a class `Autocomplete` backed by a prefix tree (trie):

```python
class Autocomplete:
    def add(self, word: str, weight: int = 1) -> None
    def suggest(self, prefix: str, k: int = 5) -> list[str]
    def __len__(self) -> int
```

- `add` inserts `word` with the given weight. Adding a word that is already
  present **replaces** its weight rather than adding a duplicate entry.
  Adding the empty string is a no-op.
- `suggest` returns up to `k` words that start with `prefix`, ordered by weight
  descending; words with equal weight are ordered lexicographically ascending.
  A word counts as a prefix of itself, so `suggest("cat")` may return `"cat"`.
  An empty prefix matches every word. If `k` is 0 or negative, return an empty
  list. Matching is case-sensitive.
- `__len__` returns the number of distinct words stored.

Build an actual trie: `suggest` must walk the tree down to the prefix node and
then explore only that subtree. Do not keep a flat list of all words and filter
it with `startswith` — a lookup for a rare prefix in a large dictionary must
not touch unrelated words.
