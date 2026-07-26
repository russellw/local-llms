"""Load task definitions from the tasks/ directory.

Each task is a directory containing:
    prompt.md     the user message sent to the model
    tests.py      a script that imports `solution` and exits non-zero on failure
    reference.py  a known-good solution, used by `bench selfcheck`

Per-task metadata lives in one place, tasks/manifest.json, keyed by directory
name. Anything omitted falls back to the defaults below.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

TASKS_DIR = Path(__file__).resolve().parent.parent / "tasks"


@dataclass
class Task:
    id: str
    title: str
    category: str
    difficulty: str
    prompt: str
    tests: str
    timeout: float = 30.0
    max_tokens: int = 2048
    path: Path | None = None

    @property
    def reference(self) -> str:
        p = (self.path or TASKS_DIR / self.id) / "reference.py"
        return p.read_text() if p.exists() else ""


def load_tasks(root: Path | None = None, filters: list[str] | None = None) -> list[Task]:
    root = root or TASKS_DIR
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}

    tasks: list[Task] = []
    for prompt_path in sorted(root.glob("*/prompt.md")):
        d = prompt_path.parent
        meta = manifest.get(d.name, {})
        tasks.append(
            Task(
                id=d.name,
                title=meta.get("title", d.name),
                category=meta.get("category", "misc"),
                difficulty=meta.get("difficulty", "medium"),
                prompt=prompt_path.read_text(),
                tests=(d / "tests.py").read_text(),
                timeout=float(meta.get("timeout", 30)),
                max_tokens=int(meta.get("max_tokens", 2048)),
                path=d,
            )
        )

    if filters:
        tasks = [
            t
            for t in tasks
            if any(f in (t.id, t.category, t.difficulty) or f in t.id for f in filters)
        ]
    return tasks
