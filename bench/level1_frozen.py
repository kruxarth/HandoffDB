"""Frozen-graph condition for Level 1, run as its own process.

Builds the graph once from every event before the first test task (exactly the
state the live graph has at that moment), never updates it, and answers every
test task from it. The frozen graph is static, so queries run concurrently.

  uv run python bench/level1_frozen.py --seed history --out results/level1_history_frozen.jsonl
"""
import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "bench"))
from bearings.core import Bearings, Params  # noqa: E402
from bearings.db import Hydra  # noqa: E402
from level1 import TEST_FROM, load, metrics, reset_scope  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", choices=["tasks", "history"], default="history")
    ap.add_argument("--out", required=True)
    ap.add_argument("--tenant", default="bench")
    args = ap.parse_args()
    tasks = load("tasks.jsonl")
    events = [dict(t, kind="task") for t in tasks]
    if args.seed == "history":
        events += [dict(h, kind="history") for h in load("history.jsonl") if h["date"] < tasks[-1]["date"]]
    events.sort(key=lambda e: (e["date"], e["kind"] != "history", e["id"]))
    first = next(i for i, e in enumerate(events) if e["kind"] == "task" and e["date"] >= TEST_FROM)
    db = Hydra(tenant=args.tenant, subtenant=f"django-{args.seed}-frozen")
    reset_scope(db)
    eng = Bearings(db, Params())
    t0 = time.time()
    for e in events[:first]:
        eng.ingest(e["id"], e["text"], e["files"] + e.get("test_files", []), date=e["date"], source=e["kind"], flush=False)
    eng.flush()
    print(f"frozen graph built from {first} events in {time.time() - t0:.0f}s", flush=True)
    test = [e for e in events[first:] if e["kind"] == "task"]

    def q(ev):
        ranked = [f["path"] for f in eng.context_pack(ev["text"], k=5, hops=2, repo=ROOT / "data/repos/django",
                                                             commit=ev["base_commit"]).files]
        return {"id": ev["id"], "ranked": ranked, "metrics": metrics(ranked, ev["files"])}

    with ThreadPoolExecutor(4) as ex, open(args.out, "w") as out:
        for i, row in enumerate(ex.map(q, test)):
            out.write(json.dumps(row) + "\n")
            if i % 100 == 0:
                print(f"{i}/{len(test)} ({time.time() - t0:.0f}s)", flush=True)
    print("done")


if __name__ == "__main__":
    main()
