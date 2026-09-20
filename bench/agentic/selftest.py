"""The guard rail. Three things, all of which must stay true.

**Every task is solvable and is not already solved.** Its `reference/` overlay
must make the hidden suite pass, and the project as shipped must fail it. A
task whose own reference fix fails measures nothing; a task that passes as
shipped measures nothing either, and both are easy to introduce by accident.

**The workspace cannot be talked out of its boundaries.** The tests must not be
readable, reachable by a relative path, or visible in a listing, and failure
output must not carry their source back to the model.

**The scorer scores the right thing.** Scripted agents are played against it:
one that fixes the code must pass, and -- the case worth protecting -- one that
announces success without fixing anything must not.
"""

from __future__ import annotations

import os
import shutil

from ..client import Completion
from .loop import run_task
from .tasks import load_tasks
from .tools import ToolError, Workspace


class ScriptedClient:
    """Replays a fixed list of assistant messages, ignoring the conversation."""

    def __init__(self, script):
        self.script = list(script)
        self.calls = 0

    def complete(self, messages, **kw):
        self.calls += 1
        if not self.script:
            return Completion(text="", wall_s=0.0, message={"role": "assistant", "content": "done"})
        msg = self.script.pop(0)
        return Completion(
            text=msg.get("content") or "",
            wall_s=0.0,
            completion_tokens=1,
            message=msg,
        )


def _tool(name, args, call_id="c0"):
    import json as _json

    return {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {"id": call_id, "type": "function",
             "function": {"name": name, "arguments": _json.dumps(args)}}
        ],
    }


def _reference_files(task):
    """The reference overlay as {relative path: contents}."""
    out = {}
    for dirpath, _, filenames in os.walk(task.reference_dir):
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, task.reference_dir)
            with open(full) as f:
                out[rel] = f.read()
    return out


