"""Where do Level 2 tokens go? Decomposes the existing runs (no model calls).

For each run, every step's input tokens (uncached + cache read: the context the
model re-read that step) are split evenly over the tool calls made in that step,
and each call is classified:
  search  grep / rg / find / ls / git grep / git log
  read    sed -n / cat / head / tail / nl / awk / read tool  (a file's contents)
  run     python / runtests (should be rare: the prompt forbids the test suite)
  other
The run is also split at the step where the agent first touches a real-fix file
(same rule as tokens_to_first_gold): "before" = finding, "after" = confirming.
Steps with no tool call (the final answer) count as "answer".

  uv run python bench/l2_decompose.py            # writes results/level2_decompose.txt
"""
from __future__ import annotations

import ast
import json
import re
import statistics as st
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "runs" / "level2"
CONDS = ["none", "dict", "bearings"]

SEARCH = re.compile(r"^\s*(grep|rg|find|ls|git\s+(grep|log|show|status|diff)|egrep|tree|wc)\b")
READ = re.compile(r"^\s*(sed|cat|head|tail|nl|awk|less|python3?\s+-c\s+.*open\()\b")
RUN = re.compile(r"^\s*(python3?|\./tests/runtests|pytest|django-admin)\b")
SED_RANGE = re.compile(r"sed\s+-n\s+['\"]?(\d+),(\d+)p")


def classify(tool: str, inp: dict) -> str:
    if tool in ("read",):
        return "read"
    if tool in ("grep", "glob", "list"):
        return "search"
    cmd = inp.get("command", "") if isinstance(inp, dict) else ""
    segs = [x for x in re.split(r"&&|\|\||;|\|", cmd) if x.strip() and not re.match(r"^\s*cd\b", x)]
    first = re.sub(r"git\s+-C\s+\S+", "git", segs[0]) if segs else ""
    if SEARCH.match(first):
        return "search"
    if READ.match(first):
        return "read"
    if RUN.match(first):
        return "run"
    return "other"


def read_spans(tool: str, inp: dict) -> list[int]:
    """Line counts of each file range read by this call (None-free; whole-file reads count as -1)."""
    out = []
    if tool == "read":
        lim = inp.get("limit")
        out.append(int(lim) if lim else -1)
        return out
    cmd = inp.get("command", "") if isinstance(inp, dict) else ""
    for a, b in SED_RANGE.findall(cmd):
        out.append(int(b) - int(a) + 1)
    for _ in re.findall(r"(?:^|&&|;|\|)\s*cat\s+[\w./-]+\.py", cmd):
        out.append(-1)
    return out


def decompose(path: Path, gold: list[str]) -> dict:
    steps, cur = [], {"calls": []}
    for line in path.read_text().splitlines():
        try:
            e = json.loads(line)
        except ValueError:
            continue
        p = e.get("part", {})
        if e["type"] == "tool_use":
            cur["calls"].append((p.get("tool"), p.get("state", {}).get("input", {}) or {}))
        elif e["type"] == "step_finish":
            t = p.get("tokens", {})
            cur["tok"] = t.get("input", 0) + t.get("cache", {}).get("read", 0)
            steps.append(cur)
            cur = {"calls": []}
    by = defaultdict(float)
    phase = {"before": 0, "after": 0}
    found = False
    spans = []
    after_files = set()
    target = defaultdict(float)   # after-phase tokens by what the tool call was aimed at
    for s in steps:
        hit_here = any(any(g in json.dumps(inp) for g in gold) for _, inp in s["calls"])
        ph = "after" if found else "before"
        phase[ph] += s["tok"]
        if hit_here:
            found = True
        if not s["calls"]:
            by["answer"] += s["tok"]
            continue
        for tool, inp in s["calls"]:
            by[classify(tool, inp)] += s["tok"] / len(s["calls"])
            spans += read_spans(tool, inp)
            if ph == "after":
                after_files |= set(re.findall(r"[\w/]+\.py", json.dumps(inp)))
                target[aim(inp, gold)] += s["tok"] / len(s["calls"])
        if ph == "after" and not s["calls"]:
            target["final answer"] += s["tok"]
    total = sum(s["tok"] for s in steps)
    return {"total": total, "steps": len(steps), "by": dict(by), "phase": phase, "found": found,
            "spans": spans, "after_files": len(after_files), "target": dict(target)}


