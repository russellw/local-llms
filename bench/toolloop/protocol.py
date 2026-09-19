"""Two ways to ask a model for a tool call, and one way to read the answer.

`native` uses the OpenAI `tools` parameter and reads `message.tool_calls`. That
is how a real agent drives a model, so it is the default and the one whose
results transfer.

`text` describes the tools in the system prompt and asks for a JSON object in a
fenced block. It exists for servers that reject the `tools` parameter outright
-- not for models that are merely bad at using it, which is a thing this suite
is trying to measure rather than route around.

Parsing is deliberately forgiving and separately *counted*. A call that had to
be salvaged still executes, so a model is not scored down twice for one
mistake, but `malformed` records that the salvage happened, because in a real
loop the strict parser on the other end would have rejected it.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from ..extract import strip_reasoning

TOOL_SPECS: list[dict] = [
    {
        "name": "list_tables",
        "description": "List the tables in the dataset with their row counts.",
        "properties": {},
        "required": [],
    },
    {
        "name": "describe_table",
        "description": "Column names and distinct-value counts for one table.",
        "properties": {"table": "Table name."},
        "required": ["table"],
    },
    {
        "name": "sample_column",
        "description": (
            "Sample a column. Values come back redacted to their SHAPE "
            "(A=uppercase letter, a=lowercase letter, 9=digit, other characters "
            "literal). A shape describes the form of the data and never occurs "
            "in it, so a shape can never be used as a search value."
        ),
        "properties": {"table": "Table name.", "column": "Column name.", "n": "How many shapes to return."},
        "required": ["table", "column"],
    },
    {
        "name": "distinct_values",
        "description": (
            "The verbatim distinct values of a column, with row counts. Only "
            "permitted on columns marked samplable_verbatim by describe_table."
        ),
        "properties": {"table": "Table name.", "column": "Column name."},
        "required": ["table", "column"],
    },
    {
        "name": "count_rows",
        "description": (
            "Count rows matching a condition. op is one of =, !=, <, >, <=, >=, "
            "blank, not_blank, in, not_in. For in/not_in, value is a "
            "comma-separated list. blank/not_blank ignore value."
        ),
        "properties": {
            "table": "Table name.",
            "column": "Column name.",
            "op": "Comparison operator.",
            "value": "Value to compare against, as a string.",
        },
        "required": ["table", "column", "op"],
    },
    {
        "name": "check_orphans",
        "description": (
            "Count distinct values of a left column that have no match in a "
            "right column. left_strip and right_strip remove a leading prefix "
            "from each side before comparing, for keys that are written "
            "differently on either side of a join."
        ),
        "properties": {
            "left_table": "Table holding the referencing column.",
            "left_column": "The referencing column.",
            "right_table": "Table holding the referenced column.",
            "right_column": "The referenced column.",
            "left_strip": "Prefix to remove from left values before comparing.",
            "right_strip": "Prefix to remove from right values before comparing.",
        },
        "required": ["left_table", "left_column", "right_table", "right_column"],
    },
    {
        "name": "list_documents",
        "description": "List the customer documents supplied alongside the dataset.",
        "properties": {},
        "required": [],
    },
    {
        "name": "read_document",
        "description": "Read one of the customer documents in full.",
        "properties": {"name": "Document name from list_documents."},
        "required": ["name"],
    },
    {
        "name": "record_finding",
        "description": (
            "Record a defect you have established. You must supply the query "
            "that demonstrates it and the result you expect that query to "
            "return; the query is re-run and a disagreement records nothing and "
            "hands back the real figure."
        ),
        "properties": {
            "title": "One sentence describing the defect.",
            "evidence_tool": "count_rows, check_orphans or distinct_values.",
            "evidence_args": "The arguments to that tool, as a JSON object.",
            "expected": "The number you expect it to return, as a string.",
        },
        "required": ["title", "evidence_tool", "evidence_args", "expected"],
    },
    {
        "name": "finish",
        "description": (
            "End the investigation. Call this when you have recorded what you "
            "found, or when you are confident there is nothing further to find."
        ),
        "properties": {"summary": "What you established, in one or two sentences."},
        "required": ["summary"],
    },
]

TOOL_NAMES = [t["name"] for t in TOOL_SPECS]


def openai_tools() -> list[dict]:
    """TOOL_SPECS in the shape the `tools` request parameter wants."""
    out = []
    for t in TOOL_SPECS:
        out.append(
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": {
                        "type": "object",
                        "properties": {
                            k: {"type": "string", "description": v}
                            for k, v in t["properties"].items()
                        },
                        "required": t["required"],
                    },
                },
            }
        )
    return out


def text_tool_manual() -> str:
    """TOOL_SPECS as prose, for the text protocol."""
    lines = []
    for t in TOOL_SPECS:
        args = ", ".join(
            f"{k}{'' if k in t['required'] else '?'}" for k in t["properties"]
        )
        lines.append(f"- `{t['name']}({args})` -- {t['description']}")
        for k, v in t["properties"].items():
            lines.append(f"    - `{k}`: {v}")
    return "\n".join(lines)


TEXT_PROTOCOL = """
You act by calling exactly one tool per reply. A reply is a single fenced JSON
block and nothing else:

