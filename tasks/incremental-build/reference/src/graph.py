"""Declaring targets. See docs/design.md."""


class BuildError(Exception):
    """The graph cannot be built as declared."""


class Target:
    def __init__(self, name, deps, recipe, version):
        self.name = name
        self.deps = list(deps)
        self.recipe = recipe
        self.version = version

    def __repr__(self):
        return f"Target({self.name!r}, deps={self.deps!r}, version={self.version})"


class Graph:
    def __init__(self):
        # A dict keeps insertion order, which is declaration order.
        self.targets = {}

    def add(self, name, deps=(), recipe=None, version=1):
        if name in self.targets:
            raise BuildError(f"{name} is declared twice")
        self.targets[name] = Target(name, deps, recipe, version)
        return self.targets[name]
