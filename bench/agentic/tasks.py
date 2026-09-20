"""Task definitions: a broken project, a hidden test suite, and a reference fix.

    tasks/<id>/
        task.json     title, brief, budget and the rest of the metadata
        project/      the tree the model is given, copied fresh per attempt
        tests/        the hidden suite; copied in only to run, never readable
        reference/    files overlaid on project/ to make the suite pass

`reference/` is what `selfcheck` uses: overlay it, run the tests, and they must
pass. A task whose own reference fix fails its own tests measures nothing, and
that is the single most important thing the guard rail catches.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

TASKS_DIR = Path(__file__).resolve().parent.parent.parent / "tasks"


@dataclass
class Task:
    id: str
    title: str
    brief: str
    budget: int = 24
    difficulty: str = "medium"
    test_timeout: float = 90.0
    max_tokens: int = 1400
    # The file holding a requirement that cannot be inferred from the code.
    # Empty when the task has no such clause. Drives `reads the spec`.
    spec_file: str = ""
    # A fix that looks right, passes the obvious symptom, and is wrong. Used
    # only for reporting, never to score.
    trap: str = ""
    dir: Path = field(default=TASKS_DIR)

    @property
    def project_dir(self) -> str:
        return str(self.dir / "project")

    @property
    def tests_dir(self) -> str:
        return str(self.dir / "tests")

    @property
    def reference_dir(self) -> str:
        return str(self.dir / "reference")


def load_tasks(filters: list[str] | None = None) -> list[Task]:
    out = []
    if not TASKS_DIR.is_dir():
        return out
    for d in sorted(TASKS_DIR.iterdir()):
        if not (d / "task.json").is_file():
            continue
        meta = json.loads((d / "task.json").read_text())
        t = Task(
            id=d.name,
            title=meta.get("title", d.name),
            brief=meta["brief"],
            budget=int(meta.get("budget", 24)),
            difficulty=meta.get("difficulty", "medium"),
            test_timeout=float(meta.get("test_timeout", 90.0)),
            max_tokens=int(meta.get("max_tokens", 1400)),
            spec_file=meta.get("spec_file", ""),
            trap=meta.get("trap", ""),
            dir=d,
        )
        out.append(t)
    if filters:
        want = {f.lower() for f in filters}
        out = [t for t in out if t.id.lower() in want or t.difficulty.lower() in want]
    return out
