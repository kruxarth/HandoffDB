"""Handoff graph: what earlier agent runs read and concluded, as structure in HydraDB.

A later agent on a different task traverses it instead of re-exploring.
Pre-registration: bench/handoff_prereg.md.

  (:HTerm {key})  -[:ABOUT {w}]->    (:HRun {key, issue, date})    entity of the run's task
  (:HFile {path}) -[:READ_BY {w}]->  (:HRun)                       a run opened this file
  (:HRun)         -[:READ {w, lines, n}]-> (:HFile)                what it opened, which lines
  (:HRun)         -[:CONCLUDED {w}]->      (:HFile)                files in its final answer

Read side: two ``algo.MSpaths`` calls of length 2, from the new task's entities
(HTerm -> HRun -> HFile) and from the files that define the task's identifiers
(HFile -> HRun -> HFile). No model calls anywhere in the graph condition.

  uv run python bench/handoff.py record                 # logged runs -> HydraDB
  uv run python bench/handoff.py targets                # the fixed target list
  uv run python bench/handoff.py retrieval              # no-model-call tables (learning curve, ablation)
  uv run python bench/handoff.py notes                  # handoff-file baseline (one model call per earlier run)
  uv run python bench/handoff.py run --tasks 12         # live runs
  uv run python bench/handoff.py report
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bench"))
sys.path.insert(0, str(ROOT / "src"))

import level2  # noqa: E402
from bearings import handoff as HO  # noqa: E402
from bearings.anchors import definitions  # noqa: E402
from bearings.core import is_source  # noqa: E402
from bearings.db import Hydra, cypher_strings  # noqa: E402

SCOPE = ("bench", "handoff-v2")
OLD = ROOT / "runs" / "level2" / "none"          # 40 runs logged for Level 2 (DeepSeek API)
RUNS = ROOT / "runs" / "handoff"
PRIOR = RUNS / "prior"                           # cold runs on the memory issues (Refuseless)
# Fixed date rules (bench/handoff_prereg.md)
MEMORY_FROM, MEMORY_TO = "2021-01-01", "2022-07-01"  # every SWE-bench Django issue in this window gets one cold run
TARGET_FROM = "2022-07-01"                           # targets: issues from here on
DEV_FROM = "2022-01-01"                              # dev (tuning) targets: memory issues from here to MEMORY_TO
NOTES = RUNS / "notes"
REPO = ROOT / "data/repos/django"
FILE_RE = re.compile(r"(?:/work/repo/|\./|(?<![\w/]))((?:django|tests|docs)/[\w/.-]+\.(?:py|txt|html|json))")
SED_RE = re.compile(r"sed\s+-n\s+['\"]?(\d+),(\d+)p['\"]?\s+(\S+)")
MAX_TERMS = 60

PROMPT = """You are planning a fix for an issue in this repository (the Django source tree at /work/repo). Read the issue, explore the code as needed, and decide (1) which source files must be edited to fix it and (2) which existing test file the regression test for it belongs in. Everything you need is in this repository; do not search outside it. The upstream fix is not available anywhere, so do not look for it (no release notes, git objects or other versions). As soon as you have decided both, stop and answer. Do not edit any files and do not run the test suite. Finish with two final lines in exactly this form:
FILES: path/one.py, path/two.py
TESTS: tests/some_app/test_file.py
(repo-relative paths; FILES are the source files to edit, most likely first, at most 5; TESTS are existing test files, at most 3).
{extra}
ISSUE:
{issue}"""

EXTRA = {
    "cold": "",
    "notes": "\nEarlier agent sessions on this repository left handoff notes, one Markdown file per session, in /work/repo/HANDOFF/ ({n} files). They were written for other issues; read the ones that are relevant if that helps.\n",
    "graph": "\n{pack}\n",
}


def tasks_by_id() -> dict:
    return {t["id"]: t for t in level2.load("tasks.jsonl")}


# ---------------------------------------------------------------- recorded runs

def _usable(p: Path) -> bool:
    """A run that started and produced at least one step (rate-limited / never started runs are dropped)."""
    try:
        return any('"step_finish"' in line for line in p.read_text().splitlines())
    except OSError:
        return False


def prior_runs(include_old: bool = True, include_new: bool = True) -> list[dict]:
    """The recorded runs the graph learns from, one per issue, oldest issue first:
    the cold memory runs (runs/handoff/prior, Refuseless) and the 40 logged Level 2
    runs (DeepSeek API). Only what they opened and concluded is used, never their tokens."""
    T = tasks_by_id()
    out, seen = [], set()
    # a run counts only once its result row is written (killed / rate-limited runs are dropped)
    finished = {q["id"] for q in map(json.loads, open(PRIOR / "results.jsonl"))
                if not q["rate_limited"] and q["steps"] > 0} if (PRIOR / "results.jsonl").exists() else set()
    dirs = ([(PRIOR, "refuseless")] if include_new else []) + ([(OLD, "deepseek-api")] if include_old else [])
    for d, src in dirs:
        for p in sorted(d.glob("*.r0.jsonl")):
            iid = p.name.split(".")[0]
            if iid in T and iid not in seen and _usable(p) and (src != "refuseless" or iid in finished):
                seen.add(iid)
                out.append({"key": iid, "issue": iid, "date": T[iid]["date"], "text": T[iid]["text"], "path": p,
                            "src": src, **HO.parse_opencode(p)})
    return sorted(out, key=lambda r: (r["date"], r["key"]))


def memory_tasks() -> list[dict]:
    """Fixed rule: every SWE-bench Django issue dated in [MEMORY_FROM, MEMORY_TO), date order."""
    out = []
    for t in sorted(level2.load("tasks.jsonl"), key=lambda t: t["date"]):
        if MEMORY_FROM <= t["date"] < MEMORY_TO:
            out.append(dict(t, gold_tests=gold_tests(t), gold_src=[f for f in t["files"] if is_source(f)]))
    return out


_ANCH: dict = {}


def task_sources(task: dict) -> tuple[list[str], list[str]]:
    """The task's entities and its code anchors (files defining identifiers it names, by git grep at its commit)."""
    if task["id"] not in _ANCH:
        sc = definitions(REPO, task["base_commit"], task["text"])
        _ANCH[task["id"]] = [f for f, _ in sorted(sc.items(), key=lambda kv: (-kv[1], kv[0]))[:8]]
    return HO.run_terms(task["text"]), _ANCH[task["id"]]


