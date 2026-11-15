"""Summarise Level 1 result files: hit@k / recall@k per condition with 95% CIs.

  uv run python bench/summarize.py results/level1_tasks.jsonl [--split test] [--subset verified]
"""

from __future__ import annotations

import argparse
import json
import math
import random
from collections import defaultdict

CONDS = ["bm25", "dict", "anchors", "graph", "bearings-1", "bearings", "frozen"]


def ci(xs: list[float], reps: int = 2000, seed: int = 0) -> tuple[float, float, float]:
    """Mean and bootstrap 95% CI."""
    if not xs:
        return (float("nan"),) * 3
    rnd = random.Random(seed)
    n = len(xs)
    means = sorted(sum(xs[rnd.randrange(n)] for _ in range(n)) / n for _ in range(reps))
    return sum(xs) / n, means[int(0.025 * reps)], means[int(0.975 * reps)]


def paired_diff(a: list[float], b: list[float], reps: int = 2000, seed: int = 0) -> tuple[float, float, float]:
    d = [x - y for x, y in zip(a, b)]
    return ci(d, reps, seed)


def load(path: str, split: str | None, subset: str | None) -> list[dict]:
    rows = [json.loads(line) for line in open(path)]
    if split:
        rows = [r for r in rows if r["split"] == split]
    if subset:
        rows = [r for r in rows if r.get(subset)]
    return rows


def table(rows: list[dict], metrics=("hit@1", "hit@3", "hit@5", "recall@5")) -> dict:
    out = {}
    for c in CONDS:
        rs = [r for r in rows if c in r["metrics"]]
        if not rs:
            continue
        out[c] = {m: ci([r["metrics"][c][m] for r in rs]) for m in metrics}
        out[c]["n"] = len(rs)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--split", default="test")
    ap.add_argument("--subset", default=None)
    args = ap.parse_args()
    rows = load(args.path, args.split, args.subset)
    t = table(rows)
    print(f"{args.path}  split={args.split} subset={args.subset or 'all'}  n={len(rows)}")
    print(f"{'condition':12s} " + " ".join(f"{m:>20s}" for m in ("hit@1", "hit@3", "hit@5", "recall@5")))
    for c, v in t.items():
        print(f"{c:12s} " + " ".join(f"{v[m][0]:.3f} [{v[m][1]:.3f},{v[m][2]:.3f}]" for m in ("hit@1", "hit@3", "hit@5", "recall@5")))
    for a, b in [("bearings", "dict"), ("bearings", "bearings-1"), ("bearings-1", "dict"), ("bearings", "frozen"), ("bearings", "bm25")]:
        rs = [r for r in rows if a in r["metrics"] and b in r["metrics"]]
        for m in ("hit@1", "hit@5"):
            d = paired_diff([r["metrics"][a][m] for r in rs], [r["metrics"][b][m] for r in rs])
            print(f"  {a} - {b} {m}: {d[0]:+.3f} [{d[1]:+.3f},{d[2]:+.3f}] (n={len(rs)})")
    lat = defaultdict(list)
    for r in rows:
        lat["full"].append(r.get("latency_full_ms", 0))
        lat["one"].append(r.get("latency_one_ms", 0))
    for k, v in lat.items():
        v = sorted(v)
        print(f"latency {k}: p50 {v[len(v)//2]:.0f} ms, p95 {v[int(len(v)*0.95)]:.0f} ms")
    tc = [r["test_cmd_hit"] for r in rows]
    print(f"test command matches gold test module: {sum(tc)/max(1,len(tc)):.3f} (n={len(tc)})")
    pc = sorted(r["pack_chars"] for r in rows)
    print(f"pack size chars p50 {pc[len(pc)//2]}, approx tokens {pc[len(pc)//2]//4}")


if __name__ == "__main__":
    main()
