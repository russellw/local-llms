"""Unit tests for the tool-loop scorer, run as part of `bench selfcheck`.

A grader nobody checks is worth nothing. The code-task half of this benchmark
guards itself by running every reference solution against its own tests; this
is the same guarantee for the half that has no reference solution to run.

Four scripted agents play the episodes:

    ideal       does the right thing            -> must score every axis
    wrong       asks a well-formed wrong question -> must hit the anti-target
                                                      and fail the episode
    spiral      repeats a refused call           -> must score zero, and be
                                                      visibly stuck
    mute        writes prose instead of calling  -> must end as no_call

If the scorer can be fooled by any of them, that shows up here rather than in a
table of model results nobody can check.
"""

from __future__ import annotations

import json

from ..client import Completion
from . import world
from .episodes import load_episodes
from .loop import run_episode


class ScriptedClient:
    """A model replaced by a fixed list of calls, in the native tool shape."""

    def __init__(self, script):
        self.script = list(script)
        self.i = 0

    def complete(self, messages, **kw) -> Completion:
        if self.i >= len(self.script):
            return Completion("(out of script)", 0.01, message={"role": "assistant", "content": "(out of script)"})
        item = self.script[self.i]
        self.i += 1
        if isinstance(item, str):  # prose, no call
            return Completion(item, 0.01, message={"role": "assistant", "content": item})
        tool, args = item
        return Completion(
            "",
            0.01,
            message={
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": f"c{self.i}",
                        "type": "function",
                        "function": {"name": tool, "arguments": json.dumps(args)},
                    }
                ],
            },
        )


class OutOfBandClient(ScriptedClient):
    """Emits the same calls as prose in the reply, the way a small model does.

    Observed, not hypothetical: qwen2.5-coder-1.5b gets the tool name and every
    argument right and then wraps the object in a markdown fence instead of the
    `<tool_call>` tags its own chat template asked for.
    """

    def complete(self, messages, **kw) -> Completion:
        comp = super().complete(messages, **kw)
        calls = comp.message.get("tool_calls") or []
        if not calls:
            return comp
        fn = calls[0]["function"]
        body = json.dumps({"name": fn["name"], "arguments": json.loads(fn["arguments"])})
        text = f"```json\n{body}\n```"
        return Completion(text, 0.01, message={"role": "assistant", "content": text})


def _finding(tool, args, expected):
    return (
        "record_finding",
        {
            "title": "a defect",
            "evidence_tool": tool,
            "evidence_args": args,
            "expected": str(expected),
        },
    )


_IDEAL = {
    "basics": [
        ("list_tables", {}),
        ("describe_table", {"table": "readings"}),
        _finding("count_rows", {"table": "readings", "column": "kwh", "op": "<", "value": "0"}, 3),
        ("finish", {"summary": "3 negative readings"}),
    ],
    "shapes": [
        ("describe_table", {"table": "premises"}),
        ("sample_column", {"table": "premises", "column": "address"}),
        _finding("count_rows", {"table": "premises", "column": "address", "op": "blank"}, 2),
        ("finish", {"summary": "2 blank addresses"}),
    ],
    "dictionary": [
        ("list_documents", {}),
        ("read_document", {"name": "data-dictionary"}),
        ("distinct_values", {"table": "readings", "column": "status"}),
        _finding(
            "count_rows",
            {"table": "readings", "column": "status", "op": "not_in", "value": "ACTUAL,ESTIMATED,CUSTOMER"},
            6,
        ),
        ("finish", {"summary": "6 undocumented states"}),
    ],
    "premise": [
        ("list_documents", {}),
        ("read_document", {"name": "data-dictionary"}),
        _finding(
            "check_orphans",
            {
                "left_table": "readings",
                "left_column": "site_ref",
                "right_table": "premises",
                "right_column": "upn",
                "left_strip": "SITE-",
                "right_strip": "UPN-",
            },
            4,
        ),
        ("finish", {"summary": "4 genuine orphans"}),
    ],
}

# The failure that evidence re-execution cannot catch: a correct answer to the
# wrong question. It verifies, it records, and it is wrong.
_WRONG_PREMISE = [
    ("describe_table", {"table": "readings"}),
    _finding(
        "check_orphans",
        {
            "left_table": "readings",
            "left_column": "site_ref",
            "right_table": "premises",
            "right_column": "upn",
        },
        14,
    ),
    ("finish", {"summary": "every reading is an orphan"}),
]

# Asks for a redacted shape as though it were a value, then keeps asking.
_SPIRAL = [("sample_column", {"table": "premises", "column": "address"})] + [
    ("count_rows", {"table": "premises", "column": "address", "op": "=", "value": "AAAA 9999"})
] * 6