def aim(inp: dict, gold: list[str]) -> str:
    """What a tool call was aimed at: the fix file again, tests/docs, another source file, or a repo-wide search."""
    s = json.dumps(inp)
    if any(g in s for g in gold):
        return "the fix file again"
    if re.search(r"(?<![\w])(tests|docs)/", s):
        return "tests and docs"
    if re.search(r"django/[\w/]+\.py", s):
        return "neighbouring source files"
    return "repo-wide search and other"


def main() -> None:
    rows = [json.loads(x) for x in open(RUNS / "results.jsonl")]
    rows = [r for r in rows if r["condition"] in CONDS]
    ids = sorted({r["id"] for r in rows if all((r["id"], c) in {(q["id"], q["condition"]) for q in rows} for c in CONDS)})
    out = []
    w = out.append
    w(f"Level 2 token decomposition: {len(ids)} issues x {len(CONDS)} conditions, existing runs, no model calls.")
    w("Tokens = input + cache read per step (the context re-read each step), split evenly over that step's tool calls.\n")
    agg = {}
    for c in CONDS:
        D = []
        for r in rows:
            if r["condition"] != c or r["id"] not in ids:
                continue
            gold = r["gold"] if isinstance(r["gold"], list) else ast.literal_eval(r["gold"])
            gold = [g for g in gold if not g.startswith("tests/") and "/tests/" not in g] or gold
            D.append(decompose(RUNS / c / f"{r['id']}.r{r.get('rep', 0)}.jsonl", gold))
        agg[c] = D
    w("Median tokens per run, by phase (before = until a real-fix file is first touched; after = the rest):")
    w(f"{'condition':10} {'total':>9} {'before':>8} {'after':>9} {'after share':>12} {'steps':>6} {'files touched after':>20}")
    for c, D in agg.items():
        tot = [d["total"] for d in D]
        w(f"{c:10} {st.median(tot):9,.0f} {st.median(d['phase']['before'] for d in D):8,.0f} "
          f"{st.median(d['phase']['after'] for d in D):9,.0f} "
          f"{sum(d['phase']['after'] for d in D) / sum(tot):11.0%} {st.median(d['steps'] for d in D):6.0f} "
          f"{st.median(d['after_files'] for d in D):20.0f}")
    w("\nShare of all tokens by kind of tool call (pooled over runs):")
    kinds = ["search", "read", "run", "other", "answer"]
    w(f"{'condition':10} " + " ".join(f"{k:>8}" for k in kinds))
    for c, D in agg.items():
        tot = sum(d["total"] for d in D)
        w(f"{c:10} " + " ".join(f"{sum(d['by'].get(k, 0) for d in D) / tot:8.0%}" for k in kinds))
    w("\nFile reads: how much of a file per read (sed -n ranges, read-tool limits, whole-file cat):")
    w(f"{'condition':10} {'reads':>6} {'whole file':>11} {'median lines':>13} {'>200 lines':>11}")
    for c, D in agg.items():
        sp = [x for d in D for x in d["spans"]]
        rng = [x for x in sp if x > 0]
        w(f"{c:10} {len(sp):6} {sum(x < 0 for x in sp) / max(len(sp), 1):11.0%} "
          f"{(st.median(rng) if rng else 0):13.0f} {sum(x > 200 for x in rng) / max(len(rng), 1):11.0%}")
    w("\nAfter-phase tokens by what the tool call was aimed at (pooled over runs, share of after-phase tokens):")
    aims = ["neighbouring source files", "tests and docs", "the fix file again", "repo-wide search and other", "final answer"]
    w(f"{'condition':10} " + " ".join(f"{k[:18]:>19}" for k in aims))
    for c, D in agg.items():
        tot = sum(d["phase"]["after"] for d in D)
        w(f"{c:10} " + " ".join(f"{sum(d['target'].get(k, 0) for d in D) / tot:19.0%}" for k in aims))
    (ROOT / "results" / "level2_decompose.txt").write_text("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
