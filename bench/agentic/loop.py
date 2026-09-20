"""Drive one task and score it.

**The ground truth is the hidden test suite.** A task is passed when the suite
passes against the project the model leaves behind -- not when the model says
it is done, and not when some intermediate run went green. Everything else
here is a diagnostic that explains *how* a model passed or failed, and none of
it contributes to that verdict.

**Prose is never scored.** Summaries go to the transcript for a human to read.

One deliberate asymmetry, inherited from the loop this replaces: a malformed
call that can still be salvaged is executed, so a model is not penalised twice
for one mistake, but the salvage is counted. In a real agent the strict parser
on the other end would have rejected it, and `calls_malformed` is what says how
often that would have happened.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict

from ..client import ChatClient
from .. import toolcall
from .tasks import Task
from .tools import TOOL_SPECS, TOOL_NAMES, TEXT_EXAMPLE, ToolError, Workspace

MAX_CALLS_PER_STEP = 2

_NUDGE = (
    "That was not a tool call. Reply with a tool call and nothing else, using "
    "the form you were given."
)

_TRUNCATED = (
    "Your last tool call was cut off before it finished and could not be read. "
    "That usually means you tried to send a whole file at once. Use "
    "replace_in_file and quote only the lines you are changing."
)

# A model that overruns its token budget in the middle of a tool call makes the
# server reject its own output. That is the model overreaching, not the harness
# failing, so it is counted as a malformed call and the attempt carries on --
# ending the task on it would score a recoverable mistake as a dead run.
_TRUNCATED_HINTS = (
    "parse tool call",
    "tool call arguments",
    "parse_error",
    "invalid string",
    "missing closing quote",
)


def _is_truncated_call(err: str) -> bool:
    low = (err or "").lower()
    return any(h in low for h in _TRUNCATED_HINTS)

SYSTEM = """
You are fixing a small Python project. The project is on disk and you change it
by calling tools -- you cannot see or edit the test suite, but you can run it as
often as you like and it will tell you what is failing.

Work like this: look at what is there, read the code, run the tests to see where
you stand, make a change, run them again. When the suite passes, call finish.

Change existing code with replace_in_file, quoting just the lines you are
changing. write_file is for creating a new file: using it to re-send a whole
file you have already read wastes most of your budget on retyping code that was
already correct.

