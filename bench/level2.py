"""Level 2: live localization runs through OpenCode (headless).

The agent gets the issue and a history-free checkout of the repo at the task's
base commit, explores, and names the files it would edit, then stops. Success
is checked in code against the files the real fix touched.

Conditions:
  none      no memory
  dict      the dictionary baseline's top-5 files, inlined in the prompt
  bearings  the Bearings MCP server connected to OpenCode; the agent is told to
            call get_context_pack first

Usage:
  uv run python bench/level2.py build-graph            # seed scope bench/django-l2 (events before CUTOFF)
  uv run python bench/level2.py run --tasks 30 --conditions none,dict,bearings
  uv run python bench/level2.py run --only django__django-11532 --conditions none   # trial
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bearings.baselines import DictBaseline  # noqa: E402
from bearings.core import Bearings, Params, is_source  # noqa: E402
from bearings.db import Hydra  # noqa: E402

MODEL = os.environ.get("L2_MODEL", "opencode/deepseek-v4.1-flash-free")
CUTOFF = "2022-07-01"  # graph/dictionary learn from events before this; sample from after
SCOPE = ("bench", "django-l2")
RUNS = ROOT / "runs" / "level2"
WORK = ROOT / "runs" / "tmp"
STEP_CAP = 25
import threading  # noqa: E402
_lock = threading.Lock()
_start_lock = threading.Lock()
TIMEOUT = 900

PROMPT = """You are localizing an issue in this repository (the Django source tree). Read the issue, explore the code as needed, and decide which source files must be edited to fix it. Do not edit any files and do not run the test suite. Finish with one final line in exactly this form:
FILES: path/one.py, path/two.py
(repo-relative paths of the source files to edit, most likely first, at most 5).
{extra}
ISSUE:
{issue}"""

EXTRA = {
    "none": "",
    "dict": "\nFiles that past fixes with similar wording changed (from a word-to-file table built from this repo's history; may be wrong):\n{pack}\n",
    "bearings": "\nA Bearings MCP tool is available. Call bearings_get_context_pack with the issue text before you start exploring; it returns where past work on this repo landed.\n",
}

OC_ENV = {
    "OPENCODE_DISABLE_CLAUDE_CODE": "1",
    "OPENCODE_DISABLE_CLAUDE_CODE_SKILLS": "1",
    "OPENCODE_DISABLE_CLAUDE_CODE_PROMPT": "1",
}


def load(name: str) -> list[dict]:
    return [json.loads(line) for line in open(ROOT / "data/derived" / name)]


def events_before(cutoff: str) -> list[dict]:
    evs = [dict(h, kind="history") for h in load("history.jsonl") if h["date"] < cutoff]
    evs += [dict(t, kind="task", files=t["files"] + t["test_files"]) for t in load("tasks.jsonl") if t["date"] < cutoff]
    evs.sort(key=lambda e: (e["date"], e["id"]))
    return evs


def build_graph() -> None:
    sys.path.insert(0, str(ROOT / "bench"))
    from level1 import reset_scope

    db = Hydra(tenant=SCOPE[0], subtenant=SCOPE[1])
    reset_scope(db)
    eng = Bearings(db, Params())
    t0 = time.time()
    evs = events_before(CUTOFF)
    for i, e in enumerate(evs):
        eng.ingest(e["id"], e["text"], e["files"], date=e["date"], source=e["kind"], flush=False)
        if (i + 1) % 3000 == 0:
            eng.flush()
            print(f"{i + 1}/{len(evs)} ({time.time() - t0:.0f}s)", flush=True)
    eng.flush()
    print(f"built {SCOPE[0]}/{SCOPE[1]} from {len(evs)} events before {CUTOFF} in {time.time() - t0:.0f}s")


def sample(n: int, seed: int = 0) -> list[dict]:
    pool = [t for t in load("tasks.jsonl") if t["verified"] and t["date"] >= CUTOFF]
    rnd = random.Random(seed)
    rnd.shuffle(pool)
    return sorted(pool[:n], key=lambda t: t["date"])


def oc_config(cond: str) -> Path:
    cfg = {
        "$schema": "https://opencode.ai/config.json",
        "agent": {"locate": {"description": "Find the files to edit for an issue; never edits.",
                             "mode": "primary", "steps": STEP_CAP,
                             "permission": {"edit": "deny", "bash": "allow", "webfetch": "deny"}}},
    }
    if cond == "bearings":
        cfg["mcp"] = {"bearings": {
            "type": "local",
            "command": ["uv", "run", "--quiet", "--directory", str(ROOT), "bearings-mcp"],
            "environment": {"BEARINGS_TEAM": SCOPE[0], "BEARINGS_REPO": SCOPE[1],
                            "BEARINGS_LOG": str(RUNS / "mcp_calls.jsonl"), "BEARINGS_READONLY": "1"},
            "enabled": True,
        }}
    p = ROOT / "bench" / "opencode" / f"{cond}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(cfg, indent=2))
    return p


def parse_events(path: Path) -> dict:
    tok = {"input": 0, "output": 0, "reasoning": 0, "cache_read": 0, "cache_write": 0}
    tools, steps, text = [], 0, []
    errors = []
    for line in path.read_text().splitlines():
        try:
            e = json.loads(line)
        except ValueError:
            continue
        p = e.get("part", {})
        if e["type"] == "step_finish":
            steps += 1
            t = p.get("tokens", {})
            tok["input"] += t.get("input", 0)
            tok["output"] += t.get("output", 0)
            tok["reasoning"] += t.get("reasoning", 0)
            tok["cache_read"] += t.get("cache", {}).get("read", 0)
            tok["cache_write"] += t.get("cache", {}).get("write", 0)
        elif e["type"] == "tool_use":
            tools.append(p.get("tool"))
        elif e["type"] == "text":
            text.append(p.get("text", ""))
        elif e["type"] == "error":
            errors.append(json.dumps(e.get("error") or e)[:300])
    final = "\n".join(text)
    m = re.findall(r"FILES:\s*(.+)", final)
    files = []
    if m:
        files = [f.strip().strip("`").lstrip("./") for f in re.split(r"[,\s]+", m[-1]) if f.strip()]
        files = [f for f in files if "/" in f or f.endswith(".py")]
    return {"tokens": tok, "total_input": tok["input"] + tok["cache_read"] + tok["cache_write"],
            "tools": tools, "tool_calls": len(tools), "steps": steps, "files": files[:5],
            "errors": errors, "answered": bool(m)}


def score(pred: list[str], gold: list[str]) -> dict:
    g = {f for f in gold if is_source(f)}
    p = set(pred)
    return {"hit": int(bool(p & g)), "all": int(g <= p), "recall": len(p & g) / len(g) if g else 0.0}


def run_one(task: dict, cond: str, dic: DictBaseline | None, rep: int = 0) -> dict:
    out_dir = RUNS / cond
    out_dir.mkdir(parents=True, exist_ok=True)
    ev_path = out_dir / f"{task['id']}.r{rep}.jsonl"
    wt = WORK / f"wt-{cond}-{task['id']}"
    subprocess.run([str(ROOT / "scripts/snapshot.sh"), str(ROOT / "data/repos/django"), task["base_commit"], str(wt)],
                   check=True)
    extra = EXTRA[cond]
    pack_text = ""
    if cond == "dict":
        pack_text = "\n".join(f"  {f}" for f in dic.rank(task["text"], k=5))
        extra = extra.format(pack=pack_text or "  (none)")
    prompt = PROMPT.format(extra=extra, issue=task["text"])
    env = dict(os.environ, **OC_ENV, OPENCODE_CONFIG=str(oc_config(cond)))
    attempts = 0
    while True:
        attempts += 1
        with _start_lock:  # stagger starts: concurrent opencode launches lock its sqlite db
            time.sleep(5)
        t0 = time.time()
        with open(ev_path, "w") as fo, open(ev_path.with_suffix(".err"), "w") as fe:
            try:
                proc = subprocess.run(["opencode", "run", "--title", "bench", "--format", "json", "--agent", "locate",
                                       "-m", MODEL, "--dir", str(wt), prompt],
                                      stdout=fo, stderr=fe, env=env, timeout=TIMEOUT)
                code = proc.returncode
            except subprocess.TimeoutExpired:
                code = "timeout"
        wall = time.time() - t0
        res = parse_events(ev_path)
        # infrastructure failure before the model ran (e.g. opencode's db locked): retry
        if code != 0 and res["steps"] == 0 and attempts < 3:
            continue
        break
    err_text = ev_path.with_suffix(".err").read_text()[-4000:]
    rate_limited = bool(re.search(r"rate.?limit|429|too many requests|quota", err_text + " ".join(res["errors"]), re.I))
    subprocess.run(["rm", "-rf", str(wt)])
    row = {"id": task["id"], "date": task["date"], "condition": cond, "rep": rep, "model": MODEL,
           "exit": code, "attempts": attempts, "wall_s": round(wall, 1), "rate_limited": rate_limited, "gold": task["files"],
           "dict_pack": pack_text, **res, **score(res["files"], task["files"])}
    with _lock, open(RUNS / "results.jsonl", "a") as f:
        f.write(json.dumps(row) + "\n")
    return row


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build-graph")
    r = sub.add_parser("run")
    r.add_argument("--tasks", type=int, default=30)
    r.add_argument("--only", default=None)
    r.add_argument("--conditions", default="none,dict,bearings")
    r.add_argument("--seed", type=int, default=0)
    r.add_argument("--skip-done", action="store_true")
    r.add_argument("--parallel", type=int, default=3)
    args = ap.parse_args()
    if args.cmd == "build-graph":
        build_graph()
        return
    RUNS.mkdir(parents=True, exist_ok=True)
    tasks = [t for t in load("tasks.jsonl") if t["id"] == args.only] if args.only else sample(args.tasks, args.seed)
    conds = args.conditions.split(",")
    dic = DictBaseline()
    if "dict" in conds:
        for e in events_before(CUTOFF):
            dic.ingest(e["text"], e["files"])
    done = set()
    if args.skip_done and (RUNS / "results.jsonl").exists():
        for line in open(RUNS / "results.jsonl"):
            r0 = json.loads(line)
            if not r0["rate_limited"] and r0["answered"]:
                done.add((r0["id"], r0["condition"]))
    jobs = [(t, c) for t in tasks for c in conds if (t["id"], c) not in done]
    # all conditions of one task run at the same time, so time-of-day and
    # rate-limit drift hit every condition equally

    def job(tc):
        t, c = tc
        row = run_one(t, c, dic)
        print(f"{t['id']} {c}: hit={row['hit']} all={row['all']} files={row['files']} "
              f"in={row['total_input']} out={row['tokens']['output']} tools={row['tool_calls']} "
              f"{row['wall_s']}s exit={row['exit']} rl={row['rate_limited']}", flush=True)

    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(args.parallel) as ex:
        list(ex.map(job, jobs))


if __name__ == "__main__":
    main()
