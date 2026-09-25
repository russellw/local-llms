"""Turn recorded attempts into a table.

One suite, one ground truth: `solved` is the fraction of attempts where the
hidden test suite passes against what the model left behind. Every other
column explains how, and none of them is averaged into it.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

RESULTS_DIR = Path(__file__).resolve().parent.parent.parent / "results"


def load_run(path: Path) -> tuple[dict, list[dict]]:
    meta: dict = {}
    rows: list[dict] = []
    for line in path.read_text().splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("type") == "meta":
            meta = rec
        elif rec.get("type") == "result":
            rows.append(rec)
    return meta, rows


def _operates(r: dict, protocol: str) -> bool:
    """The tool-operating floor, recomputed here so every row uses one rule.

    Under the native protocol a malformed call means the model wrote its call
    into the reply text instead of the tool-call field: a real channel failure,
    because a strict agent client reads the field and sees nothing.

    Under the text protocol there is no field to miss -- the reply text *is*
    the channel -- and `malformed` there mostly means the JSON was not fenced
    the way the prompt asked. That is a formatting nit, not an inability to
    operate the tools, and counting it the same way put a model at 0% on this
    floor in the same run it solved two tasks outright. So the in-channel test
    applies only where there is a channel.
    """
    total = r.get("calls_total", 0)
    if total < 3:
        return False
    answered = (total - r.get("calls_refused", 0)) / total
    if answered < 0.8 or r.get("distinct_tools", 0) < 3:
        return False
    if protocol == "text":
        return True
    in_channel = (total - r.get("calls_malformed", 0)) / total
    return in_channel >= 0.8


def _mean(vals) -> float:
    vals = list(vals)
    return sum(1 for v in vals if v) / len(vals) if vals else 0.0


def summarise(meta: dict, rows: list[dict]) -> dict:
    if not rows:
        return {"model": meta.get("model", "?"), "n": 0}

    by_task: dict[str, list[bool]] = defaultdict(list)
    for r in rows:
        by_task[r["task_id"]].append(bool(r.get("passed")))

    spec_rows = [r for r in rows if r.get("spec_relevant")]
    finished = [r for r in rows if r.get("stopped") == "finish"]
    calls = sum(r.get("calls_total", 0) for r in rows)
    bad = sum(r.get("calls_malformed", 0) + r.get("calls_unknown_tool", 0) for r in rows)

    return {
        "model": meta.get("model", "?"),
        "protocol": meta.get("protocol", "?"),
        "n": len(rows),
        "n_tasks": len(by_task),
        "solved": _mean(bool(r.get("passed")) for r in rows),
        "solved_any": sum(1 for v in by_task.values() if any(v)) / len(by_task),
        "operates": _mean(_operates(r, meta.get("protocol", "native")) for r in rows),
        "verifies": _mean(r.get("test_runs", 0) > 0 for r in rows),
        "reads_spec": _mean(bool(r.get("read_spec")) for r in spec_rows) if spec_rows else None,
        "false_done": sum(1 for r in rows if r.get("finished_unverified")),
        "false_green": sum(1 for r in rows if r.get("false_green")),
        "visible_solved": _mean(bool(r.get("visible_passed")) for r in rows),
        "regressed": sum(1 for r in rows if r.get("regressed")),
        "edits": sum(r.get("edits_made", 0) for r in rows) / len(rows),
        "edit_failures": sum(r.get("calls_refused", 0) for r in rows),
        "test_runs": sum(r.get("test_runs", 0) for r in rows) / len(rows),
        "steps_used": sum(
            r.get("steps", 0) / max(1, r.get("budget", 1)) for r in rows
        ) / len(rows),
        "call_error_rate": bad / calls if calls else 0.0,
        "out_of_band": sum(r.get("calls_malformed", 0) for r in rows),
        "repeats": sum(r.get("calls_repeated", 0) for r in rows),
        "truncated": sum(r.get("calls_truncated", 0) for r in rows),
        "compactions": sum(r.get("compactions", 0) for r in rows),
        "no_call": sum(1 for r in rows if r.get("stopped") == "no_call"),
        "api_errors": sum(1 for r in rows if r.get("stopped") == "error"),
        "voluntary_stop": len(finished) / len(rows),
        "tok_per_s": _median([r.get("tok_per_s", 0) for r in rows if r.get("tok_per_s")]),
        "total_min": sum(r.get("wall_s", 0) for r in rows) / 60,
        "never_solved": sorted(t for t, v in by_task.items() if not any(v)),
    }


def _median(vals):
    vals = sorted(v for v in vals if v)
    if not vals:
        return 0.0
    m = len(vals) // 2
    return vals[m] if len(vals) % 2 else (vals[m - 1] + vals[m]) / 2


def _pct(x) -> str:
    return "-" if x is None else f"{round(x * 100):d}%"


def render(summaries: list[dict]) -> str:
    summaries = [s for s in summaries if s.get("n")]
    if not summaries:
        return "_No results yet._\n"
    summaries.sort(key=lambda s: (-s["solved"], -s["solved_any"]))

    w = max(len(s["model"]) for s in summaries)
    head = (
        f"| {'Model'.ljust(w)} | solved | tests green | any | operates tools | "
        "reads the spec | green but wrong | false done | steps | tok/s |"
    )
    rule = (
        f"|{'-' * (w + 2)}|--------|-------------|-----|----------------|"
        "----------------|-----------------|------------|-------|-------|"
    )
    lines = [head, rule]
    for s in summaries:
        lines.append(
            f"| {s['model'].ljust(w)} | {_pct(s['solved']):>6} | "
            f"{_pct(s['visible_solved']):>11} | {_pct(s['solved_any']):>3} | "
            f"{_pct(s['operates']):>14} | {_pct(s['reads_spec']):>14} | "
            f"{s['false_green']:>15} | {s['false_done']:>10} | "
            f"{_pct(s['steps_used']):>5} | {s['tok_per_s']:>5.1f} |"
        )

    n_tasks = max(s["n_tasks"] for s in summaries)
    reps = sorted({max(1, s["n"] // max(1, s["n_tasks"])) for s in summaries})
    # Models are not all run the same number of times -- a model at 0.3 tok/s
    # costs a day for a single pass -- so say so rather than quoting the
    # largest and letting it read as though it applied to every row.
    if len(reps) == 1:
        sample = f"{n_tasks} task(s) x {reps[0]} attempt(s) per model."
    else:
        sample = (
            f"{n_tasks} task(s); attempts per model vary "
            f"({reps[0]}-{reps[-1]}), so a row with fewer attempts resolves "
            "less. Per-model counts are in the notes below."
        )
    lines += [
        "",
        "### Reading these numbers",
        "",
        f"Sample: {sample}",
        "",
        "**solved** is the score, and it is the only column that is. It is the",
        "fraction of attempts where the **held-out** suite passes against the",
        "project the model left behind. The model never sees or runs that suite.",
        "Everything else explains how.",
        "",
        "- **tests green** — the suite the model *could* run, passing at the end.",
        "  This is what the model thinks it achieved.",
        "- **green but wrong** — attempts where *tests green* and *solved*",
        "  disagree: every signal the model had said done, and the held-out",
        "  suite says no. The visible tests report the symptoms; the held-out",
        "  ones check the rules that only the spec states, so this column counts",
        "  the fixes that satisfied the symptoms without reading why. It is the",
        "  closest thing here to how real work goes wrong.",
        "- **any** — tasks solved by at least one attempt. The gap from *solved*",
        "  measures consistency.",
        "- **operates tools** — four fifths of calls in the tool-call field, four",
        "  fifths not refused, at least three distinct tools. A floor, not a",
        "  skill: below it, nothing else in the row means anything.",
        "- **verifies** — ran the tests at least once. A model that edits blind",
        "  is guessing even when it guesses right.",
        "- **reads the spec** — on tasks with a requirement stated only in prose,",
        "  whether it opened the file holding it. Nothing points it there.",
        "- **false done** — called `finish` with tests still failing: it believed",
        "  it was done and was not. The agentic failure that costs most in real",
        "  use, and the one no amount of re-running the evidence can catch.",
        "- **steps** — fraction of the step budget spent. Low with a high score",
        "  is a model that knew when it was done; high with a low score is one",
        "  that wandered until it was stopped.",
        "",
    ]
    for s in summaries:
        notes = []
        if s["false_green"]:
            notes.append(
                f"**{s['false_green']} attempt(s) went green on every test they "
                "could run and still failed the held-out suite**"
            )
        if s["false_done"]:
            notes.append(
                f"**{s['false_done']} attempt(s) declared done with tests failing**"
            )
        if s["regressed"]:
            notes.append(f"{s['regressed']} attempt(s) had it green and then broke it")
        if s["call_error_rate"] > 0.05:
            if s["protocol"] == "text":
                notes.append(
                    f"{_pct(s['call_error_rate'])} of calls were not fenced as "
                    "the prompt asked (parsed anyway; a formatting deviation, "
                    "not a channel failure)"
                )
            else:
                notes.append(
                    f"{_pct(s['call_error_rate'])} of calls were malformed or named no "
                    f"tool ({s['out_of_band']} written in the reply text rather "
                    "than as a tool call)"
                )
        if s["no_call"]:
            notes.append(f"{s['no_call']} attempt(s) ended with prose instead of a call")
        if s["api_errors"]:
            notes.append(f"{s['api_errors']} attempt(s) ended on a server error")
        if s["repeats"]:
            notes.append(f"{s['repeats']} call(s) repeated a call already made")
        if s.get("truncated"):
            notes.append(
                f"{s['truncated']} call(s) ran out of tokens mid-argument "
                "(tried to send a whole file)"
            )
        if s["edit_failures"]:
            notes.append(f"{s['edit_failures']} edit(s) were refused")
        if s.get("compactions"):
            notes.append(
                f"{s['compactions']} history compaction(s) -- conversations "
                "outgrew the window and older results were summarised"
            )
        notes.append(
            f"{s['n']} attempt(s) over {s['n_tasks']} task(s); "
            f"{s['edits']:.1f} edits and {s['test_runs']:.1f} test runs per attempt"
        )
        if s["never_solved"]:
            notes.append("never solved: " + ", ".join(s["never_solved"]))
        lines.append(f"**{s['model']}** ({s['protocol']} tool calls) -- " + "; ".join(notes))
    return "\n".join(lines) + "\n"


def build_report(results_dir: Path | None = None) -> str:
    d = results_dir or RESULTS_DIR
    summaries = []
    if d.is_dir():
        for p in sorted(d.glob("*.jsonl")):
            meta, rows = load_run(p)
            if meta.get("suite") != "agentic":
                continue
            summaries.append(summarise(meta, rows))
    return render(summaries)