def build_pack(g, task: dict, allowed: set[str] | None, P: HO.Params | None = None) -> dict:
    terms, anchors = task_sources(task)
    return HO.build_pack(g, terms, anchors, allowed, P)


def graph_pack_text(g, task: dict, allowed: set[str] | None, P: HO.Params | None = None) -> str:
    pk = build_pack(g, task, allowed, P)
    return HO.render(pk, g.run_info(pk["runs"][:3]))


render = HO.render
tokens = HO.tokens
FINAL = HO.Params()   # the pack design fixed on the dev set (see tune and bench/handoff_prereg.md)


# ---------------------------------------------------------------- targets

def gold_tests(task: dict) -> list[str]:
    """Test files the real fix changed that already exist at the issue's commit."""
    out = []
    for f in task["test_files"]:
        if f.endswith(".py") and subprocess.run(["git", "-C", str(REPO), "cat-file", "-e", f"{task['base_commit']}:{f}"],
                                                capture_output=True).returncode == 0:
            out.append(f)
    return out


def pool(runs: list[dict] | None = None) -> list[dict]:
    """Targets (fixed rule): every SWE-bench Django issue dated from TARGET_FROM on, with no
    recorded run, whose real fix touches a source file and extends an existing test file."""
    have = {r["issue"] for r in runs or []}
    out = []
    for t in sorted(level2.load("tasks.jsonl"), key=lambda t: t["date"]):
        if t["id"] in have or t["date"] < TARGET_FROM:
            continue
        gt = gold_tests(t)
        if gt and [f for f in t["files"] if is_source(f)]:
            out.append(dict(t, gold_tests=gt, gold_src=[f for f in t["files"] if is_source(f)]))
    return out


def dev_set() -> list[dict]:
    """Tuning only: memory issues dated in [DEV_FROM, MEMORY_TO) with an existing test file;
    each uses memory runs on issues dated before it (leave-future-out)."""
    return [t for t in memory_tasks() if t["date"] >= DEV_FROM and t["gold_tests"] and t["gold_src"]]