```json
{"tool": "describe_table", "args": {"table": "readings"}}
```

Do not write more than one block. Do not write the result yourself -- you will
be given it, and then you reply with the next call.

Tools:

%s
""".strip()


@dataclass
class ParsedCall:
    tool: str
    args: dict
    call_id: str = ""
    malformed: bool = False  # parsed, but not in the form that was asked for
    reason: str = ""


@dataclass
class ParseOutcome:
    calls: list[ParsedCall] = field(default_factory=list)
    text: str = ""


_FENCE_RE = re.compile(r"```(?:json|js|javascript|tool_code|python)?\s*\n(.*?)(?:```|\Z)", re.S)
_OBJ_RE = re.compile(r"\{.*\}", re.S)


def _coerce_args(raw) -> tuple[dict, bool]:
    """Accept an object, or a JSON string holding one. Report which it was."""
    if isinstance(raw, dict):
        return {str(k): raw[k] for k in raw}, False
    if isinstance(raw, str):
        try:
            v = json.loads(raw)
        except json.JSONDecodeError:
            return {}, True
        if isinstance(v, dict):
            return {str(k): v[k] for k in v}, True
    return {}, True


def parse_native(message: dict) -> ParseOutcome:
    """Read `message.tool_calls`, falling back to a call written in the content.

    Small models routinely emit a perfectly sensible call as *text* even when
    they were offered the `tools` parameter, because the chat template did not
    fire or they never learned to use the channel. A strict reader sees an
    empty `tool_calls` and calls it prose, which scores "wrote the right call
    in the wrong place" identically to "had no idea" -- two different problems
    with two different fixes.

    So it is salvaged, executed, and counted as malformed. The score still
    reflects it: a loop full of out-of-band calls fails `operates_tools`,
    because a real agent client reads the field and would have seen nothing.
    """
    out = ParseOutcome(text=(message.get("content") or ""))
    if not (message.get("tool_calls") or []):
        salvaged = parse_text(message.get("content") or "")
        for c in salvaged.calls:
            c.malformed = True
            c.reason = "written in the reply text, not as a tool call"
        salvaged.text = out.text
        return salvaged
    for tc in message.get("tool_calls") or []:
        fn = tc.get("function") or {}
        args, salvaged = _coerce_args(fn.get("arguments"))
        out.calls.append(
            ParsedCall(
                tool=str(fn.get("name") or ""),
                args=args,
                call_id=str(tc.get("id") or f"call_{len(out.calls)}"),
                malformed=salvaged and not isinstance(fn.get("arguments"), str),
                reason="arguments were not a JSON object" if salvaged and not fn.get("arguments") else "",
            )
        )
    return out


def parse_text(content: str) -> ParseOutcome:
    """Pull one call out of free text, recording how much salvaging it took."""
    out = ParseOutcome(text=content or "")
    text = strip_reasoning(content or "")

    blobs = [m.group(1) for m in _FENCE_RE.finditer(text)]
    malformed = False
    if not blobs:
        m = _OBJ_RE.search(text)
        if not m:
            return out
        blobs = [m.group(0)]
        malformed = True  # a bare object where a fenced block was asked for

    # Last block wins: models revise, and the revision is the answer.
    for blob in reversed(blobs):
        obj = _first_object(blob)
        if obj is None:
            continue
        tool = obj.get("tool") or obj.get("name") or obj.get("function")
        if isinstance(tool, dict):  # {"function": {"name": ..., "arguments": ...}}
            obj = tool
            tool = obj.get("name")
            malformed = True
        if not tool:
            continue
        raw = obj.get("args", obj.get("arguments", obj.get("parameters")))
        if raw is None:
            # Arguments written beside the tool name rather than nested under
            # it: {"tool": "finish", "summary": "..."}. Observed in the wild,
            # and dropping them would score a well-aimed call as an empty one.
            raw = {k: v for k, v in obj.items() if k not in ("tool", "name", "function")}
            malformed = True
        args, salvaged = _coerce_args(raw)
        out.calls.append(
            ParsedCall(
                tool=str(tool),
                args=args,
                call_id="call_0",
                malformed=malformed or salvaged or len(blobs) > 1,
                reason="more than one block" if len(blobs) > 1 else "",
            )
        )
        return out
    return out


def _first_object(blob: str):
    blob = blob.strip()
    try:
        v = json.loads(blob)
    except json.JSONDecodeError:
        m = _OBJ_RE.search(blob)
        if not m:
            return None
        try:
            v = json.loads(m.group(0))
        except json.JSONDecodeError:
            return None
    if isinstance(v, list):
        v = v[0] if v and isinstance(v[0], dict) else None
    return v if isinstance(v, dict) else None

