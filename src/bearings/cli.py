"""Bearings command line.

  bearings import-history <repo-path> [--team T] [--repo R] [--since 2015-01-01] [--github owner/name]
  bearings pack "<task text>" [--team T] [--repo R]
  bearings report "<task text>" --changed a.py b.py [--read c.py] [--test "cmd"] [--failed]
  bearings stats [--team T] [--repo R]
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from .core import Bearings, Params
from .db import Hydra
from .history import git_history, github_prs


def _engine(args, full: bool = False) -> Bearings:
    eng = Bearings(Hydra(tenant=args.team, subtenant=args.repo), Params())
    eng.load(full=full)
    return eng


def main() -> None:
    ap = argparse.ArgumentParser(prog="bearings")
    ap.add_argument("--team", default=os.environ.get("BEARINGS_TEAM", "default-team"))
    ap.add_argument("--repo", default=os.environ.get("BEARINGS_REPO", Path.cwd().name))
    sub = ap.add_subparsers(dest="cmd", required=True)
    h = sub.add_parser("import-history", help="seed the graph from merged history")
    h.add_argument("path", nargs="?", default=".")
    h.add_argument("--since", default=None)
    h.add_argument("--until", default=None, help="only events before this ISO date")
    h.add_argument("--github", default=None, help="owner/name: use merged PRs via gh instead of git log")
    h.add_argument("--limit", type=int, default=1000)
    p = sub.add_parser("pack", help="print a context pack")
    p.add_argument("task")
    p.add_argument("-k", type=int, default=5)
    p.add_argument("--json", action="store_true")
    r = sub.add_parser("report", help="record a finished task")
    r.add_argument("task")
    r.add_argument("--changed", nargs="+", required=True)
    r.add_argument("--read", nargs="*", default=[])
    r.add_argument("--test", default=None)
    r.add_argument("--failed", action="store_true")
    sub.add_parser("stats", help="graph size")
    args = ap.parse_args()

    if args.cmd == "import-history":
        eng = _engine(args, full=True)
        events = github_prs(args.github, args.limit) if args.github else git_history(args.path, since=args.since)
        n, t0 = 0, time.time()
        for ev in events:
            if args.until and ev["date"] >= args.until:
                break
            eng.ingest(ev["id"], ev["text"], ev["files"], date=ev["date"], source=ev["source"], flush=False)
            n += 1
            if n % 2000 == 0:
                eng.flush()
                print(f"{n} events ({time.time() - t0:.0f}s)", flush=True)
        eng.flush()
        print(f"imported {n} events into {args.team}/{args.repo} in {time.time() - t0:.0f}s")
    elif args.cmd == "pack":
        pack = _engine(args).context_pack(args.task, k=args.k)
        if args.json:
            print(json.dumps({"files": [{k: v for k, v in f.items() if k != "terms"} for f in pack.files],
                              "test_command": pack.test_command, "entities": pack.entities}, indent=2))
        else:
            print(pack.render())
    elif args.cmd == "report":
        eng = _engine(args)
        tid = "cli:" + str(int(time.time()))
        print(eng.ingest(tid, args.task, args.changed, read=args.read, test_cmd=args.test, passed=not args.failed,
                         date=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), source="cli"))
    elif args.cmd == "stats":
        eng = _engine(args, full=True)
        print(json.dumps({"tasks": eng.n_events, "terms": len(eng.df), "files": len(eng.files),
                          "points_to": len(eng.n), "co_changed": sum(len(v) for v in eng.co_written.values())}))


if __name__ == "__main__":
    main()
