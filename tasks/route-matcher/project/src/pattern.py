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
    """Split a request path into its segments."""
    return path.strip("/").split("/")


def compile_pattern(pattern):
    """Turn a pattern string into a list of Segments."""
    out = []
    for raw in split_path(pattern):
        if raw.startswith(":"):
            out.append(Segment(PARAM, raw))
        elif raw.startswith("*"):
            out.append(Segment(WILD, raw))
        else:
            out.append(Segment(STATIC, raw))
    return out
