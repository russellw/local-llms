"""A URL router. See SPEC.md for the matching rules."""

from .pattern import STATIC, PARAM, WILD, compile_pattern, split_path


class Route:
    def __init__(self, pattern, handler, order):
        self.pattern = pattern
        self.segments = compile_pattern(pattern)
        self.handler = handler
        self.order = order


class Router:
    def __init__(self):
        self.routes = []

    def add(self, pattern, handler):
        self.routes.append(Route(pattern, handler, len(self.routes)))

    def match(self, path):
        """Return (handler, params) for the best matching route, or None."""
        for route in self.routes:
            params = _try(route, split_path(path))
            if params is not None:
                return route.handler, params
        return None


def _try(route, parts):
    """Match one route against the path segments, returning captures or None."""
    params = {}
    for i, seg in enumerate(route.segments):
        if i >= len(parts):
            return None
        if seg.kind == STATIC:
            if parts[i] != seg.text:
                return None
        elif seg.kind == PARAM:
            params[seg.text] = parts[i]
        elif seg.kind == WILD:
            params[seg.text] = parts[i]
            return params
    if len(parts) != len(route.segments):
        return None
    return params
