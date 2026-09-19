"""Drive one episode and score it.

The scoring is the whole point of this file, so it is worth being explicit
about what is and is not counted.

**Counted:** whether the evidence a finding carries is about the right column
and returns the right number; whether a rejected call was followed by a
different one; whether the run ended because the model decided it had; which
tools were reached for at all.

**Not counted:** anything the model wrote in prose. Titles, summaries and
explanations are recorded in the transcript for a human to read and contribute
nothing to a score. A benchmark that grades text has to decide what a good
sentence is, and this one declines to.

One deliberate asymmetry: a malformed call that can still be salvaged is
executed, so a model is not penalised twice for one mistake, but the salvage is
counted. In a real agent the strict parser on the other end would have rejected
it, and `calls_malformed` is what says how often that would have happened.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict

from ..client import ChatClient
from . import protocol, world
from .episodes import Episode, Target

MAX_CALLS_PER_STEP = 4

_NUDGE = (
    "That was not a tool call. Reply with a tool call and nothing else, using "
    "the form you were given."
)


@dataclass
class EpisodeResult:
    episode_id: str
    axis: str
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
    distinct_tools: int = 0
    tools_used: list[str] = field(default_factory=list)

    guard_hits: int = 0
    guard_recovered: int = 0

    read_document: bool = False
    documents_relevant: bool = False

    findings_recorded: int = 0
    findings_verified: int = 0
    findings_rejected: int = 0

    target_hit: bool = False
    anti_target_hit: bool = False

    wall_s: float = 0.0
    completion_tokens: int = 0
    tok_per_s: float = 0.0
    error: str = ""

    @property
    def operates_tools(self) -> bool:
        """Can it work the instrument at all. Three conditions, all necessary.

        **Four fifths of its calls arrived in the channel.** A call written
        into the reply text is salvaged here so the rest of the episode can be
        measured, but the strict client at the other end of a real agent reads
        the tool-call field and would have seen an empty one. Crediting that as
        working tools would be scoring a capability the model does not have.

        **Four fifths came back with an answer rather than a refusal.** Being
        told no and asking again the same way is a mechanics failure as much as
        a comprehension one, so guard refusals count against this.

        **It reached for at least three different tools.** A model that only
        ever calls one tool is not operating the instrument even when every
        call succeeds -- the failure that turned up in a real audit as forty
        consecutive identical queries and nothing recorded.
        """
        if self.calls_total == 0:
            return False
        in_channel = (self.calls_total - self.calls_malformed) / self.calls_total
        answered = self.calls_ok / self.calls_total
        return in_channel >= 0.8 and answered >= 0.8 and self.distinct_tools >= 3

    def to_dict(self) -> dict:
        d = asdict(self)
        d["operates_tools"] = self.operates_tools
        return d


def _matches(target: Target, tool: str, args: dict, value) -> bool:
    """Does this evidence call establish the target defect?

    Matched on the columns the call names and the number it returns, not on the
    exact spelling of the call. `kwh < 0` and `kwh <= -0.01` are the same
    question and should score the same.
    """
    if target.tool and tool != target.tool:
        return False
    if not world.values_equal(target.value, value):
        return False
    named = set()
    a = {str(k).strip().lower(): str(v).strip().lower() for k, v in (args or {}).items()}
    if "table" in a and "column" in a:
        named.add(f"{a['table']}.{a['column']}")
    if "left_table" in a and "left_column" in a:
        named.add(f"{a['left_table']}.{a['left_column']}")
    if "right_table" in a and "right_column" in a:
        named.add(f"{a['right_table']}.{a['right_column']}")
    return all(m in named for m in target.mentions)


class _Session:
    """The mutable state of one episode, separated out so scoring can read it."""

    def __init__(self, ep: Episode):
        self.ep = ep
        self.res = EpisodeResult(
            episode_id=ep.id,
            axis=ep.axis,
            budget=ep.budget,
            documents_relevant=ep.documents_relevant,
        )
        self.seen_calls: set[tuple] = set()
        self.tools_used: list[str] = []
        self.pending_recovery = False
        self.transcript: list[dict] = []

    # -- tool dispatch ------------------------------------------------------

    def execute(self, call: protocol.ParsedCall) -> str:
        res = self.res
        res.calls_total += 1
        if call.malformed:
            res.calls_malformed += 1

        key = world.canonical(call.tool, call.args)
        if key in self.seen_calls:
            res.calls_repeated += 1
        self.seen_calls.add(key)

        name = call.tool.strip().lower()
        if name not in self.tools_used:
            self.tools_used.append(name)

        if name == "finish":
            res.calls_ok += 1
            return json.dumps({"ok": True, "note": "investigation closed"})

        if name == "record_finding":
            return self._record(call.args)

        fn = world.READ_TOOLS.get(name)
        if fn is None:
            res.calls_unknown_tool += 1
            return json.dumps(
                {
                    "error": f"no tool named {call.tool!r}",
                    "tools": protocol.TOOL_NAMES,
                }
            )

        try:
            out = self._invoke(fn, call.args)
        except world.ToolError as e:
            res.calls_refused += 1
            if "shape" in str(e):
                res.guard_hits += 1
                self.pending_recovery = True
            return json.dumps({"error": str(e)})
        except TypeError as e:
            res.calls_refused += 1
            return json.dumps({"error": f"wrong arguments for {name}: {e}"})

        res.calls_ok += 1
        if name == "read_document":
            res.read_document = True
        self._on_success()
        return out

    def _on_success(self) -> None:
        """A call that worked, after one was refused: the model adapted.

        Finishing does not count. Ending the run is how a stuck model gets out
        of a refusal loop, and crediting that as recovery would score giving up
        the same as working out what the refusal meant.
        """
        if self.pending_recovery:
            self.res.guard_recovered += 1
            self.pending_recovery = False

    @staticmethod
    def _invoke(fn, args: dict) -> str:
        clean = {str(k).strip().lower(): ("" if v is None else str(v)) for k, v in (args or {}).items()}
        allowed = fn.__code__.co_varnames[: fn.__code__.co_argcount]
        return fn(**{k: v for k, v in clean.items() if k in allowed})

    # -- record_finding: the evidence is re-run ------------------------------

    def _record(self, args: dict) -> str:
        res = self.res
        res.findings_recorded += 1
        a = {str(k).strip().lower(): v for k, v in (args or {}).items()}

        tool = str(a.get("evidence_tool") or "").strip().lower()
        fn = world.EVIDENCE_TOOLS.get(tool)
        if fn is None:
            res.findings_rejected += 1
            return json.dumps(
                {
                    "recorded": False,
                    "error": "evidence_tool must be one of "
                    + ", ".join(sorted(world.EVIDENCE_TOOLS)),
                }
            )

        ev_args, _ = protocol._coerce_args(a.get("evidence_args"))
        try:
            payload = self._invoke(fn, ev_args)
        except (world.ToolError, TypeError) as e:
            res.findings_rejected += 1
            return json.dumps({"recorded": False, "error": f"evidence did not run: {e}"})

        actual = world.result_value(tool, payload)
        claimed = a.get("expected")
        if not world.values_equal(claimed, actual):
            res.findings_rejected += 1
            return json.dumps(
                {
                    "recorded": False,
                    "error": "your evidence does not return what you claimed",
                    "you_expected": claimed,
                    "it_returned": actual,
                }
            )

        res.calls_ok += 1
        res.findings_verified += 1
        self._on_success()
        if _matches(self.ep.target, tool, ev_args, actual):
            res.target_hit = True
        if self.ep.anti_target and _matches(self.ep.anti_target, tool, ev_args, actual):
            res.anti_target_hit = True
        return json.dumps({"recorded": True, "verified": actual})


def run_episode(
    client: ChatClient,
    ep: Episode,
    protocol_mode: str = "native",
    temperature: float = 0.0,
    seed: int = 0,
    max_tokens_scale: float = 1.0,
) -> tuple[EpisodeResult, list[dict]]:
    """Play one episode to its end, and return the score and the transcript."""
    sess = _Session(ep)
    res = sess.res

    system = (
        "You are a careful data auditor. You investigate only through the tools "
        "you are given, and you never state a number you have not measured."
    )
    if protocol_mode == "text":
        system += "\n\n" + protocol.TEXT_PROTOCOL % protocol.text_tool_manual()

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": ep.brief},
    ]
    tools = protocol.openai_tools() if protocol_mode == "native" else None
    max_tokens = int(ep.max_tokens * max_tokens_scale)

    prose_strikes = 0
    rates: list[float] = []
    t0 = time.monotonic()

    for step in range(ep.budget):
        res.steps = step + 1
        comp = client.complete(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            seed=seed,
            tools=tools,
        )
        res.completion_tokens += comp.completion_tokens
        if comp.predict_per_s:
            rates.append(comp.predict_per_s)

        if comp.error:
            res.stopped, res.error = "error", comp.error
            break

        out = (
            protocol.parse_native(comp.message)
            if protocol_mode == "native"
            else protocol.parse_text(comp.text)
        )
        sess.transcript.append(
            {
                "step": step + 1,
                "text": comp.text,
                "calls": [{"tool": c.tool, "args": c.args} for c in out.calls],
            }
        )

        if not out.calls:
            prose_strikes += 1
            if prose_strikes >= 2:
                res.stopped = "no_call"
                break
            messages.append({"role": "assistant", "content": comp.text})
            messages.append({"role": "user", "content": _NUDGE})
            continue
        prose_strikes = 0

        calls, overflow = out.calls[:MAX_CALLS_PER_STEP], out.calls[MAX_CALLS_PER_STEP:]
        if protocol_mode == "native":
            messages.append(comp.message)
        else:
            messages.append({"role": "assistant", "content": comp.text})

        finished = False
        results = []
        for call in calls:
            payload = sess.execute(call)
            results.append((call, payload))
            if call.tool.strip().lower() == "finish":
                finished = True

        # Every tool call in the message needs a reply, including the ones over
        # the per-step cap, or the next request is malformed and the server
        # rejects the whole conversation.
        for call in overflow:
            results.append(
                (
                    call,
                    json.dumps(
                        {
                            "error": f"not executed: at most {MAX_CALLS_PER_STEP} "
                            f"calls per step, and this was call "
                            f"{len(calls) + overflow.index(call) + 1}"
                        }
                    ),
                )
            )

        if protocol_mode == "native":
            for call, payload in results:
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.call_id,
                        "name": call.tool,
                        "content": payload,
                    }
                )
        else:
            body = "\n".join(
                f"{c.tool} -> {p}" for c, p in results
            )
            messages.append({"role": "user", "content": body + "\n\nNext call."})

        if finished:
            res.stopped = "finish"
            break

    res.wall_s = time.monotonic() - t0
    res.tools_used = sess.tools_used
    res.distinct_tools = len(sess.tools_used)
    res.tok_per_s = sum(rates) / len(rates) if rates else 0.0

    # The episode's own objective: the right defect, established and kept.
    res.passed = res.target_hit
    return res, sess.transcript
