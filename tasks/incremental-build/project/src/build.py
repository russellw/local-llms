"""Running a build. See docs/design.md."""

from .fingerprint import digest, fingerprint
from .plan import order, wanted


class Report:
    """What happened to each target a build involved."""

    def __init__(self):
        self.ran = []
        self.up_to_date = []
        self.failed = []
        self.blocked = []

    def __repr__(self):
        return (f"Report(ran={self.ran}, up_to_date={self.up_to_date}, "
                f"failed={self.failed}, blocked={self.blocked})")


def _hash_of(name, sources, store):
    if name in sources:
        return digest(sources[name])
    rec = store.get(name)
    return rec.output_hash if rec else None


def _value_of(name, sources, store):
    if name in sources:
        return sources[name]
    return store.get(name).output


def build(graph, sources, store, goal=None):
    """Bring the targets of `graph` up to date. Returns a Report."""
    names = order(graph, wanted(graph, goal))
    prints = {
        name: fingerprint(
            graph.targets[name],
            {d: _hash_of(d, sources, store) for d in graph.targets[name].deps},
        )
        for name in names
    }

    report = Report()
    rebuilt = set()
    for name in names:
        target = graph.targets[name]
        rec = store.get(name)
        if (rec is not None and rec.fingerprint == prints[name]
                and not any(d in rebuilt for d in target.deps)):
            report.up_to_date.append(name)
            continue
        inputs = {d: _value_of(d, sources, store) for d in target.deps}
        try:
            output = target.recipe(inputs)
        except Exception:
            report.failed.append(name)
            break
        store.put(name, prints[name], output)
        rebuilt.add(name)
        report.ran.append(name)
    return report
