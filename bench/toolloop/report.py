"""Summarise tool-loop runs on the four axes the episodes probe.

There is no single number here on purpose. A model that works the tools
flawlessly and asks the wrong question is not "half as good" as one that does
both; it is a different failure, and averaging the two into one score is how a
benchmark ends up saying a model is usable when it is not.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

RESULTS_DIR = Path(__file__).resolve().parent.parent.parent / "results" / "toolloop"


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


def _mean(vals) -> float:
    vals = list(vals)
    return sum(vals) / len(vals) if vals else 0.0


def summarise(meta: dict, results: list[dict]) -> dict:
    if not results:
        return {"model": meta.get("model", "?"), "n": 0}

    doc_eps = [r for r in results if r.get("documents_relevant")]
    guarded = [r for r in results if r.get("guard_hits")]
    by_ep: dict[str, list[bool]] = defaultdict(list)
    for r in results:
        by_ep[r["episode_id"]].append(bool(r.get("target_hit")))

    calls = sum(r.get("calls_total", 0) for r in results)
    bad = sum(r.get("calls_malformed", 0) + r.get("calls_unknown_tool", 0) for r in results)
    refused = sum(r.get("calls_refused", 0) for r in results)

    return {
        "model": meta.get("model", "?"),
        "protocol": meta.get("protocol", "?"),
        "n": len(results),
        "n_episodes": len(by_ep),
        # The four axes, each a rate over attempts.
        "operates": _mean(bool(r.get("operates_tools")) for r in results),
        # Only episodes where the guard actually fired can measure recovery.
        "shapes": _mean(
            r.get("guard_recovered", 0) > 0 for r in guarded
        ) if guarded else None,
        "question": _mean(bool(r.get("target_hit")) for r in results),
        "seeks": _mean(bool(r.get("read_document")) for r in doc_eps) if doc_eps else None,
        # Diagnostics.
        "voluntary_stop": _mean(r.get("stopped") == "finish" for r in results),
        "steps_used": _mean(r.get("steps", 0) / max(1, r.get("budget", 1)) for r in results),
        "call_error_rate": bad / calls if calls else 0.0,
        "refusal_rate": refused / calls if calls else 0.0,
        "out_of_band": sum(r.get("calls_malformed", 0) for r in results),
        "repeats": sum(r.get("calls_repeated", 0) for r in results),
        "distinct_tools": _mean(r.get("distinct_tools", 0) for r in results),
        "no_call": sum(1 for r in results if r.get("stopped") == "no_call"),
        "api_errors": sum(1 for r in results if r.get("stopped") == "error"),
        "findings_rejected": sum(r.get("findings_rejected", 0) for r in results),
        "wrong_premise": sum(1 for r in results if r.get("anti_target_hit")),
        "guard_stuck": sum(
            1 for r in guarded if not r.get("guard_recovered")
        ),
        "total_min": sum(r.get("wall_s", 0) for r in results) / 60,
        "never_hit": sorted(e for e, v in by_ep.items() if not any(v)),
    }


def _pct(x) -> str:
    return "-" if x is None else f"{100 * x:.0f}%"


_NOTE = """### Reading these numbers

Sample: {sample}.

These are four separate questions, not one score, and they are ordered the way
a model fails them. A model that cannot work the tools never gets far enough to
ask a wrong question; a model that asks the right question without being
pushed to the information is doing something the first three columns cannot
show.

- **operates tools** — four fifths of its calls arrived in the tool-call field
  rather than the reply text, four fifths came back with an answer rather than
  a refusal, and it reached for at least three different tools. A floor, not a
  skill: a model below it is unusable in a loop regardless of anything else.
- **not confused by shapes** — of the attempts where a sampled *shape* was used
  as if it were a value and refused, the fraction that then did something
  different and got an answer. Blank means the trap was never sprung, which is
  a pass by a different route.
- **asks the right question** — the fraction of episodes where the defect was
  established: a recorded finding whose re-run query is about the right column
  and returns the right number. This is the score.
- **seeks out information** — of the episodes whose answer is only in a
  supplied document, the fraction where any document was opened.

`steps` is the fraction of the step budget spent. Low with a high score is a
model that knew when it was done; high with a low score is one that wandered
until it was stopped.
"""


def render(summaries: list[dict]) -> str:
    summaries = [s for s in summaries if s.get("n")]
    if not summaries:
        return (
            "No tool-loop results yet. Run "
            "`python3 -m bench toolloop --label <model>` first.\n"
        )
    summaries.sort(key=lambda s: (-s["question"], -s["operates"]))

    head = [
        "Model",
        "operates tools",
        "not confused by shapes",
        "asks the right question",
        "seeks out information",
        "steps",
    ]
    rows = [
        [
            s["model"],
            _pct(s["operates"]),
            _pct(s["shapes"]),
            _pct(s["question"]),
            _pct(s["seeks"]),
            _pct(s["steps_used"]),
        ]
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

    shapes = {(s["n_episodes"], s["n"]) for s in summaries}
    if len(shapes) == 1:
        eps, att = shapes.pop()
        sample = f"{eps} episodes x {att // eps if eps else 0} attempt(s) per model"
    else:
        sample = "; ".join(f"{s['model']}: {s['n']} attempts" for s in summaries)

    out.append("")
    out.append(_NOTE.format(sample=sample))

    for s in summaries:
        notes = []
        if s["wrong_premise"]:
            notes.append(
                f"**{s['wrong_premise']} attempt(s) recorded the wrong-premise answer** "
                f"-- a verified finding that answers a question nobody asked; "
                f"re-running the evidence cannot catch this"
            )
        if s["no_call"]:
            notes.append(f"{s['no_call']} episode(s) ended with prose instead of a tool call")
        if s["api_errors"]:
            notes.append(f"{s['api_errors']} episode(s) ended on an API error")
        if s["guard_stuck"]:
            notes.append(f"{s['guard_stuck']} episode(s) hit the shape guard and never adapted")
        if s["call_error_rate"] > 0.05:
            notes.append(
                f"{_pct(s['call_error_rate'])} of calls were malformed or named no tool"
                + (
                    f" ({s['out_of_band']} written in the reply text rather than as a tool call)"
                    if s["out_of_band"]
                    else ""
                )
            )
        if s["refusal_rate"] > 0.15:
            notes.append(f"{_pct(s['refusal_rate'])} of calls were refused by a tool")
        if s["repeats"]:
            notes.append(f"{s['repeats']} call(s) repeated a call already made")
        if s["findings_rejected"]:
            notes.append(
                f"{s['findings_rejected']} finding(s) rejected for claiming a number "
                f"their own evidence did not return"
            )
        notes.append(f"{s['voluntary_stop'] * 100:.0f}% of episodes ended voluntarily")
        notes.append(f"{s['distinct_tools']:.1f} distinct tools per episode")
        if s["never_hit"]:
            notes.append("never solved: " + ", ".join(s["never_hit"]))
        out.append(f"**{s['model']}** ({s['protocol']} tool calls) -- " + "; ".join(notes))

    return "\n".join(out) + "\n"


def build_report(results_dir: Path | None = None) -> str:
    results_dir = results_dir or RESULTS_DIR
    if not results_dir.exists():
        return render([])
    return render([summarise(*load_run(p)) for p in sorted(results_dir.glob("*.jsonl"))])