_MUTE = ["I would start by looking at the premises table."] * 4


def run() -> list[str]:
    """Return a list of failure descriptions; empty means everything passed."""
    fails = []
    eps = {e.id: e for e in load_episodes()}

    if set(eps) != set(_IDEAL):
        fails.append(f"selftest scripts cover {sorted(_IDEAL)}, episodes are {sorted(eps)}")

    for eid, script in _IDEAL.items():
        if eid not in eps:
            continue
        res, _ = run_episode(ScriptedClient(script), eps[eid])
        if not res.target_hit:
            fails.append(f"toolloop [{eid}]: the ideal agent did not hit the target")
        if not res.passed:
            fails.append(f"toolloop [{eid}]: the ideal agent did not pass")
        if res.stopped != "finish":
            fails.append(f"toolloop [{eid}]: ideal agent stopped as {res.stopped}, want finish")
        if res.findings_rejected:
            fails.append(f"toolloop [{eid}]: ideal agent had {res.findings_rejected} finding(s) rejected")
        if not res.operates_tools:
            fails.append(f"toolloop [{eid}]: ideal agent failed operates_tools ({res.tools_used})")
        if res.anti_target_hit:
            fails.append(f"toolloop [{eid}]: ideal agent tripped the anti-target")
        if eps[eid].documents_relevant and not res.read_document:
            fails.append(f"toolloop [{eid}]: ideal agent never read a document")

    res, _ = run_episode(ScriptedClient(_WRONG_PREMISE), eps["premise"])
    if res.target_hit:
        fails.append("toolloop [premise]: the wrong-premise agent was scored as correct")
    if not res.anti_target_hit:
        fails.append("toolloop [premise]: the wrong-premise agent did not trip the anti-target")
    if res.findings_verified != 1:
        fails.append(
            "toolloop [premise]: the wrong-premise finding should still verify "
            f"(got {res.findings_verified} verified) -- that is the whole point of it"
        )

    res, _ = run_episode(ScriptedClient(_SPIRAL), eps["shapes"])
    if res.target_hit:
        fails.append("toolloop [shapes]: the spiralling agent was scored as correct")
    if res.guard_hits == 0:
        fails.append("toolloop [shapes]: the shape guard never fired on a shape query")
    if res.guard_recovered:
        fails.append("toolloop [shapes]: a spiralling agent was credited with recovering")
    if res.calls_repeated < 4:
        fails.append(f"toolloop [shapes]: repeated calls undercounted ({res.calls_repeated})")
    if res.stopped != "budget":
        fails.append(f"toolloop [shapes]: spiral stopped as {res.stopped}, want budget")

    res, _ = run_episode(ScriptedClient(_MUTE), eps["basics"])
    if res.stopped != "no_call":
        fails.append(f"toolloop [basics]: prose-only agent stopped as {res.stopped}, want no_call")
    if res.calls_total:
        fails.append("toolloop [basics]: prose was counted as a call")
    if res.operates_tools:
        fails.append("toolloop [basics]: a model that never called a tool operates_tools")

    # A model that writes its calls into the reply text instead of the tool-call
    # field must still be measured -- but must not be credited with operating
    # the tools, because a real agent client would have seen nothing at all.
    res, _ = run_episode(OutOfBandClient(_IDEAL["basics"]), eps["basics"])
    if not res.target_hit:
        fails.append("toolloop [basics]: an out-of-band call was not salvaged")
    if res.calls_malformed != res.calls_total:
        fails.append(
            f"toolloop [basics]: out-of-band calls not all counted as malformed "
            f"({res.calls_malformed} of {res.calls_total})"
        )
    if res.operates_tools:
        fails.append(
            "toolloop [basics]: a model whose every call was written in the reply "
            "text was credited with operating the tools"
        )

    # A model that recovers after the guard must be told apart from one that does not.
    recovering = [
        ("sample_column", {"table": "premises", "column": "address"}),
        ("count_rows", {"table": "premises", "column": "address", "op": "=", "value": "AAAA 9999"}),
        _finding("count_rows", {"table": "premises", "column": "address", "op": "blank"}, 2),
        ("finish", {"summary": "2 blank"}),
    ]
    res, _ = run_episode(ScriptedClient(recovering), eps["shapes"])
    if not (res.guard_hits == 1 and res.guard_recovered == 1):
        fails.append(
            f"toolloop [shapes]: recovery not detected (hits={res.guard_hits}, "
            f"recovered={res.guard_recovered})"
        )
    if not res.target_hit:
        fails.append("toolloop [shapes]: a recovering agent should still pass")

    # A finding whose evidence contradicts its claim must not be kept.
    lying = [
        _finding("count_rows", {"table": "readings", "column": "kwh", "op": "<", "value": "0"}, 99),
        ("finish", {"summary": "done"}),
    ]
    res, _ = run_episode(ScriptedClient(lying), eps["basics"])
    if res.findings_verified or res.target_hit:
        fails.append("toolloop [basics]: an invented number was recorded")
    if res.findings_rejected != 1:
        fails.append("toolloop [basics]: the invented number was not rejected")

    # Equivalent phrasings of the same question must score the same.
    equivalent = [
        _finding("count_rows", {"table": "readings", "column": "kwh", "op": "<=", "value": "-0.01"}, 3),
        ("finish", {"summary": "done"}),
    ]
    res, _ = run_episode(ScriptedClient(equivalent), eps["basics"])
    if not res.target_hit:
        fails.append("toolloop [basics]: an equivalent query was not credited")

    fails += _parse_checks()
    fails += _world_checks()
    return fails


