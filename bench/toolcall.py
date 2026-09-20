"""Ask a model for a tool call, and read the answer. Tool-set agnostic.

Two protocols. `native` uses the OpenAI `tools` parameter and reads
`message.tool_calls`; that is how a real agent drives a model, so it is the
default and the one whose results transfer. `text` describes the tools in the
system prompt and asks for a fenced JSON object, for servers that reject the
`tools` parameter outright -- not for models that are merely bad at using it,
which is a thing this suite measures rather than routes around.

Parsing is deliberately forgiving and separately *counted*. A call that had to
be salvaged still executes, so a model is not scored down twice for one
mistake, but `malformed` records that the salvage happened, because in a real
loop the strict parser on the other end would have rejected it.

Everything here is driven by a list of tool specs:

    {"name": ..., "description": ..., "properties": {arg: doc}, "required": [...]}

so a suite defines its tools and reuses all of this.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from .extract import strip_reasoning


def openai_tools(specs: list[dict]) -> list[dict]:
    """Specs in the shape the `tools` request parameter wants."""
    return [
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
        for t in specs
    ]


def text_tool_manual(specs: list[dict]) -> str:
    """Specs as prose, for the text protocol."""
    lines = []
    for t in specs:
        args = ", ".join(
            f"{k}{'' if k in t['required'] else '?'}" for k in t["properties"]
        )
        lines.append(f"- `{t['name']}({args})` -- {t['description']}")
        for k, v in t["properties"].items():
            lines.append(f"    - `{k}`: {v}")
    return "\n".join(lines)


_TEXT_PROTOCOL = """
You act by calling exactly one tool per reply. A reply is a single fenced JSON
block and nothing else:

```json
%s
```

Do not write more than one block. Do not write the result yourself -- you will
be given it, and then you reply with the next call.

Tools:

%s
""".strip()


def text_protocol(specs: list[dict], example: dict) -> str:
    return _TEXT_PROTOCOL % (json.dumps(example), text_tool_manual(specs))


def message_text(message: dict) -> str:
    """The model's words, wherever the server put them.

    A reasoning model may answer entirely in its analysis channel, which
    llama-server returns as `reasoning_content` beside an empty `content`.
    Reading only `content` there does not measure a quiet model -- it discards
    a talkative one, and scores the harness instead of the model.
    """
    content = (message or {}).get("content") or ""
    if content.strip():
        return content
    return (message or {}).get("reasoning_content") or ""


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

    Models routinely emit a perfectly sensible call as *text* even when offered
    the `tools` parameter, because the chat template did not fire or they never
    learned the channel. A strict reader sees an empty `tool_calls` and calls
    it prose, scoring "wrote the right call in the wrong place" identically to
    "had no idea" -- two different problems with two different fixes.

    So it is salvaged, executed, and counted as malformed. The score still
    reflects it: a loop full of out-of-band calls fails `operates_tools`,
    because a real agent client reads the field and would have seen nothing.
    """
    content = message_text(message)
    out = ParseOutcome(text=content)
    if not (message.get("tool_calls") or []):
        salvaged = parse_text(content)
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