def same_tasks(runs: list[dict], n: int = 40) -> list[dict]:
    """Experiment B issues (fixed rule): the n latest memory issues whose fix extends an
    existing test file and whose memory run was recorded."""
    have = {r["issue"] for r in runs if r["src"] == "refuseless"}
    xs = [t for t in memory_tasks() if t["gold_tests"] and t["gold_src"] and t["id"] in have]
    return xs[-n:]


def earlier(runs: list[dict], task: dict) -> set[str]:
    """Date rule: only runs on issues dated strictly before the task (and never the task itself)."""
    return {r["issue"] for r in runs if r["date"] < task["date"] and r["issue"] != task["id"]}


# ---------------------------------------------------------------- retrieval (no model calls)

def hits(pack: dict, t: dict) -> dict:
    src = [f for f, _ in pack["source"]]
    tst = [f for f, _ in pack["test"]]
    s = int(set(t["gold_src"]) <= set(src))
    te = int(bool(set(t["gold_tests"]) & set(tst)))
    return {"src": s, "test": te, "both": int(s and te)}


def _discount(files: dict, runs: list[dict], allowed: set[str], N: int) -> None:
    """The same hot-file discount the graph uses, ln(1 + N / runs that opened the file)."""
    df: dict[str, int] = defaultdict(int)
    for r in runs:
        if r["issue"] in allowed:
            for f in r["reads"]:
                df[f] += 1
    for f, d in files.items():
        d["score"] *= math.log(1 + N / max(df[f], 1))


def dictionary_pack(runs: list[dict], task: dict, allowed: set[str]) -> dict:
    """Plain store: a word -> file table of what earlier runs opened (1) and concluded (+2),
    tf-idf weighted, same entities as the graph; tests and docs ranked from the same table."""
    N = max(len(allowed), 1)
    df: dict[str, int] = defaultdict(int)
    tf: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for r in runs:
        if r["issue"] not in allowed:
            continue
        for t in set(r.get("terms") or HO.run_terms(r["text"])):
            df[t] += 1
            for f in r["reads"]:
                tf[t][f] += 1
            for f in r["concluded"]:
                tf[t][f] += 2
    files: dict[str, dict] = {}
    for t in HO.run_terms(task["text"]):
        if t in tf:
            tot = sum(tf[t].values())
            for f, c in tf[t].items():
                d = files.setdefault(f, {"score": 0.0, "runs": set(), "concluded": set(), "lines": set()})
                d["score"] += math.log(1 + N / df[t]) * c / tot

    _discount(files, runs, allowed, N)

    def top(kind, k):
        xs = [(f, d) for f, d in files.items() if HO.kind_of(f) == kind]
        return sorted(xs, key=lambda fd: (-fd[1]["score"], fd[0]))[:k]
    return {"source": top("source", 5), "test": top("test", 3), "doc": top("doc", 2), "runs": [], "n_runs": 0}


def table_anchor_pack(runs: list[dict], task: dict, allowed: set[str], anchor_w: float = 2.0) -> dict:
    """Stronger plain store: the word -> file table plus an anchor-file -> file table (files opened
    in the same runs as the anchor), both tf-idf, added. No run nodes, no traversal through the
    chosen sources."""
    N = max(len(allowed), 1)
    terms, anchors = task_sources(task)
    tabs = []
    for keys_of, keys in ((lambda r: set(r.get("terms") or HO.run_terms(r["text"])), terms),
                          (lambda r: set(r["reads"]), anchors)):
        df: dict[str, int] = defaultdict(int)
        tf: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        want = set(keys)
        for r in runs:
            if r["issue"] not in allowed:
                continue
            for t in keys_of(r) & want:
                df[t] += 1
                for f in r["reads"]:
                    tf[t][f] += 1
                for f in r["concluded"]:
                    tf[t][f] += 2
        tabs.append((df, tf, keys))
    files: dict[str, dict] = {}
    for i, (df, tf, keys) in enumerate(tabs):
        for t in keys:
            if t in tf:
                tot = sum(tf[t].values())
                for f, c in tf[t].items():
                    d = files.setdefault(f, {"score": 0.0, "runs": set(), "concluded": set(), "lines": set()})
                    d["score"] += (anchor_w if i else 1.0) * math.log(1 + N / df[t]) * c / tot

    _discount(files, runs, allowed, N)

    def top(kind, k):
        xs = [(f, d) for f, d in files.items() if HO.kind_of(f) == kind]
        return sorted(xs, key=lambda fd: (-fd[1]["score"], fd[0]))[:k]
    return {"source": top("source", 5), "test": top("test", 3), "doc": top("doc", 2), "runs": [], "n_runs": 0}


