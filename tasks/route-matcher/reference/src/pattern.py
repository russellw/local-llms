"""Compiling a pattern string into segments. See SPEC.md."""

STATIC = "static"
PARAM = "param"
WILD = "wild"


class Segment:
    def __init__(self, kind, text):
        self.kind = kind
        self.text = text

    def __repr__(self):
        return f"Segment({self.kind}, {self.text!r})"


def split_path(path):
    """Split a request path into its segments.

    A trailing slash is never significant, and the root path has no segments --
    `"".split("/")` would otherwise yield one empty segment that matches things
    it should not.
    """
    stripped = path.strip("/")
    return stripped.split("/") if stripped else []


def compile_pattern(pattern):
    """Turn a pattern string into a list of Segments.

    The marker is stripped: a capture is named `id`, not `:id`.
    """
    out = []
    for raw in split_path(pattern):
        if raw.startswith(":"):
            out.append(Segment(PARAM, raw[1:]))
        elif raw.startswith("*"):
            out.append(Segment(WILD, raw[1:]))
        else:
            out.append(Segment(STATIC, raw))
    return out
