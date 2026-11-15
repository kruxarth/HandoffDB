"""Query latency on a quiet machine: one context pack at a time against the
Level 2 graph (Django history + SWE-bench tasks before 2022-07-01, ~19k events).

  uv run python bench/latency.py [--n 100]   -> results/latency.json

Times, per task: the HydraDB path query (MSpaths), the code anchors (git grep at
the task's commit), and the whole pack (both + scoring + line lookup).
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from bearings.anchors import definitions  # noqa: E402
from bearings.core import Bearings, Params  # noqa: E402
from bearings.db import Hydra  # noqa: E402

REPO = ROOT / "data/repos/django"


def pct(xs: list[float], q: float) -> float:
    xs = sorted(xs)
    return round(xs[min(len(xs) - 1, int(q * len(xs)))], 1)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100)
    a = ap.parse_args()
    eng = Bearings(Hydra(tenant="bench", subtenant="django-l2"), Params())
    eng.load(full=False)
    tasks = [json.loads(x) for x in open(ROOT / "data/derived/tasks.jsonl")]
    post = [t for t in tasks if t["date"] >= "2022-07-01"]
    tasks, other = post[: a.n], post[a.n: 2 * a.n]
    db_ms, code_ms, total_ms = [], [], []
    eng.context_pack(post[-1]["text"])  # warm up the connection
    # Each measurement runs on issues not queried before in this process, so no
    # answer can come from a cache: whole packs on one set, components on another.
    for t in tasks:
        q0 = time.time()
        eng.context_pack(t["text"], k=5, repo=REPO, commit=t["base_commit"])
        total_ms.append((time.time() - q0) * 1000)
    for t in other or tasks:
        terms = eng.select_terms(t["text"])
        q0 = time.time()
        if terms:
            eng._db_paths(terms, 2)
        db_ms.append((time.time() - q0) * 1000)
        q0 = time.time()
        definitions(REPO, t["base_commit"], t["text"])
        code_ms.append((time.time() - q0) * 1000)
    out = {"n": len(tasks), "n_components": len(other or tasks), "graph_events": eng.n_events,
           "hydradb_path_query_ms": {"p50": pct(db_ms, .5), "p95": pct(db_ms, .95), "mean": round(statistics.mean(db_ms), 1)},
           "code_anchors_ms": {"p50": pct(code_ms, .5), "p95": pct(code_ms, .95)},
           "context_pack_ms": {"p50": pct(total_ms, .5), "p95": pct(total_ms, .95)},
           "note": "sequential, one client, nothing else running on the machine"}
    (ROOT / "results" / "latency.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
