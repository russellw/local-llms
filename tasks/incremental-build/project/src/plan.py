"""What a build involves, and in what order. See docs/design.md."""

from .graph import BuildError


def wanted(graph, goal=None):
    """The targets a build of `goal` involves: every target when there is none."""
    if goal is None:
        return list(graph.targets)
    if goal not in graph.targets:
        raise BuildError(f"no target named {goal}")
    return [d for d in graph.targets[goal].deps if d in graph.targets] + [goal]


def order(graph, names):
    """`names`, arranged so that every target comes after its dependencies."""
    names = set(names)
    done, visiting, out = set(), set(), []

    def visit(name):
        if name in done:
            return
        if name in visiting:
            raise BuildError(f"dependency cycle through {name}")
        visiting.add(name)
        for dep in sorted(graph.targets[name].deps):
            if dep in names:
                visit(dep)
        visiting.discard(name)
        done.add(name)
        out.append(name)

    for name in sorted(names):
        visit(name)
    return out
