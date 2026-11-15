"""Dev-split tuning with the in-memory reference backend (no database).

Only tasks dated before level1.TEST_FROM are scored. Prints hit@1/hit@5 per setting.
  uv run python bench/tune_dev.py --seed history
"""
import argparse
import itertools
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "bench"))
from bearings.core import Bearings, Params  # noqa: E402
from level1 import TEST_FROM, load, metrics  # noqa: E402


def stream(seed):
    tasks = [t for t in load("tasks.jsonl") if t["date"] < TEST_FROM]
    evs = [dict(t, kind="task") for t in tasks]
    if seed == "history":
        evs += [dict(h, kind="history") for h in load("history.jsonl") if h["date"] < TEST_FROM]
    evs.sort(key=lambda e: (e["date"], e["kind"] != "history", e["id"]))
    return evs


def run(args):
    seed, kw = args
    p = Params(**kw)
    eng = Bearings(None, p)
    hits = {"1": [], "5": [], "1h1": [], "5h1": []}
    for ev in stream(seed):
        if ev["kind"] == "task":
            pk = eng.context_pack(ev["text"], k=5, hops=2)
            m = metrics([f["path"] for f in pk.files], ev["files"])
            hits["1"].append(m["hit@1"]); hits["5"].append(m["hit@5"])
            m1 = metrics([f["path"] for f in eng.context_pack(ev["text"], k=5, hops=1).files], ev["files"])
            hits["1h1"].append(m1["hit@1"]); hits["5h1"].append(m1["hit@5"])
            eng.feedback(pk, ev["files"])
        eng.ingest(ev["id"], ev["text"], ev["files"] + ev.get("test_files", []), flush=True)
    n = len(hits["1"])
    return kw, {k: round(sum(v) / n, 3) for k, v in hits.items()}, n


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", default="history")
    ap.add_argument("--grid", default='{"beta":[0,1],"hop_penalty":[0,1.5]}')
    a = ap.parse_args()
    grid = json.loads(a.grid)
    keys = list(grid)
    combos = [dict(zip(keys, vals)) for vals in itertools.product(*[grid[k] for k in keys])]
    with ProcessPoolExecutor(min(8, len(combos))) as ex:
        for kw, res, n in ex.map(run, [(a.seed, c) for c in combos]):
            print(json.dumps(kw), res, f"n={n}", flush=True)