Everything the task requires is somewhere in the project. If the code alone does
not tell you what a function is supposed to do, something else in the project
will.
""".strip()


@dataclass
class TaskResult:
    task_id: str
    difficulty: str = ""
    passed: bool = False

    steps: int = 0
    budget: int = 0
    stopped: str = "budget"  # finish | budget | no_call | error

    calls_total: int = 0
    calls_ok: int = 0
    calls_malformed: int = 0
    calls_unknown_tool: int = 0
    calls_refused: int = 0
    calls_repeated: int = 0
    calls_truncated: int = 0
    distinct_tools: int = 0
    tools_used: list[str] = field(default_factory=list)

    # Process, not outcome.
    edits_made: int = 0
    edits_failed: int = 0
    files_read: int = 0
    read_before_edit: bool = False
    read_spec: bool = False
    spec_relevant: bool = False
    test_runs: int = 0
    tests_ever_green: bool = False
    finished_unverified: bool = False
    regressed: bool = False

    first_green_step: int = 0
    tests_failed_at_end: int = 0
    tests_total: int = 0

    wall_s: float = 0.0
    completion_tokens: int = 0
    tok_per_s: float = 0.0
    error: str = ""

    @property
    def operates_tools(self) -> bool:
        """Can it work the instrument at all. A floor, not a skill.

        Four fifths of calls in the channel, four fifths not refused, and at
        least three distinct tools reached for. A model below this is unusable
        in a loop regardless of how well it writes Python.
        """
        if self.calls_total < 3:
            return False
        in_channel = (self.calls_total - self.calls_malformed) / self.calls_total
        answered = (self.calls_total - self.calls_refused) / self.calls_total
        return in_channel >= 0.8 and answered >= 0.8 and self.distinct_tools >= 3

    def to_dict(self) -> dict:
        d = asdict(self)
        d["operates_tools"] = self.operates_tools
        return d


def _describe(outcome) -> str:
    if outcome.timed_out or outcome.crashed:
        return outcome.report
    head = (
        f"{outcome.total - outcome.failed}/{outcome.total} tests passed"
        if outcome.total
        else "tests ran"
    )
    return head + (("\n" + outcome.report) if outcome.report else "")


def run_task(
    client: ChatClient,
    task: Task,
    protocol_mode: str = "native",
    temperature: float = 0.0,
    seed: int = 0,
    max_tokens_scale: float = 1.0,
) -> tuple[TaskResult, list[dict]]:
    res = TaskResult(task_id=task.id, difficulty=task.difficulty, budget=task.budget)
    res.spec_relevant = bool(task.spec_file)
    transcript: list[dict] = []
    ws = Workspace(task.project_dir, task.tests_dir, timeout=task.test_timeout)

    native = protocol_mode == "native"
    system = SYSTEM if native else (
        SYSTEM + "\n\n" + toolcall.text_protocol(TOOL_SPECS, TEXT_EXAMPLE)
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": task.brief},
    ]
    tools = toolcall.openai_tools(TOOL_SPECS) if native else None

    seen_calls: set[str] = set()
    tools_used: list[str] = []
    consecutive_errors = 0
    t0 = time.monotonic()
    max_tokens = int(task.max_tokens * max_tokens_scale)

    try:
        for step in range(1, task.budget + 1):
            res.steps = step
            comp = client.complete(
                messages,
                temperature=temperature,
                max_tokens=max_tokens,
                seed=seed,
                tools=tools,
            )
            if comp.error:
                consecutive_errors += 1
                if _is_truncated_call(comp.error):
                    res.calls_total += 1
                    res.calls_malformed += 1
                    res.calls_truncated += 1
                    transcript.append(
                        {"step": step, "text": "", "calls": [],
                         "results": ["(tool call was cut off mid-argument)"]}
                    )
                    messages.append({"role": "user", "content": _TRUNCATED})
                    consecutive_errors = 0  # recoverable, and it was told how
                elif consecutive_errors >= 3:
                    res.stopped = "error"
                    res.error = comp.error
                    break
                continue
            consecutive_errors = 0
            res.completion_tokens += getattr(comp, "completion_tokens", 0) or 0

            parsed = (
                toolcall.parse_native(comp.message)
                if native
                else toolcall.parse_text(toolcall.message_text(comp.message) or comp.text)
            )
            entry = {"step": step, "text": parsed.text, "calls": [], "results": []}

            if not parsed.calls:
                transcript.append(entry)
                messages.append(comp.message or {"role": "assistant", "content": comp.text})
                messages.append({"role": "user", "content": _NUDGE})
                if step >= 2 and not any(t["calls"] for t in transcript[-2:]):
                    res.stopped = "no_call"
                    break
                continue

            messages.append(comp.message or {"role": "assistant", "content": comp.text})
            done = False
            for n, call in enumerate(parsed.calls):
                # Every call in the message gets an answer, even the ones past
                # the per-step cap. A tool_call_id left without a reply makes
                # the *next* request malformed, which would end the attempt on
                # a server error and score it as the model's failure.
                if n >= MAX_CALLS_PER_STEP:
                    _reply(
                        messages,
                        native,
                        call,
                        "not executed: one tool call per reply, please.",
                    )
                    continue
                res.calls_total += 1
                if call.malformed:
                    res.calls_malformed += 1
                entry["calls"].append({"tool": call.tool, "args": _trim(call.args)})

                if call.tool not in TOOL_NAMES:
                    res.calls_unknown_tool += 1
                    out = f"no such tool: {call.tool}. Available: {', '.join(TOOL_NAMES)}"
                    entry["results"].append(out)
                    _reply(messages, native, call, out)
                    continue

                key = call.tool + json.dumps(call.args, sort_keys=True, default=str)
                if key in seen_calls:
                    res.calls_repeated += 1
                seen_calls.add(key)
                if call.tool not in tools_used:
                    tools_used.append(call.tool)

                try:
                    out, finished = _dispatch(ws, task, call, res, step)
                except ToolError as e:
                    res.calls_refused += 1
                    out, finished = str(e), False
                else:
                    res.calls_ok += 1

                entry["results"].append(out)
                _reply(messages, native, call, out)
                if finished:
                    res.stopped = "finish"
                    done = True
                    break

            transcript.append(entry)
            if done:
                break

        # The verdict: the suite against whatever the model left behind.
        final = ws.run_tests()
        res.passed = final.ok
        res.tests_total = final.total
        res.tests_failed_at_end = final.failed
        if res.stopped == "finish" and not final.ok:
            res.finished_unverified = True
        if res.tests_ever_green and not final.ok:
            res.regressed = True
    finally:
        res.wall_s = time.monotonic() - t0
        res.distinct_tools = len(tools_used)
        res.tools_used = tools_used
        if res.wall_s > 0 and res.completion_tokens:
            res.tok_per_s = res.completion_tokens / res.wall_s
        ws.close()

    return res, transcript


def _dispatch(ws: Workspace, task: Task, call, res: TaskResult, step: int):
    """Run one tool. Returns (text for the model, whether the run is over)."""
    a = call.args
    if call.tool == "list_files":
        return ws.list_files(), False
    if call.tool == "read_file":
        path = str(a.get("path", ""))
        out = ws.read_file(path)
        res.files_read += 1
        if task.spec_file and _same_path(path, task.spec_file):
            res.read_spec = True
        return out, False
    if call.tool in ("write_file", "replace_in_file"):
        if res.files_read and res.edits_made == 0:
            res.read_before_edit = True
        if call.tool == "write_file":
            out = ws.write_file(str(a.get("path", "")), a.get("content"))
        else:
            out = ws.replace_in_file(
                str(a.get("path", "")), a.get("old"), a.get("new")
            )
        res.edits_made += 1
        return out, False
    if call.tool == "run_tests":
        outcome = ws.run_tests()
        res.test_runs += 1
        if outcome.ok:
            res.tests_ever_green = True
            if not res.first_green_step:
                res.first_green_step = step
        return _describe(outcome), False
    if call.tool == "finish":
        return "ended", True
    raise ToolError(f"no such tool: {call.tool}")


def _same_path(a: str, b: str) -> bool:
    norm = lambda s: s.strip().lstrip("./").lstrip("/").lower()
    return norm(a) == norm(b)


def _reply(messages: list[dict], native: bool, call, out: str) -> None:
    if native and call.call_id and not call.malformed:
        messages.append(
            {"role": "tool", "tool_call_id": call.call_id, "content": out}
        )
    else:
        messages.append({"role": "user", "content": out})


def _trim(args: dict) -> dict:
    """Keep the transcript readable: a whole-file write is not worth echoing."""
    out = {}
    for k, v in (args or {}).items():
        s = v if isinstance(v, str) else json.dumps(v, default=str)
        out[k] = s if len(s) <= 300 else s[:300] + f"... ({len(s)} chars)"
    return out
