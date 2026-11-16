"""Level 2: live localization runs through OpenCode (headless).

The agent gets the issue and a history-free checkout of the repo at the task's
base commit, explores, and names the files it would edit, then stops. Success
is checked in code against the files the real fix touched.

Conditions:
  none      no memory
  dict      the dictionary baseline's top-5 files, inlined in the prompt
  bearings  the Bearings MCP server connected to OpenCode; the agent is told to
            call get_context_pack first

Usage:
  uv run python bench/level2.py build-graph            # seed scope bench/django-l2 (events before CUTOFF)
  uv run python bench/level2.py run --tasks 30 --conditions none,dict,bearings
  uv run python bench/level2.py run --only django__django-11532 --conditions none   # trial
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bearings.anchors import definitions  # noqa: E402
from bearings.baselines import DictBaseline  # noqa: E402
from bearings.core import Bearings, Params, is_source  # noqa: E402
from bearings.db import Hydra  # noqa: E402

# DeepSeek V4.1 Flash, free tier through OpenCode (signed-in account key, see
# oc_auth). Fallback: L2_MODEL=deepseek/deepseek-flash uses the same model through
# the DeepSeek API (paid, capped by BALANCE_FLOOR).
MODEL = os.environ.get("L2_MODEL", "opencode/deepseek-v4.1-flash-free")
BALANCE_FLOOR = 0.05  # USD: stop starting new runs below this DeepSeek balance
CUTOFF = "2022-07-01"  # graph/dictionary learn from events before this; sample from after
SCOPE = ("bench", "django-l2")
RUNS = Path(os.environ["L2_RUNS"]) if os.environ.get("L2_RUNS") else ROOT / "runs" / "level2"
WORK = ROOT / "runs" / "tmp"
STEP_CAP = 25
MCP_PORT = 8766
import threading  # noqa: E402
_lock = threading.Lock()
_start_lock = threading.Lock()
_pack_lock = threading.Lock()
_engine = None


def bearings_engine():
    """Read-only engine on the Level 2 graph (history + tasks before CUTOFF)."""
    global _engine
    if _engine is None:
        _engine = Bearings(Hydra(tenant=SCOPE[0], subtenant=SCOPE[1]), Params())
        _engine.load(full=False)
    return _engine
TIMEOUT = 900
LIMIT_RE = re.compile(r"usage limit|rate.?limit|too many requests|quota|\b429\b", re.I)
AUTH = None

PROMPT = """You are localizing an issue in this repository (the Django source tree at /work/repo). Read the issue, explore the code as needed, and decide which source files must be edited to fix it. Everything you need is in this repository; do not search outside it. The upstream fix is not available anywhere, so do not look for it (no release notes, git objects or other versions). As soon as you have identified the files, stop and answer. Do not edit any files and do not run the test suite. Finish with one final line in exactly this form:
FILES: path/one.py, path/two.py
(repo-relative paths of the source files to edit, most likely first, at most 5).
{extra}
ISSUE:
{issue}"""

EXTRA = {
    "none": "",
    "dict": "\nFiles that past fixes with similar wording changed (from a word-to-file table built from this repo's history; may be wrong):\n{pack}\n",
    "anchors": "\nWhere identifiers named in the issue are defined in this checkout (from git grep; may be wrong):\n{pack}\n",
    "bearings": "\n{pack}\n",
    # ceiling test (bench/oracle_prereg.md): Bearings' format, filled from the real fix
    "oracle": "\n{pack}\n",
    # v1 delivery, kept for comparison: the agent pulls the pack through an MCP tool
    "bearings-mcp": "\nA Bearings MCP tool is available. Call bearings_get_context_pack with the issue text before you start exploring; it returns where past work on this repo landed.\n",
}

OC_ENV = {
    "OPENCODE_DISABLE_CLAUDE_CODE": "1",
    "OPENCODE_DISABLE_CLAUDE_CODE_SKILLS": "1",
    "OPENCODE_DISABLE_CLAUDE_CODE_PROMPT": "1",
}


def load(name: str) -> list[dict]:
    return [json.loads(line) for line in open(ROOT / "data/derived" / name)]


def events_before(cutoff: str) -> list[dict]:
    evs = [dict(h, kind="history") for h in load("history.jsonl") if h["date"] < cutoff]
    evs += [dict(t, kind="task", files=t["files"] + t["test_files"]) for t in load("tasks.jsonl") if t["date"] < cutoff]
    evs.sort(key=lambda e: (e["date"], e["id"]))
    return evs


def build_graph() -> None:
    sys.path.insert(0, str(ROOT / "bench"))
    from level1 import reset_scope

    db = Hydra(tenant=SCOPE[0], subtenant=SCOPE[1])
    reset_scope(db)
    eng = Bearings(db, Params())
    t0 = time.time()
    evs = events_before(CUTOFF)
    for i, e in enumerate(evs):
        eng.ingest(e["id"], e["text"], e["files"], date=e["date"], source=e["kind"], flush=False)
        if (i + 1) % 3000 == 0:
            eng.flush()
            print(f"{i + 1}/{len(evs)} ({time.time() - t0:.0f}s)", flush=True)
    eng.flush()
    print(f"built {SCOPE[0]}/{SCOPE[1]} from {len(evs)} events before {CUTOFF} in {time.time() - t0:.0f}s")


_GOLD = None


def oracle_pack(tid: str) -> str:
    """The real fix rendered as a Bearings pack: changed source files with the
    pre-fix line range of each hunk, and the test module from the test patch."""
    global _GOLD
    if _GOLD is None:
        import pyarrow.parquet as pq
        rows = pq.read_table(ROOT / "data/raw/full.parquet", columns=["instance_id", "patch", "test_patch"]).to_pylist()
        _GOLD = {r["instance_id"]: (r["patch"], r["test_patch"]) for r in rows}
    patch, test_patch = _GOLD[tid]
    files, cur = [], None
    for line in patch.splitlines():
        m = re.match(r"^diff --git a/(\S+) b/", line)
        if m:
            cur = [m.group(1), []]
            files.append(cur)
        m = re.match(r"^@@ -(\d+)(?:,(\d+))? ", line)
        if m and cur:
            a, n = int(m.group(1)), int(m.group(2) or 1)
            cur[1].append(f"lines {a}-{a + max(n, 1) - 1}")
    files = [f for f in files if is_source(f[0])]
    mods = []
    for t in re.findall(r"^diff --git a/tests/([^/\s]+)/", test_patch, re.M):
        if t not in mods:
            mods.append(t)
    lines = ["Bearings context pack: where past work on this repo landed, and where the task's identifiers "
             "are defined in this checkout. Read the listed lines first; search wider only if they do not fit.",
             "Start in:"]
    for i, (f, hunks) in enumerate(files, 1):
        lines.append(f"  {i}. {f}  " + ", ".join(hunks[:4]))
    if mods:
        lines.append("Verify with: ./tests/runtests.py " + " ".join(mods))
    return "\n".join(lines)


def sample(n: int, seed: int = 0) -> list[dict]:
    pool = [t for t in load("tasks.jsonl") if t["verified"] and t["date"] >= CUTOFF]
    rnd = random.Random(seed)
    rnd.shuffle(pool)
    return sorted(pool[:n], key=lambda t: t["date"])


def oc_config(cond: str) -> Path:
    cfg = {
        "$schema": "https://opencode.ai/config.json",
        "agent": {"locate": {"description": "Find the files to edit for an issue; never edits.",
                             "mode": "primary", "steps": STEP_CAP,
                             "permission": {"edit": "deny", "bash": "allow", "webfetch": "deny", "websearch": "deny",
                                            "codesearch": "deny", "external_directory": "deny"}}},
    }
    if cond == "bearings-mcp":
        # served over HTTP from outside the sandbox (see start_mcp), so the
        # agent's sandbox never contains the Bearings repo or its data
        cfg["mcp"] = {"bearings": {"type": "remote", "url": f"http://127.0.0.1:{MCP_PORT}/mcp", "enabled": True}}
    p = ROOT / "bench" / "opencode" / f"{cond}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(cfg, indent=2))
    return p


def tokens_to_first_gold(path: Path, gold: list[str]) -> int | None:
    """Total input tokens (uncached + cache read) of the steps up to and including
    the one in which the agent first reads or searches inside a file of the real
    fix (the file path appears in a tool call's input). None if it never does."""
    cum, found = 0, False
    for line in path.read_text().splitlines():
        try:
            e = json.loads(line)
        except ValueError:
            continue
        p = e.get("part", {})
        if e["type"] == "tool_use" and not found:
            inp = json.dumps(p.get("state", {}).get("input", {}))
            found = any(g in inp for g in gold)
        elif e["type"] == "step_finish":
            t = p.get("tokens", {})
            cum += t.get("input", 0) + t.get("cache", {}).get("read", 0)
            if found:
                return cum
    return cum if found else None


def parse_events(path: Path) -> dict:
    tok = {"input": 0, "output": 0, "reasoning": 0, "cache_read": 0, "cache_write": 0}
    tools, steps, text = [], 0, []
    errors = []
    for line in path.read_text().splitlines():
        try:
            e = json.loads(line)
        except ValueError:
            continue
        p = e.get("part", {})
        if e["type"] == "step_finish":
            steps += 1
            t = p.get("tokens", {})
            tok["input"] += t.get("input", 0)
            tok["output"] += t.get("output", 0)
            tok["reasoning"] += t.get("reasoning", 0)
            tok["cache_read"] += t.get("cache", {}).get("read", 0)
            tok["cache_write"] += t.get("cache", {}).get("write", 0)
        elif e["type"] == "tool_use":
            tools.append(p.get("tool"))
        elif e["type"] == "text":
            text.append(p.get("text", ""))
        elif e["type"] == "error":
            errors.append(json.dumps(e.get("error") or e)[:300])
    final = "\n".join(text)
    m = re.findall(r"FILES:\s*(.+)", final)
    files = []
    if m:
        files = [f.strip().strip("`").lstrip("./") for f in re.split(r"[,\s]+", m[-1]) if f.strip()]
        files = [f for f in files if "/" in f or f.endswith(".py")]
    return {"tokens": tok, "total_input": tok["input"] + tok["cache_read"] + tok["cache_write"],
            "tools": tools, "tool_calls": len(tools), "steps": steps, "files": files[:5],
            "errors": errors, "answered": bool(m)}


def score(pred: list[str], gold: list[str]) -> dict:
    g = {f for f in gold if is_source(f)}
    p = set(pred)
    return {"hit": int(bool(p & g)), "all": int(g <= p), "recall": len(p & g) / len(g) if g else 0.0}


NET = WORK / "net"


def deepseek_key() -> str | None:
    for line in (ROOT / ".env").read_text().splitlines() if (ROOT / ".env").exists() else []:
        k, _, v = line.partition("=")
        if k.strip().startswith("DEEPSEEK"):
            return v.strip().strip('"')
    return os.environ.get("DEEPSEEK_API_KEY")


def deepseek_balance() -> float | None:
    import urllib.request
    key = deepseek_key()
    if not key:
        return None
    req = urllib.request.Request("https://api.deepseek.com/user/balance", headers={"Authorization": f"Bearer {key}"})
    try:
        d = json.load(urllib.request.urlopen(req, timeout=20))
        return float(d["balance_infos"][0]["total_balance"])
    except Exception:  # noqa: BLE001
        return None


def oc_auth() -> str | None:
    """auth.json with only the provider the model needs, for the sandbox's fresh
    OpenCode data dir. Kept in runs/tmp (git-ignored); run logs are checked for
    the key before committing (scripts/check_secrets.sh)."""
    dst = WORK / "oc_auth.json"
    if MODEL.startswith("deepseek/"):
        key = deepseek_key()
        if not key:
            return None
        dst.write_text(json.dumps({"deepseek": {"type": "api", "key": key}}))
    else:
        src = Path.home() / ".local/share/opencode/auth.json"
        d = json.loads(src.read_text()) if src.exists() else {}
        if "opencode" not in d:
            return None
        dst.write_text(json.dumps({"opencode": d["opencode"]}))
    dst.chmod(0o600)
    return str(dst)


def start_net(with_mcp: bool) -> list[subprocess.Popen]:
    """The sandbox has no network. Outside it: an allow-list HTTPS proxy that
    only reaches the model provider, and a unix-socket relay to the MCP server."""
    NET.mkdir(parents=True, exist_ok=True)
    for f in ("proxy.sock", "mcp.sock"):
        (NET / f).unlink(missing_ok=True)
    procs = [subprocess.Popen([sys.executable, str(ROOT / "scripts/netproxy.py"), str(NET / "proxy.sock"),
                               str(RUNS / "netproxy.jsonl"), "opencode.ai", "models.dev", "api.deepseek.com"])]
    if with_mcp:
        procs.append(subprocess.Popen(["socat", f"UNIX-LISTEN:{NET / 'mcp.sock'},fork",
                                       f"TCP:127.0.0.1:{MCP_PORT}"]))
    for _ in range(50):
        if (NET / "proxy.sock").exists() and (not with_mcp or (NET / "mcp.sock").exists()):
            return procs
        time.sleep(0.1)
    raise SystemExit("network relays did not start")


def start_mcp() -> subprocess.Popen:
    env = dict(os.environ, BEARINGS_TEAM=SCOPE[0], BEARINGS_REPO=SCOPE[1], BEARINGS_READONLY="1",
               BEARINGS_LOG=str(RUNS / "mcp_calls.jsonl"))
    proc = subprocess.Popen(["uv", "run", "--quiet", "--directory", str(ROOT), "bearings-mcp", "--http", str(MCP_PORT)],
                            env=env, stdout=open(RUNS / "mcp_server.log", "a"), stderr=subprocess.STDOUT)
    import socket
    for _ in range(60):
        try:
            socket.create_connection(("127.0.0.1", MCP_PORT), timeout=1).close()
            return proc
        except OSError:
            time.sleep(1)
    raise SystemExit("bearings MCP HTTP server did not start")


ESCAPE_RE = re.compile(r"/home/|/root\b|/var/|/opt/|/mnt/|/srv/|\bfind\s+/(?:\s|$)|\.\./\.\./\.\.|~/"
                       r"|\bcurl\b|\bwget\b|https?://|urllib|requests\.|\bpip\s+(?:download|install)")
WEB_TOOLS = {"websearch", "webfetch", "codesearch"}


def outside_access(ev_path: Path) -> list[str]:
    """Tool inputs that try to reach outside the sandboxed repo (the sandbox
    blocks them; this records the attempt)."""
    bad = []
    for line in ev_path.read_text().splitlines():
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if e.get("type") == "tool_use":
            inp = json.dumps(e.get("part", {}).get("state", {}).get("input", {}))
            if e.get("part", {}).get("tool") in WEB_TOOLS or ESCAPE_RE.search(inp):
                bad.append(inp[:160])
    return bad


def run_one(task: dict, cond: str, dic: DictBaseline | None, rep: int = 0) -> dict:
    out_dir = RUNS / cond
    out_dir.mkdir(parents=True, exist_ok=True)
    ev_path = out_dir / f"{task['id']}.r{rep}.jsonl"
    wt = WORK / f"wt-{cond}-{task['id']}-r{rep}"
    subprocess.run([str(ROOT / "scripts/snapshot.sh"), str(ROOT / "data/repos/django"), task["base_commit"], str(wt)],
                   check=True)
    extra = EXTRA[cond]
    pack_text = ""
    if cond == "dict":
        pack_text = "\n".join(f"  {f}" for f in dic.rank(task["text"], k=5))
        extra = extra.format(pack=pack_text or "  (none)")
    elif cond == "anchors":
        sc, where = definitions(ROOT / "data/repos/django", task["base_commit"], task["text"], detail=True)
        top = sorted(sc.items(), key=lambda kv: (-kv[1], kv[0]))[:5]
        pack_text = "\n".join(f"  {f}  defines " + ", ".join(f"{n} (line {ln})" for ln, n in sorted(where[f])[:3])
                              for f, _ in top)
        extra = extra.format(pack=pack_text or "  (none)")
    elif cond == "oracle":
        pack_text = oracle_pack(task["id"])
        extra = extra.format(pack=pack_text)
    elif cond == "bearings":
        # pushed into the prompt (like the Claude Code hook): no tool lookup, no extra turn
        with _pack_lock:
            pk = bearings_engine().context_pack(task["text"], k=5, repo=ROOT / "data/repos/django",
                                                commit=task["base_commit"])
        pack_text = pk.render()
        extra = extra.format(pack=pack_text)
    prompt = PROMPT.format(extra=extra, issue=task["text"])
    cfg_path = oc_config(cond)
    attempts = 0
    while True:
        attempts += 1
        with _start_lock:  # stagger starts: concurrent opencode launches lock its sqlite db
            time.sleep(5)
        t0 = time.time()
        data_dir = WORK / f"ocdata-{cond}-{task['id']}-r{rep}"
        subprocess.run(["rm", "-rf", str(data_dir)])
        with open(ev_path, "w") as fo, open(ev_path.with_suffix(".err"), "w") as fe:
            proc = subprocess.Popen([str(ROOT / "scripts/sandbox_opencode.sh"), str(wt), str(cfg_path), str(data_dir), str(NET), "--",
                                     "run", "--print-logs", "--log-level", "WARN", "--title", "bench", "--format", "json",
                                     "--agent", "locate", "-m", MODEL, "--dir", "/work/repo", prompt],
                                    stdin=subprocess.DEVNULL, stdout=fo, stderr=fe,
                                    env=dict(os.environ, **({"OC_AUTH": AUTH} if AUTH else {})))
            code = None
            while code is None:
                try:
                    code = proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    err = ev_path.with_suffix(".err").read_text(errors="replace")
                    if LIMIT_RE.search(err) or time.time() - t0 > TIMEOUT:
                        reason = "rate_limit" if LIMIT_RE.search(err) else "timeout"
                        proc.terminate()
                        try:
                            proc.wait(timeout=10)
                        except subprocess.TimeoutExpired:
                            proc.kill()
                        code = reason
        subprocess.run(["rm", "-rf", str(data_dir)])
        wall = time.time() - t0
        res = parse_events(ev_path)
        # infrastructure failure before the model ran (e.g. opencode's db locked): retry
        if code == "rate_limit" and attempts < 6:
            time.sleep(90 * attempts)  # back off, then try again; counted in `attempts`
            continue
        if code != 0 and code != "rate_limit" and res["steps"] == 0 and attempts < 3:
            continue
        break
    err_text = ev_path.with_suffix(".err").read_text()[-4000:]
    rate_limited = code == "rate_limit" or bool(LIMIT_RE.search(err_text + " ".join(res["errors"])))
    subprocess.run(["rm", "-rf", str(wt)])
    leaks = outside_access(ev_path)
    row = {"id": task["id"], "date": task["date"], "condition": cond, "rep": rep, "model": MODEL,
           "exit": code, "attempts": attempts, "wall_s": round(wall, 1), "rate_limited": rate_limited, "gold": task["files"],
           "dict_pack": pack_text, "sandboxed": True, "outside_access": leaks,
           "tokens_to_first_gold": tokens_to_first_gold(ev_path, task["files"]), **res, **score(res["files"], task["files"])}
    with _lock, open(RUNS / "results.jsonl", "a") as f:
        f.write(json.dumps(row) + "\n")
    return row


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build-graph")
    r = sub.add_parser("run")
    r.add_argument("--tasks", type=int, default=30)
    r.add_argument("--only", default=None)
    r.add_argument("--conditions", default="none,dict,anchors,bearings")
    r.add_argument("--seed", type=int, default=0)
    r.add_argument("--skip-done", action="store_true")
    r.add_argument("--parallel", type=int, default=3)
    r.add_argument("--stride", type=int, default=1, help="take every Nth sampled task (fixed rule)")
    r.add_argument("--reps", type=int, default=1)
    args = ap.parse_args()
    if args.cmd == "build-graph":
        build_graph()
        return
    RUNS.mkdir(parents=True, exist_ok=True)
    tasks = [t for t in load("tasks.jsonl") if t["id"] == args.only] if args.only else sample(args.tasks, args.seed)[::args.stride]
    conds = args.conditions.split(",")
    dic = DictBaseline()
    if "dict" in conds:
        for e in events_before(CUTOFF):
            dic.ingest(e["text"], e["files"])
    done = set()
    if args.skip_done and (RUNS / "results.jsonl").exists():
        for line in open(RUNS / "results.jsonl"):
            r0 = json.loads(line)
            if not r0["rate_limited"] and r0["answered"]:
                done.add((r0["id"], r0["condition"], int(r0.get("rep", 0))))
    jobs = [(t, c, k) for t in tasks for k in range(args.reps) for c in conds if (t["id"], c, k) not in done]
    mcp_proc = start_mcp() if "bearings-mcp" in conds else None
    net_procs = start_net("bearings-mcp" in conds)
    global AUTH
    AUTH = oc_auth()
    # all conditions of one task run at the same time, so time-of-day and
    # rate-limit drift hit every condition equally

    stop = {"low": False}

    def job(tc):
        t, c, k = tc
        if MODEL.startswith("deepseek/"):
            bal = deepseek_balance()
            if bal is not None and bal < BALANCE_FLOOR or stop["low"]:
                stop["low"] = True
                print(f"skip {t['id']} {c}: DeepSeek balance {bal} below floor {BALANCE_FLOOR}", flush=True)
                return None
        row = run_one(t, c, dic, rep=k)
        print(f"{t['id']} {c} r{k}: hit={row['hit']} all={row['all']} files={row['files']} "
              f"in={row['total_input']} out={row['tokens']['output']} tools={row['tool_calls']} "
              f"{row['wall_s']}s exit={row['exit']} rl={row['rate_limited']}", flush=True)

    from concurrent.futures import ThreadPoolExecutor
    try:
        with ThreadPoolExecutor(args.parallel) as ex:
            list(ex.map(job, jobs))
    finally:
        if mcp_proc:
            mcp_proc.terminate()
        for p in net_procs:
            p.terminate()


if __name__ == "__main__":
    main()