def run() -> list[str]:
    fails: list[str] = []
    tasks = load_tasks()
    if not tasks:
        return ["no tasks found"]

    for task in tasks:
        # -- shipped must fail, reference must pass ---------------------
        ws = Workspace(task.project_dir, task.tests_dir, timeout=task.test_timeout)
        try:
            before = ws.run_tests()
            if before.crashed:
                fails.append(f"{task.id}: test runner crashed before reporting: {before.report[:200]}")
            elif before.ok:
                fails.append(f"{task.id}: passes as shipped, so it measures nothing")
            elif before.total == 0:
                fails.append(f"{task.id}: test runner reported no tests")
        finally:
            ws.close()

        ws = Workspace(task.project_dir, task.tests_dir, timeout=task.test_timeout)
        try:
            shutil.copytree(task.reference_dir, ws.root, dirs_exist_ok=True)
            after = ws.run_tests()
            if not after.ok:
                fails.append(
                    f"{task.id}: reference fix does not pass its own tests "
                    f"({after.failed}/{after.total} failing)"
                )
        finally:
            ws.close()

        # -- the tests stay hidden --------------------------------------
        ws = Workspace(task.project_dir, task.tests_dir, timeout=task.test_timeout)
        try:
            listing = ws.list_files()
            if "run_tests" in listing or "test" in listing.lower().replace("latest", ""):
                fails.append(f"{task.id}: a test file is visible in list_files")
            for probe in ("run_tests.py", "../tests/run_tests.py", "/etc/passwd",
                          "../../etc/passwd", "tests/run_tests.py"):
                try:
                    ws.read_file(probe)
                except ToolError:
                    pass
                else:
                    fails.append(f"{task.id}: read_file reached {probe}")
            # A failure report must not carry the tests' own source back.
            rep = ws.run_tests().report
            if "assert" in rep or 'File "' in rep:
                fails.append(f"{task.id}: test output leaks source: {rep[:120]}")
        finally:
            ws.close()

        if task.spec_file:
            p = os.path.join(task.project_dir, task.spec_file)
            if not os.path.isfile(p):
                fails.append(f"{task.id}: spec_file {task.spec_file} is not in the project")

    # -- workspace mechanics -------------------------------------------
    task = tasks[0]
    ws = Workspace(task.project_dir, task.tests_dir, timeout=task.test_timeout)
    try:
        target = ws.files()[0]
        body = ws.read_file(target)
        try:
            ws.replace_in_file(target, "this text is definitely not present", "x")
        except ToolError:
            pass
        else:
            fails.append("replace_in_file accepted a snippet that does not occur")
        dup = "\n".join(["dup line"] * 3)
        ws.write_file("dup.txt", dup)
        try:
            ws.replace_in_file("dup.txt", "dup line", "x")
        except ToolError:
            pass
        else:
            fails.append("replace_in_file accepted an ambiguous snippet")
        ws.write_file("dup.txt", "one\ntwo\n")
        ws.replace_in_file("dup.txt", "one", "three")
        if ws.read_file("dup.txt") != "three\ntwo\n":
            fails.append("replace_in_file did not apply the replacement")
        if ws.read_file(target) != body:
            fails.append("a refused edit changed the file anyway")
    except Exception as e:  # noqa: BLE001 -- a broken guard rail must be loud
        fails.append(f"workspace mechanics raised {type(e).__name__}: {e}")
    finally:
        ws.close()

    # -- scripted agents ------------------------------------------------
    task = tasks[0]
    ref = _reference_files(task)

    fixer = [_tool("list_files", {})]
    fixer.append(_tool("read_file", {"path": list(ref)[0]}))
    for rel, content in ref.items():
        fixer.append(_tool("write_file", {"path": rel, "content": content}))
    fixer.append(_tool("run_tests", {}))
    fixer.append(_tool("finish", {"summary": "fixed"}))

    res, _ = run_task(ScriptedClient(fixer), task)
    if not res.passed:
        fails.append(
            f"scorer: an agent that applied the reference fix scored as failing "
            f"({res.tests_failed_at_end}/{res.tests_total} failing)"
        )
    if not res.operates_tools:
        fails.append("scorer: an agent using the tools properly failed the operates floor")
    if res.finished_unverified:
        fails.append("scorer: a genuine fix was marked as declaring done while failing")

    # The case worth protecting: confident, well-formed, and wrong.
    liar = [
        _tool("list_files", {}),
        _tool("read_file", {"path": list(ref)[0]}),
        _tool("run_tests", {}),
        _tool("finish", {"summary": "All tests pass. The ledger is correct."}),
    ]
    res, _ = run_task(ScriptedClient(liar), task)
    if res.passed:
        fails.append("scorer: an agent that changed nothing was scored as passing")
    if not res.finished_unverified:
        fails.append("scorer: declaring done with tests failing was not recorded")

    # Green, then broken again: the final state is what counts.
    breaker = [_tool("list_files", {})]
    breaker.append(_tool("read_file", {"path": list(ref)[0]}))
    for rel, content in ref.items():
        breaker.append(_tool("write_file", {"path": rel, "content": content}))
    breaker.append(_tool("run_tests", {}))
    breaker.append(_tool("write_file", {"path": list(ref)[0], "content": "raise RuntimeError('broken')\n"}))
    breaker.append(_tool("finish", {"summary": "done"}))
    res, _ = run_task(ScriptedClient(breaker), task)
    if res.passed:
        fails.append("scorer: a run that ended broken was scored on an earlier green run")
    if not res.regressed:
        fails.append("scorer: having it green and then breaking it was not recorded")

    # Calls written as prose are salvaged, executed, and counted as malformed.
    prose = [
        {"role": "assistant", "content": '```json\n{"tool": "list_files", "args": {}}\n```'},
        {"role": "assistant", "content": '```json\n{"tool": "read_file", "args": {"path": "README.md"}}\n```'},
        {"role": "assistant", "content": '```json\n{"tool": "run_tests", "args": {}}\n```'},
        {"role": "assistant", "content": '```json\n{"tool": "finish", "args": {"summary": "x"}}\n```'},
    ]
    res, _ = run_task(ScriptedClient(prose), task)
    if res.calls_malformed != res.calls_total or res.calls_total == 0:
        fails.append("scorer: calls written in the reply text were not all counted as malformed")
    if res.operates_tools:
        fails.append("scorer: an agent whose every call was out of band passed the operates floor")

    # A reasoning model that answers only in the analysis channel is heard.
    analysis = [
        {"role": "assistant", "content": "",
         "reasoning_content": '```json\n{"tool": "list_files", "args": {}}\n```'},
        {"role": "assistant", "content": "",
         "reasoning_content": '```json\n{"tool": "finish", "args": {"summary": "x"}}\n```'},
    ]
    res, _ = run_task(ScriptedClient(analysis), task)
    if res.calls_total < 2:
        fails.append(
            "scorer: a reply carried only in reasoning_content was discarded "
            "(this is the bug that scored gpt-oss at zero)"
        )

    return fails
