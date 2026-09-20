"""The workspace a task runs in, and the six tools that operate on it.

One workspace per attempt: the task's `project/` tree is copied into a scratch
directory the model may read and write freely. The hidden tests are *not* in
that tree. `run_tests` copies the project and the tests into a second scratch
directory and runs them there, so the model can execute the tests as often as
it likes and can never read them.

Test output is sanitised before it goes back to the model. A unittest traceback
quotes the source line that failed, which for a hidden test suite would hand
over the assertion it is trying to satisfy -- so each task's runner prints
curated one-line failures and this module strips anything that still carries a
path into the tests tree.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field

from ..sandbox import _limits

MAX_READ_BYTES = 24_000
MAX_WRITE_BYTES = 60_000
MAX_TEST_OUTPUT = 4_000

TOOL_SPECS: list[dict] = [
    {
        "name": "list_files",
        "description": "List every file in the project with its size in lines.",
        "properties": {},
        "required": [],
    },
    {
        "name": "read_file",
        "description": "Read one project file in full. Paths are relative to the project root.",
        "properties": {"path": "File path, e.g. src/ledger.py."},
        "required": ["path"],
    },
    {
        "name": "write_file",
        "description": (
            "Create a new file, or replace one entirely, sending its complete "
            "contents. To change code that is already there, use replace_in_file "
            "instead -- re-sending a whole file is far slower and risks "
            "retyping correct code wrongly."
        ),
        "properties": {"path": "File path.", "content": "The complete new file contents."},
        "required": ["path", "content"],
    },
    {
        "name": "replace_in_file",
        "description": (
            "Replace one exact snippet in a file with another. `old` must appear "
            "exactly once, verbatim, including indentation. Cheaper than "
            "rewriting the whole file."
        ),
        "properties": {
            "path": "File path.",
            "old": "The exact text to replace.",
            "new": "The text to put in its place.",
        },
        "required": ["path", "old", "new"],
    },
    {
        "name": "run_tests",
        "description": (
            "Run the project's test suite and report which tests fail and why. "
            "The tests are not part of the project and cannot be read or edited."
        ),
        "properties": {},
        "required": [],
    },
    {
        "name": "finish",
        "description": (
            "End the task. Call this when the test suite passes, or when you are "
            "confident you can make no further progress."
        ),
        "properties": {"summary": "What you changed, in one or two sentences."},
        "required": ["summary"],
    },
]

TOOL_NAMES = [t["name"] for t in TOOL_SPECS]

TEXT_EXAMPLE = {"tool": "read_file", "args": {"path": "src/ledger.py"}}


class ToolError(Exception):
    """A tool refused. The message goes back to the model verbatim."""


@dataclass
class TestOutcome:
    ok: bool
    total: int = 0
    failed: int = 0
    report: str = ""
    timed_out: bool = False
    crashed: bool = False


@dataclass
class Workspace:
    """A scratch copy of one task's project, plus a way to run its tests."""

    project_src: str
    tests_src: str
    timeout: float = 90.0

    root: str = field(default="", init=False)
    _tmp: list = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        self.root = tempfile.mkdtemp(prefix="agentic-work-")
        self._tmp.append(self.root)
        shutil.copytree(self.project_src, self.root, dirs_exist_ok=True)

    def close(self) -> None:
        for d in self._tmp:
            shutil.rmtree(d, ignore_errors=True)
        self._tmp = []

    # -- path handling -------------------------------------------------

    def _resolve(self, path: str) -> str:
        """Confine every path to the project root. Escapes are a refusal."""
        if not isinstance(path, str) or not path.strip():
            raise ToolError("path is required")
        p = path.strip().lstrip("/")
        full = os.path.realpath(os.path.join(self.root, p))
        root = os.path.realpath(self.root)
        if full != root and not full.startswith(root + os.sep):
            raise ToolError(f"path escapes the project: {path}")
        return full

    def files(self) -> list[str]:
        out = []
        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = [d for d in dirnames if d != "__pycache__"]
            for fn in filenames:
                if fn.endswith(".pyc"):
                    continue
                full = os.path.join(dirpath, fn)
                out.append(os.path.relpath(full, self.root))
        return sorted(out)

    # -- the tools -----------------------------------------------------

    def list_files(self) -> str:
        rows = []
        for rel in self.files():
            try:
                with open(os.path.join(self.root, rel), "r", errors="replace") as f:
                    n = sum(1 for _ in f)
            except OSError:
                n = 0
            rows.append(f"{rel} ({n} lines)")
        return "\n".join(rows) if rows else "(empty project)"

    def read_file(self, path: str) -> str:
        full = self._resolve(path)
        if not os.path.isfile(full):
            raise ToolError(f"no such file: {path}. Use list_files to see what exists.")
        with open(full, "r", errors="replace") as f:
            data = f.read(MAX_READ_BYTES + 1)
        if len(data) > MAX_READ_BYTES:
            return data[:MAX_READ_BYTES] + "\n... (truncated)"
        return data

    def write_file(self, path: str, content) -> str:
        full = self._resolve(path)
        if content is None:
            raise ToolError("content is required")
        text = content if isinstance(content, str) else str(content)
        if len(text) > MAX_WRITE_BYTES:
            raise ToolError("content is too large")
        os.makedirs(os.path.dirname(full), exist_ok=True)
        existed = os.path.isfile(full)
        with open(full, "w") as f:
            f.write(text)
        n = text.count("\n") + 1
        return f"{'wrote' if existed else 'created'} {path} ({n} lines)"

    def replace_in_file(self, path: str, old, new) -> str:
        full = self._resolve(path)
        if not os.path.isfile(full):
            raise ToolError(f"no such file: {path}")
        if not isinstance(old, str) or old == "":
            raise ToolError("old is required and must be a non-empty string")
        new = "" if new is None else (new if isinstance(new, str) else str(new))
        with open(full, "r", errors="replace") as f:
            data = f.read()
        n = data.count(old)
        if n == 0:
            raise ToolError(
                f"old does not appear in {path}. Read the file and copy the text "
                "exactly, including indentation."
            )
        if n > 1:
            raise ToolError(
                f"old appears {n} times in {path}; it must identify one place "
                "uniquely. Include more surrounding lines."
            )
        with open(full, "w") as f:
            f.write(data.replace(old, new))
        return f"replaced 1 occurrence in {path}"

    def run_tests(self) -> TestOutcome:
        """Run the hidden suite against the current project state."""
        work = tempfile.mkdtemp(prefix="agentic-test-")
        self._tmp.append(work)
        try:
            shutil.copytree(self.root, work, dirs_exist_ok=True)
            shutil.copytree(self.tests_src, work, dirs_exist_ok=True)
            runner = os.path.join(work, "run_tests.py")
            if not os.path.isfile(runner):
                return TestOutcome(ok=False, report="no test runner", crashed=True)
            env = {
                "PATH": "/usr/bin:/bin",
                "HOME": work,
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONPATH": work,
            }
            try:
                proc = subprocess.run(
                    [sys.executable, runner],
                    cwd=work,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    preexec_fn=_limits,
                )
            except subprocess.TimeoutExpired:
                return TestOutcome(
                    ok=False,
                    timed_out=True,
                    report=(
                        f"the test run did not finish within {self.timeout:.0f}s. "
                        "Something is looping or is far too slow."
                    ),
                )
            raw = (proc.stdout or "") + (("\n" + proc.stderr) if proc.stderr else "")
            return _read_outcome(raw, proc.returncode, work)
        finally:
            shutil.rmtree(work, ignore_errors=True)
            if work in self._tmp:
                self._tmp.remove(work)


