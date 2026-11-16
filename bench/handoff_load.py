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
    ap.add_argument("--write-every", type=float, default=0.0, help="seconds between recorded runs (0 = as fast as possible)")
    ap.add_argument("--out", default="handoff_load.json")
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
            t0 = time.time()
            g.record([r], threads=4)
            written["runs"] += 1
            if args.write_every:
                time.sleep(max(0.0, args.write_every - (time.time() - t0)))

    # clients are separate processes (as real agents' hooks would be), so the Python
    # client's own decoding does not serialise them; the writer is a thread here
    import multiprocessing as mp
    ctx = mp.get_context("fork")
    q = ctx.Queue()

    def proc_client(i):
        client(i)
        q.put((lat, errors, packs))
    procs = [ctx.Process(target=proc_client, args=(i,)) for i in range(args.clients)]
    wt = threading.Thread(target=writer)
    t0 = time.time()
    for p_ in procs:
        p_.start()
    wt.start()
    for _ in procs:
        a, b, c = q.get()
        lat.extend(a); errors.extend(b); packs.extend(c)
    for p_ in procs:
        p_.join()
    wt.join()
    wall = time.time() - t0
    lat.sort()
    q = lambda p: round(1000 * lat[min(int(p * len(lat)), len(lat) - 1)], 1)  # noqa: E731
    out = {"clients": args.clients, "seconds": args.seconds, "wall_s": round(wall, 1), "requests": len(lat),
           "errors": len(errors), "error_samples": errors[:3], "p50_ms": q(0.5), "p95_ms": q(0.95), "p99_ms": q(0.99),
           "rps": round(len(lat) / wall, 1), "runs_recorded_during_test": written["runs"],
           "write_every_s": args.write_every,
           "graph_runs_at_start": half, "empty_packs": sum(1 for n in packs if n == 0),
           "calls_per_pack": "4 length-1 algo.MSpaths traversals in 3 rounds (hop 1: entities and anchors in parallel; hop 2; file frequencies)"}
    (ROOT / "results" / args.out).write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
