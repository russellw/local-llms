"""Summarise result JSONL files into a comparison table."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"


def load_run(path: Path) -> tuple[dict, list[dict]]:
    meta, results = {}, []
    for line in path.read_text().splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("type") == "meta":
            meta = rec
        elif rec.get("type") == "result":
            results.append(rec)
    return meta, results


def summarise(meta: dict, results: list[dict]) -> dict:
    if not results:
        return {"model": meta.get("model", "?"), "n": 0}

    by_task: dict[str, list[bool]] = defaultdict(list)
    for r in results:
        by_task[r["task_id"]].append(r["passed"])

    n_tasks = len(by_task)
    # pass@1 = mean success rate over all attempts; pass@any = solved at least once.
    all_attempts = [r["passed"] for r in results]
    pass1 = sum(all_attempts) / len(all_attempts)
    passany = sum(any(v) for v in by_task.values()) / n_tasks

    speeds = [r["tok_per_s"] for r in results if r.get("tok_per_s")]
    speeds.sort()

    by_cat: dict[str, list[bool]] = defaultdict(list)
    for r in results:
        by_cat[r.get("category", "misc")].append(r["passed"])

    return {
        "model": meta.get("model", "?"),
        "n": len(results),
        "n_tasks": n_tasks,
        "pass1": pass1,
        "passany": passany,
        "med_tok_per_s": speeds[len(speeds) // 2] if speeds else 0.0,
        "total_min": sum(r.get("wall_s", 0) for r in results) / 60,
        "truncated": sum(1 for r in results if r.get("truncated")),
        "no_code": sum(1 for r in results if r.get("detail") == "no code block in response"),
        # A request that never returned is "too slow to use", not "got it wrong".
        # Lumping the two together makes a slow model look like a stupid one.
        "timeouts": sum(
            1 for r in results if "TimeoutError" in str(r.get("detail", ""))
        ),
        "exec_timeouts": sum(1 for r in results if r.get("detail") == "timeout"),
        "by_category": {k: sum(v) / len(v) for k, v in sorted(by_cat.items())},
        "failures": sorted(
            {r["task_id"] for r in results if not r["passed"]}
            - {t for t, v in by_task.items() if any(v)}
        ),
    }


def _pct(x: float) -> str:
    return f"{100 * x:.0f}%"


def render(summaries: list[dict]) -> str:
    summaries = [s for s in summaries if s.get("n")]
    if not summaries:
        return "No results yet. Run `python3 -m bench run --label <model>` first.\n"
    summaries.sort(key=lambda s: (-s["pass1"], -s["med_tok_per_s"]))

    cats = sorted({c for s in summaries for c in s["by_category"]})
    head = ["Model", "pass@1", "pass@any", "tok/s", "runtime"] + cats
    rows = [
        [
            s["model"],
            _pct(s["pass1"]),
            _pct(s["passany"]),
            f"{s['med_tok_per_s']:.1f}",
            f"{s['total_min']:.0f}m",
        ]
        + [_pct(s["by_category"][c]) if c in s["by_category"] else "-" for c in cats]
        for s in summaries
    ]

    widths = [max(len(str(r[i])) for r in [head] + rows) for i in range(len(head))]
    out = [
        "| " + " | ".join(h.ljust(w) for h, w in zip(head, widths)) + " |",
        "|" + "|".join("-" * (w + 2) for w in widths) + "|",
    ]
    out += [
        "| " + " | ".join(str(c).ljust(w) for c, w in zip(r, widths)) + " |"
        for r in rows
    ]

    out.append("")
    for s in summaries:
        notes = []
        if s["timeouts"]:
            notes.append(
                f"{s['timeouts']} attempt(s) never finished generating within the "
                f"request timeout -- too slow rather than wrong"
            )
        if s["truncated"]:
            notes.append(f"{s['truncated']} response(s) hit the token limit")
        if s["no_code"]:
            notes.append(f"{s['no_code']} response(s) contained no code block")
        if s["exec_timeouts"]:
            notes.append(f"{s['exec_timeouts']} solution(s) hung when executed")
        if s["failures"]:
            notes.append("never solved: " + ", ".join(s["failures"]))
        if notes:
            out.append(f"**{s['model']}** -- " + "; ".join(notes))
    return "\n".join(out) + "\n"


def build_report(results_dir: Path | None = None) -> str:
    results_dir = results_dir or RESULTS_DIR
    summaries = []
    for p in sorted(results_dir.glob("*.jsonl")):
        summaries.append(summarise(*load_run(p)))
    return render(summaries)
