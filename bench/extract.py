"""Pull runnable code out of a chat response.

Small local models are inconsistent markdown citizens: some emit clean fenced
blocks, some emit bare code, some narrate first and fence later. Being generous
here measures coding ability rather than formatting compliance.
"""

from __future__ import annotations

import re

FENCE = re.compile(
    r"```[ \t]*([A-Za-z0-9_+-]*)[ \t]*\r?\n(.*?)(?:```|\Z)",
    re.DOTALL,
)

# Reasoning models wrap their scratchpad in these; never treat it as an answer.
THINK = re.compile(r"<(think|thinking|reasoning)>.*?</\1>", re.DOTALL | re.IGNORECASE)

_PY_HINTS = ("def ", "class ", "import ", "from ", "return ", "print(")


def strip_reasoning(text: str) -> str:
    text = THINK.sub("", text)
    # An unterminated <think> means the model ran out of tokens mid-thought.
    open_tag = re.search(r"<(think|thinking|reasoning)>", text, re.IGNORECASE)
    if open_tag:
        text = text[: open_tag.start()]
    return text


def extract_code(text: str, lang: str = "python") -> str:
    """Return the best candidate code block, or '' if nothing looks like code."""
    if not text:
        return ""
    text = strip_reasoning(text)

    blocks = [(tag.lower(), body) for tag, body in FENCE.findall(text)]
    if blocks:
        tagged = [b for tag, b in blocks if tag in _lang_aliases(lang)]
        if tagged:
            # Last tagged block wins: models often revise after a first attempt.
            return tagged[-1].strip()
        untagged = [b for tag, b in blocks if not tag]
        if untagged:
            return untagged[-1].strip()
        # Blocks exist but all mislabelled (```text, ```sh). Take the codiest one.
        best = max(blocks, key=lambda tb: sum(h in tb[1] for h in _PY_HINTS))
        if any(h in best[1] for h in _PY_HINTS):
            return best[1].strip()
        return ""

    # No fences at all: accept the raw text if it reads as code.
    if any(h in text for h in _PY_HINTS):
        return text.strip()
    return ""


def _lang_aliases(lang: str) -> set[str]:
    aliases = {
        "python": {"python", "python3", "py"},
        "c": {"c"},
        "cpp": {"cpp", "c++", "cxx"},
        "bash": {"bash", "sh", "shell"},
        "sql": {"sql"},
    }
    return aliases.get(lang, {lang})
