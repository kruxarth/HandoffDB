"""Level 1: retrieval quality on the SWE-bench Django task stream. No model calls.

Every task is answered using only what was learned from events dated before it
(history commits and earlier tasks), then learned from. Conditions:

  bm25        keyword search over past task/commit texts
  dict        plain table of learned entity->file counts (no graph)
  bearings-1  Bearings, POINTS_TO only (no second hop)
  bearings    Bearings, full (POINTS_TO + CO_CHANGED)
  frozen      Bearings graph built once before the first test task, never updated

Scenarios (--seed):
  tasks    the graph learns only from the task stream (a team starting from zero)
  history  the graph is first seeded from Django's issue-fix commits, then learns
           from history and tasks as they happen (cold start solved)

Usage:
  uv run python bench/level1.py --seed tasks   --out results/level1_tasks.jsonl
  uv run python bench/level1.py --seed history --out results/level1_history.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bearings.baselines import BM25Baseline, DictBaseline  # noqa: E402
from bearings.core import Bearings, Params, is_source, test_command  # noqa: E402
from bearings.db import Hydra  # noqa: E402

TEST_FROM = "2019-07-01"  # tasks before this date are the dev split (tuning only)


def load(name: str) -> list[dict]:
    return [json.loads(line) for line in open(ROOT / "data/derived" / name)]


def reset_scope(db: Hydra, labels=("Term", "File", "Task", "TestCmd")) -> None:
    for lab in labels:
        while True:
            ids = [r[0] for r in db.query(f"MATCH (n:{lab}) RETURN n.id AS id LIMIT 1000")]
            if not ids:
                break
            db.batch("UNWIND $rows AS row MATCH (n {id: row.id}) DETACH DELETE n", [{"id": i} for i in ids])


def metrics(ranked: list[str], gold: list[str]) -> dict:
    g = {f for f in gold if is_source(f)}
    out = {}
    for k in (1, 3, 5):
        top = set(ranked[:k])
        out[f"hit@{k}"] = int(bool(top & g))
        out[f"recall@{k}"] = len(top & g) / len(g) if g else 0.0
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", choices=["tasks", "history"], default="tasks")
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=0, help="stop after N tasks (debug)")
    ap.add_argument("--hop-penalty", type=float, default=Params.hop_penalty)
    ap.add_argument("--beta", type=float, default=Params.beta)
    ap.add_argument("--tenant", default="bench")
    args = ap.parse_args()

    tasks = load("tasks.jsonl")
    if args.limit:
        tasks = tasks[: args.limit]
    events = [dict(t, kind="task") for t in tasks]
    if args.seed == "history":
        events += [dict(h, kind="history") for h in load("history.jsonl") if h["date"] < tasks[-1]["date"]]
    events.sort(key=lambda e: (e["date"], e["kind"] != "history", e["id"]))

    params = Params(hop_penalty=args.hop_penalty, beta=args.beta)
    live_db = Hydra(tenant=args.tenant, subtenant=f"django-{args.seed}")
    frozen_db = Hydra(tenant=args.tenant, subtenant=f"django-{args.seed}-frozen")
    for db in (live_db, frozen_db):
        reset_scope(db)
    live = Bearings(live_db, params)
    frozen = Bearings(frozen_db, params)
    bm25, dic = BM25Baseline(), DictBaseline()
    frozen_built = False

    out = open(args.out, "w")
    learned_tasks = 0
    learned_events = 0
    t0 = time.time()
    for ev in events:
        is_test = ev["kind"] == "task" and ev["date"] >= TEST_FROM
        if ev["kind"] == "task":
            if is_test and not frozen_built:
                frozen_built = True  # frozen = live state at the first test task
                # replay everything learned so far into the frozen scope
                for past in events:
                    if past is ev:
                        break
                    frozen.ingest(past["id"], past["text"], past["files"] + past.get("test_files", []), date=past["date"], source=past["kind"], flush=False)
                frozen.flush()
            row = {"id": ev["id"], "date": ev["date"], "split": "test" if is_test else "dev",
                   "verified": ev["verified"], "lite": ev["lite"], "learned_tasks": learned_tasks,
                   "learned_events": learned_events, "gold": ev["files"]}
            q0 = time.time()
            p_full = live.context_pack(ev["text"], k=5, hops=2)
            row["latency_full_ms"] = round((time.time() - q0) * 1000, 1)
            q0 = time.time()
            p_one = live.context_pack(ev["text"], k=5, hops=1)
            row["latency_one_ms"] = round((time.time() - q0) * 1000, 1)
            ranks = {
                "bm25": bm25.rank(ev["text"]),
                "dict": dic.rank(ev["text"]),
                "bearings-1": [f["path"] for f in p_one.files],
                "bearings": [f["path"] for f in p_full.files],
            }
            if frozen_built:
                ranks["frozen"] = [f["path"] for f in frozen.context_pack(ev["text"], k=5, hops=2).files]
            row["ranked"] = ranks
            row["metrics"] = {c: metrics(r, ev["files"]) for c, r in ranks.items()}
            gold_cmds = {test_command(f) for f in ev["test_files"]} - {None}
            row["test_cmd"] = p_full.test_command
            row["test_cmd_hit"] = p_full.test_command in gold_cmds
            # the database's answer vs the in-memory reference implementation
            row["db_matches_reference"] = [f["path"] for f in live.context_pack(ev["text"], k=5, hops=2, backend="local").files] == ranks["bearings"]
            row["pack_chars"] = len(p_full.render())
            out.write(json.dumps(row) + "\n")
            out.flush()
            # learn from the outcome: misses on what was suggested, then the real fix
            live.feedback(p_full, ev["files"])
            learned_tasks += 1
        changed = ev["files"] + ev.get("test_files", [])
        live.ingest(ev["id"], ev["text"], changed, date=ev["date"], source=ev["kind"], flush=False)
        bm25.ingest(ev["text"], changed)
        dic.ingest(ev["text"], changed)
        learned_events += 1
        if learned_events % 500 == 0:
            print(f"{learned_events}/{len(events)} events, {learned_tasks} tasks, "
                  f"{time.time() - t0:.0f}s, {live_db.requests} requests", flush=True)
    print(f"done: {learned_tasks} tasks, {learned_events} events, {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
