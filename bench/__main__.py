"""CLI: python3 -m bench <command>"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .client import ChatClient
from .report import build_report, RESULTS_DIR
from .runner import run_suite
from .tasks import load_tasks


def cmd_run(args) -> int:
    tasks = load_tasks(filters=args.task)
    if not tasks:
        print("No tasks matched.", file=sys.stderr)
        return 1

    # max_tokens is only a cap, so raising it costs nothing for a model that
    # stops on its own -- but a reasoning model that spends 2000 tokens thinking
    # gets cut off before it answers and scores a false zero without this.
    if args.max_tokens_scale != 1.0:
        for t in tasks:
            t.max_tokens = int(t.max_tokens * args.max_tokens_scale)

    client = ChatClient(base_url=args.url, model=args.model, timeout=args.timeout)
    if not client.health():
        print(f"No server responding at {args.url}", file=sys.stderr)
        print("Start one with: scripts/serve.sh <model.gguf>", file=sys.stderr)
        return 1

    # Greedy decoding is deterministic, so repeated attempts would return the
    # identical answer and burn hours proving nothing. Sampling is required for
    # repeats to measure anything.
    temperature = args.temperature
    if args.repeats > 1 and temperature == 0.0:
        temperature = 0.2
        print(
            f"note: --repeats {args.repeats} needs sampling to vary; "
            f"using temperature {temperature} instead of 0.0"
        )

    print(f"{len(tasks)} task(s) x {args.repeats} attempt(s) -> {args.label}\n")
    run_suite(
        client,
        tasks,
        model_label=args.label,
        repeats=args.repeats,
        temperature=temperature,
        resume=not args.fresh,
    )
    print()
    print(build_report())
    return 0


def cmd_report(args) -> int:
    text = build_report(Path(args.dir) if args.dir else None)
    print(text)
    if args.write:
        out = RESULTS_DIR / "REPORT.md"
        out.write_text("# Local LLM coding benchmark\n\n" + text)
        print(f"wrote {out}")
    return 0


def cmd_tasks(args) -> int:
    for t in load_tasks(filters=args.task):
        print(f"{t.id:24} {t.category:12} {t.difficulty:8} {t.title}")
    return 0


def cmd_selfcheck(args) -> int:
    """Run each task's reference solution against its own tests.

    A benchmark whose tests are wrong measures nothing, so this must stay green.
    """
    from .sandbox import run_python_tests
    from . import selftest

    bad = 0
    harness_fails = selftest.run()
    print(f"{'harness':24} {'ok' if not harness_fails else 'FAIL'}")
    for f in harness_fails:
        print(f"    {f}")
    bad += len(harness_fails)

    for t in load_tasks(filters=args.task):
        ref = t.reference
        if not ref:
            print(f"{t.id:24} NO REFERENCE")
            bad += 1
            continue
        res = run_python_tests(ref, t.tests, timeout=max(t.timeout, 60))
        print(f"{t.id:24} {'ok' if res.ok else 'FAIL'}")
        if not res.ok:
            bad += 1
            print("    " + (res.stdout + res.stderr).strip().replace("\n", "\n    "))
    print(f"\n{bad} problem(s)" if bad else "\nall references pass")
    return 1 if bad else 0


def main() -> int:
    p = argparse.ArgumentParser(prog="bench", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="run the suite against a running server")
    r.add_argument("--label", required=True, help="name for this model in results")
    r.add_argument("--url", default="http://127.0.0.1:8080")
    r.add_argument("--model", default="local", help="model name sent in the API call")
    r.add_argument("--task", action="append", help="task id or category (repeatable)")
    r.add_argument("--repeats", type=int, default=1)
    r.add_argument("--temperature", type=float, default=0.0)
    r.add_argument("--timeout", type=float, default=3600.0, help="per-request seconds")
    r.add_argument(
        "--max-tokens-scale",
        type=float,
        default=1.0,
        help="multiply every task's token budget (use ~3 for reasoning models)",
    )
    r.add_argument("--fresh", action="store_true", help="discard prior results")
    r.set_defaults(func=cmd_run)

    rp = sub.add_parser("report", help="summarise results/")
    rp.add_argument("--dir")
    rp.add_argument("--write", action="store_true", help="also write results/REPORT.md")
    rp.set_defaults(func=cmd_report)

    t = sub.add_parser("tasks", help="list tasks")
    t.add_argument("--task", action="append")
    t.set_defaults(func=cmd_tasks)

    sc = sub.add_parser("selfcheck", help="validate tasks against their references")
    sc.add_argument("--task", action="append")
    sc.set_defaults(func=cmd_selfcheck)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
