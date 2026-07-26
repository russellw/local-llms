"""Run the task suite against a model and record every attempt.

Results are written as JSONL, flushed after each attempt, so an overnight run
that dies at 4am still leaves you everything it finished. Re-running the same
command resumes where it stopped.
"""

from __future__ import annotations

import json
import platform
import time
from datetime import datetime, timezone
from pathlib import Path

from .client import ChatClient
from .extract import extract_code
from .sandbox import run_python_tests
from .tasks import Task

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"

SYSTEM_PROMPT = (
    "You are an expert Python programmer. Respond with a single complete Python "
    "code block containing the requested code. Do not include example usage, "
    "tests, or explanation outside the code block."
)


def _host_info() -> dict:
    info = {
        "platform": platform.platform(),
        "processor": platform.processor() or platform.machine(),
        "python": platform.python_version(),
    }
    try:
        cpu = [
            l.split(":", 1)[1].strip()
            for l in Path("/proc/cpuinfo").read_text().splitlines()
            if l.startswith("model name")
        ]
        if cpu:
            info["cpu"] = cpu[0]
            info["cpu_threads"] = len(cpu)
        mem = [
            l for l in Path("/proc/meminfo").read_text().splitlines()
            if l.startswith("MemTotal")
        ]
        if mem:
            info["mem_kb"] = int(mem[0].split()[1])
    except OSError:
        pass
    return info


def _done_keys(path: Path) -> set[tuple[str, int]]:
    """(task_id, attempt) pairs already recorded, for resume."""
    done = set()
    if not path.exists():
        return done
    for line in path.read_text().splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue  # torn last line from a hard kill
        if rec.get("type") == "result":
            done.add((rec["task_id"], rec["attempt"]))
    return done


def run_suite(
    client: ChatClient,
    tasks: list[Task],
    model_label: str,
    repeats: int = 1,
    temperature: float = 0.0,
    out_dir: Path | None = None,
    resume: bool = True,
    verbose: bool = True,
) -> Path:
    out_dir = out_dir or RESULTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    safe = "".join(c if c.isalnum() or c in "-._" else "-" for c in model_label)
    out_path = out_dir / f"{safe}.jsonl"
    log_dir = out_dir / "responses" / safe
    log_dir.mkdir(parents=True, exist_ok=True)

    done = _done_keys(out_path) if resume else set()
    if not resume and out_path.exists():
        out_path.unlink()

    with out_path.open("a") as out:
        out.write(
            json.dumps(
                {
                    "type": "meta",
                    "model": model_label,
                    "started": datetime.now(timezone.utc).isoformat(),
                    "repeats": repeats,
                    "temperature": temperature,
                    "n_tasks": len(tasks),
                    "host": _host_info(),
                }
            )
            + "\n"
        )
        out.flush()

        total = len(tasks) * repeats
        n = 0
        t_start = time.monotonic()

        for attempt in range(repeats):
            for task in tasks:
                n += 1
                if (task.id, attempt) in done:
                    if verbose:
                        print(f"[{n}/{total}] {task.id} #{attempt} -- skip (done)")
                    continue

                if verbose:
                    print(f"[{n}/{total}] {task.id} #{attempt} ... ", end="", flush=True)

                comp = client.chat(
                    task.prompt,
                    system=SYSTEM_PROMPT,
                    temperature=temperature,
                    max_tokens=task.max_tokens,
                    seed=attempt,
                )

                (log_dir / f"{task.id}.{attempt}.md").write_text(
                    comp.text or f"<no output>\n{comp.error or ''}"
                )

                code = extract_code(comp.text)
                if comp.error:
                    passed, detail = False, f"api error: {comp.error}"
                elif not code:
                    passed, detail = False, "no code block in response"
                else:
                    ex = run_python_tests(code, task.tests, timeout=task.timeout)
                    passed, detail = ex.ok, ex.summary

                rec = {
                    "type": "result",
                    "task_id": task.id,
                    "category": task.category,
                    "difficulty": task.difficulty,
                    "attempt": attempt,
                    "passed": passed,
                    "detail": detail,
                    "truncated": comp.stop_reason == "length",
                    **comp.to_dict(),
                }
                rec.pop("text", None)  # full text lives in responses/
                rec["chars"] = len(comp.text)
                out.write(json.dumps(rec) + "\n")
                out.flush()

                if verbose:
                    mark = "PASS" if passed else "FAIL"
                    print(
                        f"{mark} ({comp.tok_per_s:.1f} tok/s, "
                        f"{comp.wall_s:.0f}s)"
                        + ("" if passed else f" -- {detail}")
                    )

    if verbose:
        mins = (time.monotonic() - t_start) / 60
        print(f"\nDone in {mins:.1f} min -> {out_path}")
    return out_path
