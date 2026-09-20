"""Strip a reasoning block from a model's reply.

A model that thinks out loud emits the thinking before the answer, and a tool
call parsed out of the thinking is a call the model was only considering. The
answer is whatever follows the closing tag; an unterminated block means the
model never got to one, and there is no answer to find.
"""

from __future__ import annotations

import re

_THINK_RE = re.compile(
    r"<(think|thinking|reasoning|analysis)>.*?</\1>", re.S | re.I
)
_UNCLOSED_RE = re.compile(r"<(think|thinking|reasoning|analysis)>", re.I)


def strip_reasoning(text: str) -> str:
    """Remove closed reasoning blocks; an unclosed one swallows the rest."""
    if not text:
        return ""
    out = _THINK_RE.sub("", text)
    m = _UNCLOSED_RE.search(out)
    if m:
        out = out[: m.start()]
    return out.strip()
