"""Bearings MCP server (stdio). Two tools:

* ``get_context_pack(task)``: the files to start in, the test command, and the
  graph path behind each suggestion.
* ``report_task(task, changed_files, ...)``: record a finished task and its
  outcome so the next agent on the team starts from it.

Scope: tenant = $BEARINGS_TEAM (default "default-team"), subtenant =
$BEARINGS_REPO (default: the basename of the working directory).

Run: ``uv run --directory /path/to/bearings bearings-mcp``
"""

from __future__ import annotations

import hashlib
import logging
import json
import os
import sys
import time
from pathlib import Path

from mcp.server.mcpserver import MCPServer

from .core import Bearings, Params
from .db import Hydra

logging.getLogger("httpx").setLevel(logging.WARNING)
TEAM = os.environ.get("BEARINGS_TEAM", "default-team")
REPO = os.environ.get("BEARINGS_REPO", Path.cwd().name)
LOG = os.environ.get("BEARINGS_LOG")  # optional JSONL log of every call
READONLY = os.environ.get("BEARINGS_READONLY") == "1"  # benchmarks: never write

mcp = MCPServer(
    "bearings",
    instructions=(
        "Bearings remembers where past work in this repository landed. Call get_context_pack "
        "with the task description before exploring the code: it returns the files to start in, "
        "the test command, and why each was suggested. When you finish, call report_task with "
        "the files you changed, the files you read, and whether the tests passed."
    ),
)
_engine: Bearings | None = None
_last_pack: dict[str, object] = {}


def engine() -> Bearings:
    global _engine
    if _engine is None:
        _engine = Bearings(Hydra(tenant=TEAM, subtenant=REPO), Params())
        t = time.time()
        _engine.load(full=False)
        print(f"bearings: loaded {TEAM}/{REPO}: {_engine.n_events} tasks, {len(_engine.files)} files "
              f"in {time.time() - t:.1f}s", file=sys.stderr)
    return _engine


def _log(kind: str, payload: dict) -> None:
    if LOG:
        with open(LOG, "a") as f:
            f.write(json.dumps({"t": time.time(), "kind": kind, **payload}) + "\n")


@mcp.tool()
def get_context_pack(task: str, max_files: int = 5) -> str:
    """Get a context pack for a coding task in this repository: the few files most likely
    to need changes (learned from earlier tasks by the team), the test command, and the
    path through the graph that justifies each file. Call this first, before searching."""
    t0 = time.time()
    try:
        eng = engine()
        pack = eng.context_pack(task, k=max(1, min(max_files, 10)))
    except Exception as exc:  # never break the agent's run
        _log("error", {"task": task[:200], "error": str(exc)[:300], "ms": round((time.time() - t0) * 1000)})
        return "Bearings is unavailable right now; explore as usual."
    _last_pack[hashlib.sha1(task.encode()).hexdigest()] = pack
    text = pack.render() if pack.files else "Bearings has no learned context for this task yet; explore as usual."
    _log("pack", {"task": task[:200], "files": [f["path"] for f in pack.files], "test": pack.test_command,
                  "chars": len(text), "ms": round((time.time() - t0) * 1000)})
    return text


@mcp.tool()
def report_task(
    task: str,
    changed_files: list[str],
    read_files: list[str] | None = None,
    test_command: str | None = None,
    passed: bool = True,
    task_id: str | None = None,
) -> str:
    """Record a finished task: the files changed, the files read, the test command that
    verified it, and whether it passed. Links that led to the right files get cheaper;
    links that led nowhere get dearer."""
    if READONLY:
        _log("report-ignored", {"task": task[:200], "changed": changed_files})
        return "Bearings is read-only in this session; nothing was recorded."
    eng = engine()
    tid = task_id or "agent:" + hashlib.sha1(f"{task}{time.time()}".encode()).hexdigest()[:12]
    pack = _last_pack.pop(hashlib.sha1(task.encode()).hexdigest(), None)
    if pack is not None and passed:
        eng.feedback(pack, changed_files)
    res = eng.ingest(tid, task, changed_files, read=read_files or [], test_cmd=test_command,
                     passed=passed, date=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), source="agent")
    _log("report", {"task": task[:200], "changed": changed_files, "read": read_files, "passed": passed})
    return f"Recorded {res['task']}: {res['entities']} entities, {res['files']} files, tests {res['tests'] or '-'}."


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
