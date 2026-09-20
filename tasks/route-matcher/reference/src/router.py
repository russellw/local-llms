"""A URL router. See SPEC.md for the matching rules."""

from .pattern import STATIC, PARAM, WILD, compile_pattern, split_path

# Lower is more specific. Compared segment by segment, left to right.
_RANK = {STATIC: 0, PARAM: 1, WILD: 2}


class Route:
    def __init__(self, pattern, handler, order):
        self.pattern = pattern
        self.segments = compile_pattern(pattern)
        self.handler = handler
        self.order = order

    @property
    def specificity(self):
        return tuple(_RANK[s.kind] for s in self.segments)


class Router:
    def __init__(self):
        self.routes = []

    def add(self, pattern, handler):
        self.routes.append(Route(pattern, handler, len(self.routes)))

    def match(self, path):
        """Return (handler, params) for the best matching route, or None.

        Every route is tried, not just the first that fits: registration order
        decides nothing except ties between patterns of equal specificity.
        """
        parts = split_path(path)
        best = None
        for route in self.routes:
            params = _try(route, parts)
            if params is None:
                continue
            key = (route.specificity, route.order)
            if best is None or key < best[0]:
                best = (key, route, params)
        if best is None:
            return None
        return best[1].handler, best[2]


def _try(route, parts):
    """Match one route against the path segments, returning captures or None."""
    params = {}
    for i, seg in enumerate(route.segments):
        if seg.kind == WILD:
            # Swallows everything left, including nothing at all.
            params[seg.text] = "/".join(parts[i:])
            return params
        if i >= len(parts):
            return None
        if seg.kind == STATIC:
            if parts[i] != seg.text:
                return None
        else:
            params[seg.text] = parts[i]
    if len(parts) != len(route.segments):
        return None
    return params
