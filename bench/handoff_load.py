"""Load test for the handoff graph: N concurrent clients request packs for
60 s while a writer keeps recording runs into the same scope.

  uv run python bench/handoff_load.py --clients 20 --seconds 60
Writes results/handoff_load.json.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bench"))
sys.path.insert(0, str(ROOT / "src"))

import handoff as H  # noqa: E402
from bearings import handoff as HO  # noqa: E402
from bearings.db import Hydra  # noqa: E402

LOAD_SCOPE = ("bench", "handoff-load")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--clients", type=int, default=20)
    ap.add_argument("--seconds", type=int, default=60)
    args = ap.parse_args()
    runs = H.prior_runs()
    g0 = HO.HydraGraph(Hydra(tenant=LOAD_SCOPE[0], subtenant=LOAD_SCOPE[1]))
    g0.reset()
    half = len(runs) // 2
    g0.record(runs[:half])
    tasks = H.pool(runs)
    queries = [H.task_sources(t) for t in tasks]          # entity extraction + git grep done up front
    lat, errors, packs = [], [], []
    stop = time.time() + args.seconds
    lock = threading.Lock()

    def client(i):
        g = HO.HydraGraph(Hydra(tenant=LOAD_SCOPE[0], subtenant=LOAD_SCOPE[1]))
        rnd = random.Random(i)
        while time.time() < stop:
            terms, anchors = rnd.choice(queries)
            t0 = time.perf_counter()
            try:
                pk = HO.build_pack(g, terms, anchors, None, H.FINAL)
                ok = True
            except Exception as e:  # noqa: BLE001
                ok = False
                with lock:
                    errors.append(repr(e)[:200])
            dt = time.perf_counter() - t0
            with lock:
                lat.append(dt)
                if ok:
                    packs.append(len(pk["source"]))

    written = {"runs": 0}

    def writer():
        g = HO.HydraGraph(Hydra(tenant=LOAD_SCOPE[0], subtenant=LOAD_SCOPE[1]))
        for r in runs[half:]:
            if time.time() >= stop:
                break
            g.record([r], threads=4)
            written["runs"] += 1

    th = [threading.Thread(target=client, args=(i,)) for i in range(args.clients)] + [threading.Thread(target=writer)]
    t0 = time.time()
    for t in th:
        t.start()
    for t in th:
        t.join()
    wall = time.time() - t0
    lat.sort()
    q = lambda p: round(1000 * lat[min(int(p * len(lat)), len(lat) - 1)], 1)  # noqa: E731
    out = {"clients": args.clients, "seconds": args.seconds, "wall_s": round(wall, 1), "requests": len(lat),
           "errors": len(errors), "error_samples": errors[:3], "p50_ms": q(0.5), "p95_ms": q(0.95), "p99_ms": q(0.99),
           "rps": round(len(lat) / wall, 1), "runs_recorded_during_test": written["runs"],
           "graph_runs_at_start": half, "empty_packs": sum(1 for n in packs if n == 0),
           "calls_per_pack": "6 length-1 algo.MSpaths traversals (hop 1 x2, hop 2, file frequency, hop 3 x2)"}
    (ROOT / "results" / "handoff_load.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
