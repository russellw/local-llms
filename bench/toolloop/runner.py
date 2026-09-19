"""Run the tool-loop suite against a served model and record every episode.

Same contract as the code-task runner: JSONL flushed after each episode, so a
run that dies at 4am leaves you everything it finished, and re-running the same
command resumes.

Results land in results/toolloop/ rather than results/, because the two suites
score different things and averaging them together would produce a number that
means nothing.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from ..client import ChatClient
from ..runner import _host_info
from . import protocol
from .episodes import Episode
from .loop import run_episode

RESULTS_DIR = Path(__file__).resolve().parent.parent.parent / "results" / "toolloop"


def detect_protocol(client: ChatClient) -> str:
    """Does this server accept the `tools` parameter at all?

    Deliberately a test of the *server*, not of the model: it asks whether the
    request is accepted, not whether the reply contains a tool call. A model
    that is offered tools and does not use them is the thing being measured,
    and must not be quietly routed onto an easier protocol.
    """
    probe = [{"role": "user", "content": "Say ok."}]
    comp = client.complete(probe, max_tokens=8, tools=protocol.openai_tools())
    if comp.error:
        return "text"
    return "native"


def _done_keys(path: Path) -> set[tuple[str, int]]:
    done = set()
    if not path.exists():
        return done
    for line in path.read_text().splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("type") == "result":
            done.add((rec["episode_id"], rec["attempt"]))
    return done


def run_toolloop(
    client: ChatClient,
    episodes: list[Episode],
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
                    "suite": "toolloop",
                    "model": model_label,
                    "started": datetime.now(timezone.utc).isoformat(),
                    "protocol": protocol_mode,
                    "repeats": repeats,
                    "temperature": temperature,
                    "n_episodes": len(episodes),
                    "host": _host_info(),
                }
            )
            + "\n"
        )
        out.flush()

        total = len(episodes) * repeats
        n = 0
        t_start = time.monotonic()

        for attempt in range(repeats):
            for ep in episodes:
                n += 1
                if (ep.id, attempt) in done:
                    if verbose:
                        print(f"[{n}/{total}] {ep.id} #{attempt} -- skip (done)")
                    continue
                if verbose:
                    print(f"[{n}/{total}] {ep.id} #{attempt} ... ", end="", flush=True)

                res, transcript = run_episode(
                    client,
                    ep,
                    protocol_mode=protocol_mode,
                    temperature=temperature,
                    seed=attempt,
                    max_tokens_scale=max_tokens_scale,
                )

                (log_dir / f"{ep.id}.{attempt}.md").write_text(
                    _render_transcript(ep, res, transcript)
                )

                rec = {"type": "result", "attempt": attempt, **res.to_dict()}
                out.write(json.dumps(rec) + "\n")
                out.flush()

                if verbose:
                    mark = "HIT " if res.target_hit else "miss"
                    extra = []
                    if res.anti_target_hit:
                        extra.append("WRONG PREMISE")
                    if res.guard_hits and not res.guard_recovered:
                        extra.append("stuck on a shape")
                    if res.stopped != "finish":
                        extra.append(f"stopped: {res.stopped}")
                    print(
                        f"{mark} ({res.steps}/{res.budget} steps, "
                        f"{res.distinct_tools} tools, {res.wall_s / 60:.1f}m)"
                        + ("  -- " + "; ".join(extra) if extra else "")
                    )

    if verbose:
        print(f"\nDone in {(time.monotonic() - t_start) / 60:.1f} min -> {out_path}")
    return out_path


def _render_transcript(ep, res, transcript) -> str:
    lines = [
        f"# {ep.id} -- {ep.title}",
        "",
        f"target hit: {res.target_hit}   stopped: {res.stopped}   "
        f"steps: {res.steps}/{res.budget}   tools: {', '.join(res.tools_used) or 'none'}",
        "",
    ]
    for t in transcript:
        lines.append(f"## step {t['step']}")
        if t["text"].strip():
            lines.append("")
            lines.append(t["text"].strip())
        for c in t["calls"]:
            lines.append("")
            lines.append(f"    -> {c['tool']}({json.dumps(c['args'])})")
        lines.append("")
    return "\n".join(lines)