_COUNT_RE = re.compile(r"^RESULT\s+(\d+)\s+passed\s+(\d+)\s+failed\s*$", re.M)


def _read_outcome(raw: str, returncode: int, workdir: str) -> TestOutcome:
    """Turn a runner's output into a verdict, without leaking the tests."""
    text = _sanitise(raw, workdir)
    m = _COUNT_RE.search(text)
    passed = failed = 0
    if m:
        passed, failed = int(m.group(1)), int(m.group(2))
        text = _COUNT_RE.sub("", text).strip()
    crashed = m is None
    ok = returncode == 0 and not crashed and failed == 0
    if len(text) > MAX_TEST_OUTPUT:
        text = text[:MAX_TEST_OUTPUT] + "\n... (truncated)"
    if ok and not text:
        text = "all tests passed"
    return TestOutcome(
        ok=ok,
        total=passed + failed,
        failed=failed,
        report=text or ("crashed before reporting" if crashed else ""),
        crashed=crashed,
    )


def _sanitise(text: str, workdir: str) -> str:
    """Strip anything that would hand the model the tests themselves.

    A traceback quotes the failing source line, so a stray unittest stack would
    leak the assertion the model is meant to satisfy. Drop any line naming a
    test file or a path inside the scratch directory.
    """
    out = []
    for line in (text or "").splitlines():
        low = line.lower()
        if workdir and workdir in line:
            continue
        if re.search(r'File "[^"]*(test|conftest)', line):
            continue
        if low.strip().startswith(("file \"", "  file \"")):
            continue
        if re.match(r"\s*(assert|self\.assert)", line):
            continue
        if "run_tests.py" in line:
            continue
        out.append(line)
    return "\n".join(out).strip()
