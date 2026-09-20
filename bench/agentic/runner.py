"""Run the suite against a served model and record every attempt.

JSONL is flushed after each attempt, so a run that dies at 4am leaves you
everything it finished, and re-running the same command resumes.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from ..client import ChatClient
from ..host import host_info
from .. import toolcall
from .tasks import Task
from .loop import run_task
from .tools import TOOL_SPECS

RESULTS_DIR = Path(__file__).resolve().parent.parent.parent / "results"


def detect_protocol(client: ChatClient) -> str:
    """Does this server accept the `tools` parameter at all?

    A test of the *server*, not the model: it asks whether the request is
    accepted, not whether the reply contains a tool call. A model that is
    offered tools and does not use them is the thing being measured, and must
    not be quietly routed onto an easier protocol.
    """
    probe = [{"role": "user", "content": "Say ok."}]
    comp = client.complete(probe, max_tokens=8, tools=toolcall.openai_tools(TOOL_SPECS))
    return "text" if comp.error else "native"


def _done_keys(path: Path) -> set:
    done = set()
    if not path.exists():
        return done
    for line in path.read_text().splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("type") == "result":
            done.add((rec["task_id"], rec["attempt"]))
    return done


def run_suite(
    client: ChatClient,
    tasks: list[Task],
    model_label: str,
    protocol_mode: str = "native",
    repeats: int = 1,
    temperature: float = 0.0,
    max_tokens_scale: float = 1.0,
    out_dir: Path | None = None,
    resume: bool = True,
    verbose: bool = True,
) -> Path:
    out_dir = out_dir or RESULTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    safe = "".join(c if c.isalnum() or c in "-._" else "-" for c in model_label)
    out_path = out_dir / f"{safe}.jsonl"
    log_dir = out_dir / "transcripts" / safe
    log_dir.mkdir(parents=True, exist_ok=True)

    done = _done_keys(out_path) if resume else set()
    if not resume and out_path.exists():
        out_path.unlink()

    with out_path.open("a") as out:
        out.write(
            json.dumps(
                {
                    "type": "meta",
                    "suite": "agentic",
                    "model": model_label,
                    "started": datetime.now(timezone.utc).isoformat(),
                    "protocol": protocol_mode,
                    "repeats": repeats,
                    "temperature": temperature,
                    "n_tasks": len(tasks),
                    "host": host_info(),
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

                res, transcript = run_task(
                    client,
                    task,
                    protocol_mode=protocol_mode,
                    temperature=temperature,
                    seed=attempt,
                    max_tokens_scale=max_tokens_scale,
                )

                (log_dir / f"{task.id}.{attempt}.md").write_text(
                    _render(task, res, transcript)
                )
                out.write(json.dumps({"type": "result", "attempt": attempt, **res.to_dict()}) + "\n")
                out.flush()

                if verbose:
                    mark = "PASS" if res.passed else "fail"
                    extra = []
                    if res.finished_unverified:
                        extra.append("declared done while failing")
                    if res.regressed:
                        extra.append("was green, then broke it")
                    if res.stopped != "finish":
                        extra.append(f"stopped: {res.stopped}")
                    print(
                        f"{mark} ({res.steps}/{res.budget} steps, "
                        f"{res.tests_failed_at_end}/{res.tests_total} failing, "
                        f"{res.edits_made} edits, {res.wall_s / 60:.1f}m)"
                        + ("  -- " + "; ".join(extra) if extra else "")
                    )

    if verbose:
        print(f"\nDone in {(time.monotonic() - t_start) / 60:.1f} min -> {out_path}")
    return out_path


def _render(task: Task, res, transcript: list[dict]) -> str:
    lines = [
        f"# {task.id} -- {task.title}",
        "",
        f"passed: {res.passed}   stopped: {res.stopped}   "
        f"steps: {res.steps}/{res.budget}   edits: {res.edits_made}   "
        f"test runs: {res.test_runs}   failing at end: "
        f"{res.tests_failed_at_end}/{res.tests_total}",
        "",
    ]
    for t in transcript:
        lines.append(f"## step {t['step']}")
        if (t.get("text") or "").strip():
            lines.append("")
            lines.append(t["text"].strip())
        for c, r in zip(t["calls"], list(t["results"]) + [""] * len(t["calls"])):
            lines.append("")
            lines.append(f"    -> {c['tool']}({json.dumps(c['args'])})")
            if r:
                body = r if len(r) <= 800 else r[:800] + "... (truncated)"
                lines.append("")
                for ln in body.splitlines():
                    lines.append(f"       {ln}")
        lines.append("")
    return "\n".join(lines)