def _parse_checks() -> list[str]:
    """Shapes the text protocol has actually been handed by a real model."""
    from . import protocol

    fails = []
    cases = [
        ("fenced", '```json\n{"tool": "list_tables", "args": {}}\n```', "list_tables", {}),
        (
            "args beside the name",
            '```json\n{"tool": "finish", "summary": "no blanks"}\n```',
            "finish",
            {"summary": "no blanks"},
        ),
        (
            "openai shape with stringified arguments",
            '```json\n{"name": "count_rows", "arguments": "{\\"table\\": \\"readings\\"}"}\n```',
            "count_rows",
            {"table": "readings"},
        ),
        ("unfenced object", 'Sure: {"tool": "list_tables", "args": {}}', "list_tables", {}),
    ]
    for name, text, want_tool, want_args in cases:
        out = protocol.parse_text(text)
        if not out.calls:
            fails.append(f"toolloop parse [{name}]: nothing parsed")
            continue
        c = out.calls[0]
        if c.tool != want_tool or c.args != want_args:
            fails.append(
                f"toolloop parse [{name}]: got {c.tool}({c.args}), want {want_tool}({want_args})"
            )

    for name, text in [("prose", "I think it looks fine."), ("unclosed reasoning", "<think>hmm")]:
        if protocol.parse_text(text).calls:
            fails.append(f"toolloop parse [{name}]: prose was read as a call")
    return fails


def _world_checks() -> list[str]:
    """The planted defects must still be the ones the episodes expect."""
    fails = []
    expected = [
        ("negative kwh", world.count_rows("readings", "kwh", "<", "0"), 3),
        ("undocumented status", world.count_rows("readings", "status", "not_in", "ACTUAL,ESTIMATED,CUSTOMER"), 6),
        ("blank address", world.count_rows("premises", "address", "blank"), 2),
        ("orphans, literal", world.check_orphans("readings", "site_ref", "premises", "upn"), 14),
        (
            "orphans, prefixes stripped",
            world.check_orphans("readings", "site_ref", "premises", "upn", "SITE-", "UPN-"),
            4,
        ),
    ]
    for name, payload, want in expected:
        got = world.result_value("", payload)
        if got != want:
            fails.append(f"toolloop world [{name}]: got {got}, episodes expect {want}")

    # The document is the only place the prefix rule is written down; if that
    # stops being true the initiative axis stops measuring anything.
    doc = world.DOCUMENTS["data-dictionary"][1]
    for needle in ("SITE-", "UPN-", "ACTUAL", "ESTIMATED", "CUSTOMER"):
        if needle not in doc:
            fails.append(f"toolloop world: data-dictionary no longer states {needle!r}")

    # An episode's answer must not collide with the number a model would get by
    # the wrong reasoning, or the axis scores luck instead of judgment.
    undocumented = world.result_value("", world.count_rows("readings", "status", "not_in", "ACTUAL,ESTIMATED,CUSTOMER"))
    distinct = world.result_value("", world.distinct_values("readings", "status"))
    if undocumented == distinct:
        fails.append(
            f"toolloop world: the dictionary answer ({undocumented}) equals the "
            f"distinct-status count, so counting the states without reading the "
            f"document would score as correct"
        )

    literal = world.result_value("", world.check_orphans("readings", "site_ref", "premises", "upn"))
    stripped = world.result_value("", world.check_orphans("readings", "site_ref", "premises", "upn", "SITE-", "UPN-"))
    if literal == stripped:
        fails.append(
            "toolloop world: the premise episode no longer distinguishes the "
            "literal join from the documented one"
        )

    try:
        world.distinct_values("premises", "address")
        fails.append("toolloop world: a high-cardinality column was released verbatim")
    except world.ToolError:
        pass

    if not world.looks_like_shape("AAAA 9999") or world.looks_like_shape("ACTUAL"):
        fails.append("toolloop world: the shape detector misclassifies")
    return fails
