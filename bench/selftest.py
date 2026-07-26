"""Unit tests for the harness itself, run as part of `bench selfcheck`.

Extraction and sandboxing sit between the model and its score. A bug in either
one shows up as a model looking worse than it is, silently, so they get tested
rather than trusted.
"""

from __future__ import annotations

from .extract import extract_code
from .sandbox import run_python_tests

_EXTRACT_CASES = [
    ("plain fenced", "Here you go:\n```python\ndef f():\n    return 1\n```\nDone.",
     "def f():\n    return 1"),
    ("untagged fence", "```\ndef f():\n    return 1\n```", "def f():\n    return 1"),
    ("py alias", "```py\ndef f(): return 1\n```", "def f(): return 1"),
    ("last block wins after a revision",
     "```python\ndef f(): return 0\n```\nOops:\n```python\ndef f(): return 1\n```",
     "def f(): return 1"),
    ("bare code, no fence", "def f():\n    return 1", "def f():\n    return 1"),
    ("reasoning block stripped",
     "<think>maybe recursion?</think>\n```python\ndef f(): return 1\n```",
     "def f(): return 1"),
    ("unterminated reasoning yields nothing",
     "<think>hmm I should\n```python\ndef wrong(): pass\n```", ""),
    ("unclosed fence from a token limit", "```python\ndef f():\n    return 1",
     "def f():\n    return 1"),
    ("mislabelled fence", "```text\ndef f():\n    return 1\n```",
     "def f():\n    return 1"),
    ("prose only", "I cannot help with that.", ""),
    ("bash ignored, python kept",
     "```bash\npip install x\n```\n```python\ndef f(): return 1\n```",
     "def f(): return 1"),
    ("empty", "", ""),
]

_PASSING_TEST = "from solution import f\nassert f() == 1\n"


def run() -> list[str]:
    """Return a list of failure descriptions; empty means everything passed."""
    fails = []

    for name, text, want in _EXTRACT_CASES:
        got = extract_code(text)
        if got != want:
            fails.append(f"extract [{name}]: got {got!r}, want {want!r}")

    ok = run_python_tests("def f():\n    return 1\n", _PASSING_TEST)
    if not ok.ok:
        fails.append(f"sandbox: a correct solution failed: {ok.summary}")

    bad = run_python_tests("def f():\n    return 2\n", _PASSING_TEST)
    if bad.ok:
        fails.append("sandbox: a wrong solution passed")

    syntax = run_python_tests("def f( :\n", _PASSING_TEST)
    if syntax.ok:
        fails.append("sandbox: code with a syntax error passed")

    spin = run_python_tests("while True:\n    pass\n", _PASSING_TEST, timeout=5)
    if not spin.timed_out:
        fails.append(f"sandbox: an infinite loop was not stopped ({spin.summary})")

    # Each run must get a clean directory, or one task could poison the next.
    leak = run_python_tests(
        "import os\nopen('leaked.txt', 'w').write('x')\ndef f():\n    return 1\n",
        "import os\nassert not os.path.exists('/tmp/leaked.txt')\n"
        "from solution import f\nassert f() == 1\n",
    )
    if not leak.ok:
        fails.append(f"sandbox: workdir isolation broken: {leak.summary}")

    return fails