def boot(xs: list[float], n: int = 2000, seed: int = 0) -> tuple[float, float]:
    import random
    rnd = random.Random(seed)
    if not xs:
        return (0.0, 0.0)
    ms = sorted(sum(rnd.choice(xs) for _ in xs) / len(xs) for _ in range(n))
    return ms[int(0.025 * n)], ms[int(0.975 * n)]


def tune() -> str:
    """Dev-set grid (memory issues as targets, leave-future-out). Prints the table; the
    chosen setting is written into FINAL by hand and recorded in the pre-registration."""
    runs = prior_runs(include_old=False)
    g = HO.MemGraph(runs)
    D = dev_set()
    grid = []
    for top_runs in (10, 20, 40):
        for anchor_w in (1.0, 2.0, 4.0, 8.0):
            for hot_q in (0.0, 1.0, 2.0):
                for mode in ("direct", "via", "both"):
                    grid.append(HO.Params(top_runs=top_runs, anchor_w=anchor_w, hot_q=hot_q, test_mode=mode))
    out = [f"Dev set: {len(D)} memory issues dated {DEV_FROM}..{MEMORY_TO}, runs before each only; {len(runs)} memory runs."]
    res = []
    for P in grid:
        hs = [hits(build_pack(g, t, earlier(runs, t), P), t) for t in D]
        m = {k: sum(h[k] for h in hs) / len(hs) for k in ("src", "test", "both")}
        res.append((m["both"], m["src"], m["test"], P))
    for name, fn in (("word->file table", dictionary_pack), ("word+anchor->file table", table_anchor_pack)):
        dic = [hits(fn(runs, t, earlier(runs, t)), t) for t in D]
        out.append(f"{name}: src %.3f test %.3f both %.3f" % tuple(sum(h[k] for h in dic) / len(dic) for k in ("src", "test", "both")))
    for both, src, test, P in sorted(res, key=lambda x: (-x[0], -x[1])):
        out.append(f"both {both:.3f} src {src:.3f} test {test:.3f}  top_runs={P.top_runs} anchor_w={P.anchor_w} "
                   f"hot_q={P.hot_q} test_mode={P.test_mode}")
    txt = "\n".join(out)
    (ROOT / "results" / "handoff_tune_dev.txt").write_text(txt + "\n")
    return txt


