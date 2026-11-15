"""Bearings command line.

  bearings import-history <repo-path> [--team T] [--repo R] [--since 2015-01-01] [--github owner/name]
  bearings pack "<task text>" [--team T] [--repo R]
  bearings report "<task text>" --changed a.py b.py [--read c.py] [--test "cmd"] [--failed]
  bearings stats [--team T] [--repo R]
  bearings hook | hook-stop          Claude Code hooks (see `bearings hooks-config`)
  bearings hooks-config              print the .claude/settings.json hooks block

The pack combines the learned graph with code anchors from the current checkout
(the git work tree of the working directory; --no-code to disable).
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from .anchors import changed_files, checkout_root
from .core import Bearings, Pack, Params
from .db import Hydra
from .history import git_history, github_prs


def _engine(args, full: bool = False) -> Bearings:
    eng = Bearings(Hydra(tenant=args.team, subtenant=args.repo), Params())
    eng.load(full=full)
    return eng


STATE = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "bearings" / "sessions"


def _save_session(sid: str, data: dict) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    (STATE / f"{sid[:64]}.json").write_text(json.dumps(data))


def _load_session(sid: str) -> dict | None:
    p = STATE / f"{sid[:64]}.json"
    return json.loads(p.read_text()) if p.exists() else None


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
    p.add_argument("--no-code", action="store_true", help="learned graph only, no code anchors")
    r = sub.add_parser("report", help="record a finished task")
    r.add_argument("task")
    r.add_argument("--changed", nargs="+", required=True)
    r.add_argument("--read", nargs="*", default=[])
    r.add_argument("--test", default=None)
    r.add_argument("--failed", action="store_true")
    sub.add_parser("stats", help="graph size")
    sub.add_parser("hook", help="Claude Code UserPromptSubmit hook: add the context pack to the prompt")
    sub.add_parser("hook-stop", help="Claude Code Stop hook: learn from the files the agent changed")
    sub.add_parser("hooks-config", help="print the hooks block for .claude/settings.json")
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
        repo = None if args.no_code else checkout_root(Path.cwd())
        pack = _engine(args).context_pack(args.task, k=args.k, repo=repo)
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
    elif args.cmd == "hook":
        # Reads the hook event on stdin; prints additionalContext. Never fails the prompt.
        import sys
        try:
            event = json.load(sys.stdin)
            prompt = event.get("prompt", "")
            repo = checkout_root(event.get("cwd") or Path.cwd())
            pack = _engine(args).context_pack(prompt, k=5, repo=repo) if len(prompt) > 40 else None
            if pack and pack.files:
                _save_session(event.get("session_id", "x"), {"prompt": prompt, "repo": str(repo or ""),
                                                             "files": [{"path": f["path"], "terms": f["terms"]} for f in pack.files]})
                print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit",
                                                         "additionalContext": pack.render()}}))
        except Exception as exc:  # noqa: BLE001
            print(f"bearings hook skipped: {exc}", file=sys.stderr)
    elif args.cmd == "hook-stop":
        # Learns from what the agent actually changed, with no agent turn: misses on
        # suggested files that were not changed, then the task itself.
        import sys
        try:
            event = json.load(sys.stdin)
            st = _load_session(event.get("session_id", "x"))
            repo = checkout_root(event.get("cwd") or (st or {}).get("repo") or Path.cwd())
            changed = changed_files(repo) if repo else []
            if st and changed and os.environ.get("BEARINGS_READONLY") != "1":
                eng = _engine(args)
                eng.feedback(Pack(files=st["files"]), changed)
                eng.ingest("agent:" + event.get("session_id", str(time.time()))[:16], st["prompt"], changed,
                           date=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), source="agent")
                print(f"bearings: learned {len(changed)} changed files", file=sys.stderr)
        except Exception as exc:  # noqa: BLE001
            print(f"bearings stop hook skipped: {exc}", file=sys.stderr)
    elif args.cmd == "hooks-config":
        here = Path(__file__).resolve().parents[2]
        env = f"BEARINGS_TEAM={args.team} BEARINGS_REPO={args.repo}"
        run = f"{env} uv run --quiet --directory {here} bearings"
        print(json.dumps({"hooks": {
            "UserPromptSubmit": [{"hooks": [{"type": "command", "command": f"{run} hook"}]}],
            "Stop": [{"hooks": [{"type": "command", "command": f"{run} hook-stop"}]}]}}, indent=2))
    elif args.cmd == "stats":
        eng = _engine(args, full=True)
        print(json.dumps({"tasks": eng.n_events, "terms": len(eng.df), "files": len(eng.files),
                          "points_to": len(eng.n), "co_changed": sum(len(v) for v in eng.co_written.values())}))


if __name__ == "__main__":
    main()
