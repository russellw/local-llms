"""Running a build. See docs/design.md."""

from .fingerprint import digest, fingerprint
from .plan import check, order, wanted


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
    names = wanted(graph, goal)
    # Both checks before any recipe runs: a missing dependency found halfway
    # through would leave half a build behind.
    check(graph, names, sources)
    names = order(graph, names)

    report = Report()
    bad = set()
    for name in names:
        target = graph.targets[name]
        if any(d in bad for d in target.deps):
            report.blocked.append(name)
            bad.add(name)
            continue
        # Computed here, not up front: a dependency that ran earlier in this
        # build has new bytes, and the fingerprint has to see them. Comparing
        # contents is also what lets a dependency that ran but came out the
        # same leave this target up to date.
        fp = fingerprint(target, {d: _hash_of(d, sources, store) for d in target.deps})
        rec = store.get(name)
        if rec is not None and rec.fingerprint == fp:
            report.up_to_date.append(name)
            continue
        inputs = {d: _value_of(d, sources, store) for d in target.deps}
        try:
            output = target.recipe(inputs)
        except Exception:
            # Carry on: only what depends on this is blocked.
            report.failed.append(name)
            bad.add(name)
            continue
        store.put(name, fp, output)
        report.ran.append(name)
    return report