def retrieval(db: Hydra | None) -> str:
    runs = prior_runs()
    mem = HO.MemGraph(runs)
    hg = HO.HydraGraph(db) if db is not None else None
    P_ = pool(runs)
    rows = []
    agree = total = 0
    for t in P_:
        ok = earlier(runs, t)
        ref = build_pack(mem, t, ok, FINAL)
        full = ref
        if hg is not None:
            got = build_pack(hg, t, ok, FINAL)
            total += 1
            same = [f for f, _ in got["source"]] == [f for f, _ in ref["source"]] and \
                [f for f, _ in got["test"]] == [f for f, _ in ref["test"]]
            agree += same
            full = got
        txt = HO.render(full)
        seen = {f for r in runs if r["issue"] in ok for f in r["reads"]}
        r = {"id": t["id"], "date": t["date"], "n_prior": len(ok), "tokens": tokens(txt),
             "covered": int(all(f in seen for f in t["gold_src"])),
             "graph": hits(full, t),
             "terms_only": hits(build_pack(mem, t, ok, HO.Params(**{**FINAL.__dict__, "use_anchors": False})), t),
             "anchors_only": hits(build_pack(mem, t, ok, HO.Params(**{**FINAL.__dict__, "use_terms": False})), t),
             "no_test_hop": hits(build_pack(mem, t, ok, HO.Params(**{**FINAL.__dict__, "via_sources": False})), t),
             "no_hot_discount": hits(build_pack(mem, t, ok, HO.Params(**{**FINAL.__dict__, "hot_q": 0.0})), t),
             "dictionary": hits(dictionary_pack(runs, t, ok), t),
             "table_anchor": hits(table_anchor_pack(runs, t, ok), t),
             "direct_tests": hits(build_pack(mem, t, ok, HO.Params(**{**FINAL.__dict__, "test_mode": "direct"})), t)}
        for n in CURVE:   # learning curve: only the first n recorded runs (oldest issues first)
            sub = {x["issue"] for x in runs[:n]} & ok
            r[f"first{n}"] = hits(build_pack(mem, t, sub, FINAL), t) if sub else {"src": 0, "test": 0, "both": 0}
        rows.append(r)
    (RUNS / "retrieval.jsonl").parent.mkdir(parents=True, exist_ok=True)
    with open(ROOT / "results" / "handoff_retrieval.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    out = []
    w = out.append
    w(f"Handoff graph, retrieval without model calls. Recorded runs: {len(runs)} "
      f"({sum(r['src'] == 'refuseless' for r in runs)} memory runs {MEMORY_FROM}..{MEMORY_TO}, "
      f"{sum(r['src'] == 'deepseek-api' for r in runs)} Level 2 runs).")
    w(f"Targets: {len(P_)} SWE-bench Django issues from {TARGET_FROM} with no recorded run whose fix extends an existing "
      "test file; each uses only runs on issues dated before it.")
    w("NOTE: an earlier version of this table was looked at on these same targets before pre-registration "
      "(results/handoff_retrieval_v0.txt); the pack design was then fixed on the dev set only.")
    if hg is not None:
        w(f"HydraDB pack equals the in-memory reference on {agree}/{total} targets.")
    w(f"Pack size: median {sorted(r['tokens'] for r in rows)[len(rows) // 2]} tokens (characters / 4).\n")
    for name, sel in (("all targets", rows), ("targets whose fix files an earlier run opened", [r for r in rows if r["covered"]])):
        w(f"{name} (n={len(sel)}): share of targets where the pack holds ...")
        w(f"  {'':40} {'every fix file (top 5)':>24} {'a real test file (top 3)':>26} {'both':>20}")
        labels = [("graph", "Graph (final)"), ("terms_only", "  - without code anchors"),
                  ("anchors_only", "  - without task entities"), ("no_test_hop", "  - tests ranked directly (no hop 3)"),
                  ("no_hot_discount", "  - without hot-file discount"), ("direct_tests", "  - tests ranked directly only"),
                  ("dictionary", "Plain word -> file table"), ("table_anchor", "Plain word+anchor -> file table")]
        labels += [(f"first{n}", f"Graph, first {n} recorded runs") for n in CURVE]
        for cond, label in labels:
            cells = []
            for m in ("src", "test", "both"):
                xs = [r[cond][m] for r in sel]
                lo, hi = boot(xs)
                cells.append(f"{sum(xs) / max(len(xs), 1):.2f} [{lo:.2f}, {hi:.2f}]")
            w(f"  {label:40} {cells[0]:>24} {cells[1]:>26} {cells[2]:>20}")
        for a, b, m in (("graph", "dictionary", "both"), ("graph", "table_anchor", "both"), ("graph", "table_anchor", "test"),
                        ("graph", "table_anchor", "src"), ("graph", "no_test_hop", "test")):
            d = [r[a][m] - r[b][m] for r in sel]
            lo, hi = boot(d)
            w(f"  paired, {m}: {a} - {b} = {sum(d) / max(len(d), 1):+.3f} [{lo:+.3f}, {hi:+.3f}]")
        w("")
    txt = "\n".join(out)
    (ROOT / "results" / "handoff_retrieval.txt").write_text(txt + "\n")
    return txt


CURVE = (0, 25, 50, 100, 200, 300)


# ---------------------------------------------------------------- handoff-file baseline

NOTE_PROMPT = """Below is the full transcript of an agent session that investigated an issue in the Django repository. Write the handoff note that agent should leave for the next agent working in this repository, as Markdown, under 300 words: what the issue was, which files and line ranges mattered and why, which test files and docs relate to that code, what was ruled out, and the conclusion. Be specific about paths and line numbers. Output only the note.

ISSUE:
{issue}

TRANSCRIPT:
{transcript}"""


def transcript(path: Path, cap: int = 60000) -> str:
    parts = []
    for line in path.read_text().splitlines():
        try:
            e = json.loads(line)
        except ValueError:
            continue
        p = e.get("part", {})
        if e["type"] == "text":
            parts.append("AGENT: " + p.get("text", ""))
        elif e["type"] == "tool_use":
            s = p.get("state", {})
            parts.append("TOOL " + str(p.get("tool")) + " " + json.dumps(s.get("input", {}))[:400]
                         + "\nRESULT: " + str(s.get("output", ""))[:1500])
    return "\n".join(parts)[:cap]


NOTE_MODEL = "deepseek-v4.1-flash-fast"


def write_notes(runs: list[dict], parallel: int = 8) -> None:
    """One model call per recorded run (the cost a handoff file has and the graph does not)."""
    NOTES.mkdir(parents=True, exist_ok=True)
    log = NOTES / "usage.jsonl"

    def one(r):
        dst = NOTES / f"{r['issue']}.md"
        if dst.exists():
            return
        msgs = [{"role": "user", "content": NOTE_PROMPT.format(issue=r["text"][:4000], transcript=transcript(r["path"]))}]
        for attempt in range(3):
            try:
                d = level2.chat(msgs, model=NOTE_MODEL, max_tokens=900)
                break
            except Exception as e:  # noqa: BLE001
                print(r["issue"], "retry", e, flush=True)
                time.sleep(10 * (attempt + 1))
        else:
            return
        dst.write_text(d["choices"][0]["message"]["content"].strip() + "\n")
        with level2._lock, open(log, "a") as f:
            f.write(json.dumps({"issue": r["issue"], "model": NOTE_MODEL, **{k: d["usage"].get(k) for k in
                                ("prompt_tokens", "completion_tokens", "total_tokens")}}) + "\n")
        print(r["issue"], d["usage"].get("prompt_tokens"), d["usage"].get("completion_tokens"), flush=True)

    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(parallel) as ex:
        list(ex.map(one, runs))


# ---------------------------------------------------------------- live runs

def parse_answer(path: Path) -> dict:
    text = []
    for line in path.read_text().splitlines():
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if e["type"] == "text":
            text.append(e.get("part", {}).get("text", ""))
    final = "\n".join(text)

    def grab(tag):
        m = re.findall(tag + r":\s*(.+)", final)
        if not m:
            return None
        return [f.strip().strip("`").lstrip("./") for f in re.split(r"[,\s]+", m[-1]) if "/" in f]
    return {"files": (grab("FILES") or [])[:5], "tests": (grab("TESTS") or [])[:3],
            "answered": grab("FILES") is not None and grab("TESTS") is not None}


def run_one(task: dict, cond: str, runs: list[dict], db: Hydra | None, rep: int = 0, out_dir: Path | None = None,
            results: Path | None = None, pack_override: str | None = None, note_ids: list[str] | None = None,
            tag: str = "A") -> dict:
    """One live run. `runs` are the recorded runs; only those on issues dated before
    the task are used (date rule). Experiment B passes note_ids / pack_override."""
    results = results or RUNS / "results.jsonl"
    out_dir = out_dir or RUNS / cond
    out_dir.mkdir(parents=True, exist_ok=True)
    ev_path = out_dir / f"{task['id']}.r{rep}.jsonl"
    wt = level2.WORK / f"ho-{tag}-{cond}-{task['id']}-r{rep}"
    subprocess.run(["rm", "-rf", str(wt)])
    subprocess.run([str(ROOT / "scripts/snapshot.sh"), str(REPO), task["base_commit"], str(wt)], check=True)
    ok = earlier(runs, task)
    extra, pack_text, n_notes, note_tokens = EXTRA[cond], "", 0, 0
    if cond == "notes":
        (wt / "HANDOFF").mkdir()
        ids = note_ids if note_ids is not None else sorted(ok)
        for iid in ids:
            src = NOTES / f"{iid}.md"
            if src.exists():
                txt = src.read_text()
                (wt / "HANDOFF" / f"{iid}.md").write_text(txt)
                n_notes += 1
                note_tokens += tokens(txt)
        extra = extra.format(n=n_notes)
    elif cond == "graph":
        pack_text = pack_override if pack_override is not None else graph_pack_text(HO.HydraGraph(db), task, ok, FINAL)
        extra = extra.format(pack=pack_text) if pack_text else ""
    prompt = PROMPT.format(extra=extra, issue=task["text"])
    cfg_path = level2.oc_config("none")
    attempts = 0
    while True:
        attempts += 1
        with level2._start_lock:
            time.sleep(2.5)
        t0 = time.time()
        data_dir = level2.WORK / f"ocdata-ho-{cond}-{task['id']}-r{rep}"
        subprocess.run(["rm", "-rf", str(data_dir)])
        with open(ev_path, "w") as fo, open(ev_path.with_suffix(".err"), "w") as fe:
            proc = subprocess.Popen([str(ROOT / "scripts/sandbox_opencode.sh"), str(wt), str(cfg_path), str(data_dir),
                                     str(level2.NET), "--", "run", "--print-logs", "--log-level", "WARN", "--title", "bench",
                                     "--format", "json", "--agent", "locate", "-m", level2.MODEL, "--dir", "/work/repo", prompt],
                                    stdin=subprocess.DEVNULL, stdout=fo, stderr=fe,
                                    env=dict(os.environ, **({"OC_AUTH": level2.AUTH} if level2.AUTH else {})))
            code = None
            while code is None:
                try:
                    code = proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    err = ev_path.with_suffix(".err").read_text(errors="replace")
                    if level2.LIMIT_RE.search(err) or time.time() - t0 > level2.TIMEOUT:
                        code = "rate_limit" if level2.LIMIT_RE.search(err) else "timeout"
                        proc.terminate()
                        try:
                            proc.wait(timeout=10)
                        except subprocess.TimeoutExpired:
                            proc.kill()
        subprocess.run(["rm", "-rf", str(data_dir)])
        wall = time.time() - t0
        res = level2.parse_events(ev_path)
        if code == "rate_limit" and attempts < 3:
            time.sleep(60 * attempts)
            continue
        if code not in (0, "rate_limit") and res["steps"] == 0 and attempts < 3:
            continue
        break
    err_text = ev_path.with_suffix(".err").read_text()[-4000:]
    rate_limited = code == "rate_limit" or bool(level2.LIMIT_RE.search(err_text + " ".join(res["errors"])))
    subprocess.run(["rm", "-rf", str(wt)])
    ans = parse_answer(ev_path)
    src_ok = int(set(task["gold_src"]) <= set(ans["files"]))
    test_ok = int(bool(set(task["gold_tests"]) & set(ans["tests"])))
    row = {"id": task["id"], "date": task["date"], "condition": cond, "rep": rep, "model": level2.MODEL, "exit": code,
           "attempts": attempts, "wall_s": round(wall, 1), "rate_limited": rate_limited,
           "gold_src": task["gold_src"], "gold_tests": task["gold_tests"], "n_prior": len(ok), "n_notes": n_notes,
           "pack": pack_text, "pack_tokens": tokens(pack_text), "outside_access": level2.outside_access(ev_path),
           "tokens": res["tokens"], "total_input": res["total_input"], "tool_calls": res["tool_calls"], "steps": res["steps"],
           "errors": res["errors"], **ans, "src_ok": src_ok, "test_ok": test_ok, "success": int(src_ok and test_ok)}
    row.update(experiment=tag, note_tokens_on_disk=note_tokens)
    with level2._lock, open(results, "a") as f:
        f.write(json.dumps(row) + "\n")
    return row


def launch(jobs: list, parallel: int) -> None:
    """jobs: (label, thunk). Runs them with the sandbox network relays up."""
    level2.RUNS = RUNS
    net = level2.start_net(False)
    level2.AUTH = level2.oc_auth()

    def job(lj):
        label, fn = lj
        try:
            row = fn()
        except Exception as e:  # noqa: BLE001
            print(f"{label}: ERROR {e!r}", flush=True)
            return
        print(f"{label}: success={row['success']} src={row['src_ok']} test={row['test_ok']} in={row['total_input']} "
              f"steps={row['steps']} {row['wall_s']}s exit={row['exit']} rl={row['rate_limited']} "
              f"leak={len(row['outside_access'])}", flush=True)

    from concurrent.futures import ThreadPoolExecutor
    try:
        with ThreadPoolExecutor(parallel) as ex:
            list(ex.map(job, jobs))
    finally:
        for p in net:
            p.terminate()


def done_set(path: Path) -> set:
    out = set()
    if path.exists():
        for line in open(path):
            q = json.loads(line)
            if not q["rate_limited"] and q["steps"] > 0:
                out.add((q["id"], q["condition"], q.get("rep", 0)))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("record")
    sub.add_parser("targets")
    sub.add_parser("tune")
    r0 = sub.add_parser("retrieval")
    r0.add_argument("--no-db", action="store_true")
    n0 = sub.add_parser("notes")
    n0.add_argument("--parallel", type=int, default=8)
    m = sub.add_parser("memory")
    m.add_argument("--limit", type=int, default=None)
    m.add_argument("--only", default=None)
    m.add_argument("--parallel", type=int, default=8)
    r = sub.add_parser("run")
    r.add_argument("--tasks", type=int, default=12)
    r.add_argument("--skip", type=int, default=0)
    r.add_argument("--only", default=None)
    r.add_argument("--conditions", default="cold,notes,graph")
    r.add_argument("--reps", type=int, default=1)
    r.add_argument("--parallel", type=int, default=6)
    b = sub.add_parser("same")
    b.add_argument("--tasks", type=int, default=40)
    b.add_argument("--conditions", default="cold,notes,graph")
    b.add_argument("--parallel", type=int, default=12)
    sub.add_parser("pack").add_argument("id")
    args = ap.parse_args()
    db = Hydra(tenant=SCOPE[0], subtenant=SCOPE[1])
    RUNS.mkdir(parents=True, exist_ok=True)
    if args.cmd == "memory":
        M = memory_tasks()
        M = [t for t in M if t["id"] == args.only] if args.only else M[:args.limit]
        res = PRIOR / "results.jsonl"
        done = done_set(res)
        jobs = [(f"mem {t['id']}", (lambda t=t: run_one(t, "cold", [], None, out_dir=PRIOR, results=res, tag="mem")))
                for t in M if (t["id"], "cold", 0) not in done]
        print(len(M), "memory issues;", len(jobs), "to run", flush=True)
        launch(jobs, args.parallel)
        return
    runs = prior_runs()
    if args.cmd == "record":
        t0 = time.time()
        g = HO.HydraGraph(db)
        g.reset()
        print(g.record(runs), f"{time.time() - t0:.1f}s")
    elif args.cmd == "tune":
        print(tune())
    elif args.cmd == "targets":
        T = pool(runs)
        print(len(T), "targets")
        for t in T:
            print(t["date"][:10], t["id"], t["gold_src"], t["gold_tests"])
    elif args.cmd == "retrieval":
        print(retrieval(None if args.no_db else db))
    elif args.cmd == "notes":
        write_notes(runs, args.parallel)
    elif args.cmd == "pack":
        t = next(t for t in pool(runs) + memory_tasks() if t["id"] == args.id)
        print(graph_pack_text(HO.HydraGraph(db), t, earlier(runs, t), FINAL))
        print("gold:", t["gold_src"], t["gold_tests"])
    elif args.cmd == "same":
        # Experiment B: a second agent on the SAME issue as a recorded memory run, with nothing,
        # with that run's own handoff note, or with a pack built from that run's own record only.
        T = same_tasks(runs, args.tasks)
        res = RUNS / "same" / "results.jsonl"
        done = done_set(res)
        hg = HO.HydraGraph(db)
        jobs = []
        for t in T:
            for c in args.conditions.split(","):
                if (t["id"], c, 1) in done:
                    continue
                kw = {}
                if c == "notes":
                    kw["note_ids"] = [t["id"]]
                if c == "graph":
                    kw["pack_override"] = graph_pack_text(hg, t, {t["id"]}, FINAL)
                jobs.append((f"same {t['id']} {c}", (lambda t=t, c=c, kw=kw: run_one(
                    t, c, runs, db, rep=1, out_dir=RUNS / "same" / c, results=res, tag="B", **kw))))
        launch(jobs, args.parallel)
    elif args.cmd == "run":
        T = pool(runs)
        T = [t for t in T if t["id"] == args.only] if args.only else T[args.skip:args.skip + args.tasks]
        done = done_set(RUNS / "results.jsonl")
        jobs = [(f"{t['id']} {c} r{k}", (lambda t=t, c=c, k=k: run_one(t, c, runs, db, rep=k)))
                for t in T for k in range(args.reps) for c in args.conditions.split(",") if (t["id"], c, k) not in done]
        launch(jobs, args.parallel)


if __name__ == "__main__":
    main()
