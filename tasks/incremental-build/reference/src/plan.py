"""What a build involves, and in what order. See docs/design.md."""

from .graph import BuildError


def wanted(graph, goal=None):
    """The targets a build of `goal` involves: every target when there is none."""
    if goal is None:
        return list(graph.targets)
    if goal not in graph.targets:
        raise BuildError(f"no target named {goal}")
    # Everything the goal depends on through other targets, not just its
    # direct dependencies.
    seen = set()
    stack = [goal]
    while stack:
        name = stack.pop()
        if name in seen:
            continue
        seen.add(name)
        stack.extend(d for d in graph.targets[name].deps if d in graph.targets)
    return [name for name in graph.targets if name in seen]


def check(graph, names, sources):
    """Raise BuildError if `names` cannot be built, before anything runs."""
    for name in names:
        for dep in graph.targets[name].deps:
            if dep not in graph.targets and dep not in sources:
                raise BuildError(f"{name} depends on {dep}, which is neither a target nor a source")


def order(graph, names):
    """`names`, arranged so that every target comes after its dependencies.

    At each step, the earliest-declared target whose dependencies are all dealt
    with. Not a depth-first walk: that puts a dependency's dependents straight
    after it, ahead of targets that were declared earlier.
    """
    names = set(names)
    pending = [name for name in graph.targets if name in names]
    done, out = set(), []
    while pending:
        for i, name in enumerate(pending):
            if all(d in done or d not in names for d in graph.targets[name].deps):
                break
        else:
            raise BuildError("dependency cycle among " + ", ".join(pending))
        pending.pop(i)
        done.add(name)
        out.append(name)
    return out
