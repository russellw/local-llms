# kvstore

A small key-value store that keeps its data in files and is meant to survive
the power going out.

```python
from src.fs import FakeFS
from src.store import Store

fs = FakeFS()
store = Store.open(fs)
store.commit({"colour": "blue", "size": "large"})
store.commit({"size": None})          # None deletes a key

store = Store.open(fs)
print(store.get("colour"))            # blue
print(store.keys())                   # ['colour']
```

Layout:

- `src/fs.py` -- the filesystem, including what survives a power loss
- `src/layout.py` -- how keys map to file names
- `src/store.py` -- the store
- `docs/design.md` -- how the store is meant to behave
