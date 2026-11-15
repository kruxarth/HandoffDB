"""Claude Code demo: one real task, fixed twice through headless Claude Code,
once without Bearings and once with it. Prints token usage side by side.

This is a single example, not a statistic. The benchmark numbers come from
Level 1 and Level 2 (DeepSeek through OpenCode) and are reported separately.

  uv run python bench/claude_demo.py --task django__django-15851 [--model sonnet] [--side both|without|with]

Each side gets its own history-free snapshot of the repo at the task's base
commit. The Bearings side connects the Bearings MCP server (scope
bench/django-l2: Django history + SWE-bench tasks before 2022-07-01).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "claude_demo"
WORK = ROOT / "runs" / "tmp"

PROMPT = """Fix this issue in the Django repository in the current directory. Make the smallest correct change to the source code. You may run the relevant tests with `python tests/runtests.py <module>` (dependencies are installed). Do not add new tests. When you are done, reply with one line: CHANGED: <comma-separated files you edited>.
{extra}
ISSUE:
{issue}"""

EXTRA_WITH = ("\nA Bearings MCP server is connected. Before exploring, call its get_context_pack tool with the issue "
              "text; it returns where past work on this repo landed. When you are done, call report_task with the "
              "files you changed and read and whether the tests passed.\n")


def task_by_id(tid: str) -> dict:
    for line in open(ROOT / "data/derived/tasks.jsonl"):
        t = json.loads(line)
        if t["id"] == tid:
            return t
    raise SystemExit(f"unknown task {tid}")


def mcp_config(with_bearings: bool) -> Path:
    cfg = {"mcpServers": {}}
    if with_bearings:
        cfg["mcpServers"]["bearings"] = {
            "command": "uv",
            "args": ["run", "--quiet", "--directory", str(ROOT), "bearings-mcp"],
            "env": {"BEARINGS_TEAM": "bench", "BEARINGS_REPO": "django-l2",
                    "BEARINGS_LOG": str(OUT / "mcp_calls.jsonl")},
        }
    p = OUT / ("mcp_with.json" if with_bearings else "mcp_without.json")
    p.write_text(json.dumps(cfg, indent=2))
    return p


def run_side(task: dict, side: str, model: str) -> dict:
    wt = WORK / f"demo-{side}-{task['id']}"
    subprocess.run([str(ROOT / "scripts/snapshot.sh"), str(ROOT / "data/repos/django"), task["base_commit"], str(wt)],
                   check=True)
    with_b = side == "with"
    prompt = PROMPT.format(extra=EXTRA_WITH if with_b else "", issue=task["text"])
    tools = "Read Edit Write Glob Grep Bash(python:*) Bash(python3:*) Bash(git diff:*) Bash(git status:*) Bash(ls:*)"
    if with_b:
        tools += " mcp__bearings__get_context_pack mcp__bearings__report_task"
    cmd = ["claude", "-p", prompt, "--model", model, "--output-format", "stream-json", "--verbose",
           "--strict-mcp-config", "--mcp-config", str(mcp_config(with_b)),
           "--allowedTools", *tools.split(" "), "--max-turns", "60"]
    venv = ROOT / "runs" / "demo-venv" / "bin"
    env = dict(__import__("os").environ, PATH=f"{venv}:{__import__('os').environ['PATH']}")
    t0 = time.time()
    log = OUT / f"{task['id']}.{side}.stream.jsonl"
    with open(log, "w") as f:
        subprocess.run(cmd, cwd=wt, stdout=f, stderr=subprocess.STDOUT, env=env, timeout=1800)
    wall = time.time() - t0
    result, tools_used = {}, []
    for line in open(log):
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if e.get("type") == "result":
            result = e
        if e.get("type") == "assistant":
            for c in e.get("message", {}).get("content", []):
                if c.get("type") == "tool_use":
                    tools_used.append(c.get("name"))
    diff = subprocess.run(["git", "diff", "--name-only"], cwd=wt, capture_output=True, text=True).stdout.split()
    u = result.get("usage", {})
    row = {
        "task": task["id"], "side": side, "model": model,
        "claude_code_version": subprocess.run(["claude", "--version"], capture_output=True, text=True).stdout.strip(),
        "input_tokens": u.get("input_tokens", 0),
        "cache_creation_input_tokens": u.get("cache_creation_input_tokens", 0),
        "cache_read_input_tokens": u.get("cache_read_input_tokens", 0),
        "output_tokens": u.get("output_tokens", 0),
        "num_turns": result.get("num_turns"), "tool_calls": len(tools_used), "tools": tools_used,
        "list_price_usd": result.get("total_cost_usd"), "wall_s": round(wall, 1),
        "changed_files": diff, "gold_files": task["files"],
        "correct_files": sorted(set(diff) & set(task["files"])) == sorted(task["files"]),
        "result_text": (result.get("result") or "")[-500:],
    }
    row["total_input"] = row["input_tokens"] + row["cache_creation_input_tokens"] + row["cache_read_input_tokens"]
    (OUT / f"{task['id']}.{side}.json").write_text(json.dumps(row, indent=2))
    subprocess.run(["git", "diff"], cwd=wt, stdout=open(OUT / f"{task['id']}.{side}.diff", "w"))
    return row


def show(rows: list[dict]) -> None:
    keys = ["total_input", "input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens",
            "num_turns", "tool_calls", "wall_s", "list_price_usd", "correct_files"]
    print(f"{'Claude Code':32s}" + "".join(f"{r['side'] + ' Bearings':>18s}" for r in rows))
    for k in keys:
        print(f"{k:32s}" + "".join(f"{str(r.get(k)):>18s}" for r in rows))
    print("changed files:", {r["side"]: r["changed_files"] for r in rows}, " gold:", rows[0]["gold_files"])
    print("(list_price_usd is Claude Code's own list-price arithmetic, not measured spend; this run used a Pro plan.)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True)
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--side", default="both", choices=["both", "without", "with"])
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    task = task_by_id(args.task)
    sides = ["without", "with"] if args.side == "both" else [args.side]
    rows = []
    for s in sides:
        rows.append(run_side(task, s, args.model))
    for s in ("without", "with"):
        p = OUT / f"{task['id']}.{s}.json"
        if p.exists() and s not in sides:
            rows.append(json.loads(p.read_text()))
    rows.sort(key=lambda r: r["side"] != "without")
    show(rows)


if __name__ == "__main__":
    main()
