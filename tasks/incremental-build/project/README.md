# pybuild

A small incremental build tool. Declare targets on a graph, each with the
names it depends on and a recipe that turns their bytes into its own; `build`
runs whatever is out of date and keeps the results in a store, so the next
build can skip what has not changed.

```python
from src.graph import Graph
from src.store import Store
from src.build import build

g = Graph()
g.add("upper", deps=["greeting"], recipe=lambda i: i["greeting"].upper())
g.add("banner", deps=["upper"], recipe=lambda i: b"** " + i["upper"] + b" **")

store = Store()
report = build(g, {"greeting": b"hello"}, store)
print(report.ran)               # ['upper', 'banner']
print(store.output("banner"))   # b'** HELLO **'
```

Layout:

- `src/graph.py` -- declaring targets
- `src/plan.py` -- deciding what a build involves, and in what order
- `src/fingerprint.py` -- content hashes and fingerprints
- `src/store.py` -- what the last build left behind
- `src/build.py` -- running a build
- `docs/design.md` -- how it is meant to behave
