"""CLI: python3 -m bench <command>"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .agentic import detect_protocol, load_tasks, report, run_suite
from .client import ChatClient


def cmd_run(args) -> int:
    tasks = load_tasks(filters=args.task)
    if not tasks:
        print("No tasks matched.", file=sys.stderr)
        return 1

    client = ChatClient(base_url=args.url, model=args.model, timeout=args.timeout)
    if not client.health():
        print(f"No server responding at {args.url}", file=sys.stderr)
        print("Start one with: scripts/serve.sh <model.gguf>", file=sys.stderr)
        return 1

    mode = args.protocol
    if mode == "auto":
        mode = detect_protocol(client)
        if mode == "text":
            print(
                "note: this server rejected the `tools` parameter, so tool calls "
                "will be asked for as JSON in the reply instead. llama-server "
                "needs --jinja for native tool calls."
            )

    # Greedy decoding is deterministic, so repeated attempts would replay the
    # identical run and burn hours proving nothing.
    temperature = args.temperature
    if args.repeats > 1 and temperature == 0.0:
        temperature = 0.2
        print(
            f"note: --repeats {args.repeats} needs sampling to vary; "
            f"using temperature {temperature} instead of 0.0"
        )

    steps = sum(t.budget for t in tasks) * args.repeats
    print(
        f"{len(tasks)} task(s) x {args.repeats} attempt(s) -> {args.label} "
        f"({mode} tool calls, at most {steps} model turns)\n"
    )
    run_suite(
        client,
        tasks,
        model_label=args.label,
        protocol_mode=mode,
        repeats=args.repeats,
        temperature=temperature,
        max_tokens_scale=args.max_tokens_scale,
        resume=not args.fresh,
    )
    print()
    print(report.build_report())
    return 0


def cmd_report(args) -> int:
    text = report.build_report(Path(args.dir) if args.dir else None)
    print(text)
    if args.write:
        out = report.RESULTS_DIR / "REPORT.md"
        out.write_text("# Local LLM benchmark\n\n## Agentic coding\n\n" + text)
        print(f"wrote {out}")
    return 0


def cmd_tasks(args) -> int:
    for t in load_tasks(filters=args.task):
        spec = f"  spec in {t.spec_file}" if t.spec_file else ""
        print(f"{t.id:24} {t.difficulty:8} budget {t.budget:3}  {t.title}{spec}")
    return 0


def cmd_selfcheck(args) -> int:
    """Prove the suite still measures what it claims to.

    Every task's reference fix must pass its own hidden tests and the project
    as shipped must fail them; the workspace must keep the tests unreadable;
    and the scorer must still reject an agent that announces success without
    fixing anything.
    """
    from .agentic import selftest

    fails = selftest.run()
    for f in fails:
        print(f"  {f}")
    tasks = load_tasks()
    print(f"\n{len(tasks)} task(s) checked")
    print(f"{len(fails)} problem(s)" if fails else "all good")
    return 1 if fails else 0


def main() -> int:
    p = argparse.ArgumentParser(prog="bench", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="run the suite against a running server")
    r.add_argument("--label", required=True, help="name for this model in results")
    r.add_argument("--url", default="http://127.0.0.1:8080")
    r.add_argument("--model", default="local", help="model name sent in the API call")
    r.add_argument("--task", action="append", help="task id or difficulty (repeatable)")
    r.add_argument("--repeats", type=int, default=1)
    r.add_argument("--temperature", type=float, default=0.0)
    r.add_argument("--timeout", type=float, default=1800.0, help="per-request seconds")
    r.add_argument(
        "--protocol",
        choices=["auto", "native", "text"],
        default="auto",
        help="native uses the OpenAI tools parameter; text asks for JSON in the reply",
    )
    r.add_argument(
        "--max-tokens-scale",
        type=float,
        default=1.0,
        help="multiply every step's token budget (use ~3 for reasoning models)",
    )
    r.add_argument("--fresh", action="store_true", help="discard prior results")
    r.set_defaults(func=cmd_run)

    rep = sub.add_parser("report", help="rebuild the table from recorded results")
    rep.add_argument("--dir", help="results directory (default: results/)")
    rep.add_argument("--write", action="store_true", help="also write results/REPORT.md")
    rep.set_defaults(func=cmd_report)

    t = sub.add_parser("tasks", help="list the tasks")
    t.add_argument("--task", action="append")
    t.set_defaults(func=cmd_tasks)

    s = sub.add_parser("selfcheck", help="check the suite still measures what it claims")
    s.set_defaults(func=cmd_selfcheck)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
