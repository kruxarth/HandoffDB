"""HandoffDB handoff graph: what earlier agent runs opened, found and concluded,
recorded as structure in HydraDB from their tool calls (no model call), and
read back for the next agent as a small pack from a few traversals.

Schema (one scope per team/repo: tenant = team, subtenant = repo):

  (:HTerm {key})  -[:ABOUT]->          (:HRun {key, date, title})   entity of the run's task text
  (:HFile {key})  -[:READ_BY]->        (:HRun)                      the run opened this file
  (:HRun)         -[:READ {lines, n}]-> (:HFile)                    what it opened, which line ranges
  (:HRun)         -[:CONCLUDED]->      (:HFile)                     files in its final answer

Read side (all ``algo.MSpaths``, length 1, so nothing is truncated):
  hop 1  task entities -> runs (ABOUT) and code anchors -> runs (READ_BY);
         runs ranked by how specific the link is (rare entities, rarely opened anchors)
  hop 2  top runs -> files they opened / concluded; files ranked by the runs'
         relevance, discounted by how many runs open them anyway
  hop 3  top source files -> runs that opened them -> the test files and docs those
         same runs opened (the multi-hop step a word -> file table cannot do)

The same algorithm runs on an in-memory copy (``MemGraph``) as the reference
the HydraDB answer is checked against.
"""
from __future__ import annotations

import json
import math
import re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from .core import is_source
from .db import Hydra, cypher_strings
from .entities import extract, node_id

MAX_TERMS = 60
FILE_RE = re.compile(r"(?:/work/repo/|\./|(?<![\w/]))((?:django|tests|docs)/[\w/.-]+\.(?:py|txt|html|json))")
SED_RE = re.compile(r"sed\s+-n\s+['\"]?(\d+),(\d+)p['\"]?\s+(\S+)")


def run_terms(text: str) -> list[str]:
    ents = extract(text)
    return [k for k, _ in sorted(ents.items(), key=lambda kv: (-kv[1], kv[0]))][:MAX_TERMS]


def kind_of(f: str) -> str:
    if f.startswith("tests/") or "/tests/" in f:
        return "test"
    if f.startswith("docs/"):
        return "doc"
    return "source" if is_source(f) else "other"


def merge_spans(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    out: list[list[int]] = []
    for a, b in sorted(spans):
        if out and a <= out[-1][1] + 15:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return [(a, b) for a, b in out]


# ---------------------------------------------------------------- recorders (no model call)

def _final_files(final: str) -> list[str]:
    m = re.findall(r"FILES:\s*(.+)", final)
    if not m:
        return []
    return [f.strip().strip("`").lstrip("./") for f in re.split(r"[,\s]+", m[-1]) if "/" in f][:5]


def _touch(reads, f, span=None):
    reads[f]["n"] += 1
    if span:
        reads[f]["spans"].append(span)


def parse_opencode(path: Path) -> dict:
    """An OpenCode ``--format json`` event log -> what the run opened (file -> line
    spans, times) and concluded. Uses only tool-call inputs and the final answer."""
    reads: dict[str, dict] = defaultdict(lambda: {"n": 0, "spans": []})
    steps, text = 0, []
    for line in path.read_text().splitlines():
        try:
            e = json.loads(line)
        except ValueError:
            continue
        p = e.get("part", {})
        if e["type"] == "step_finish":
            steps += 1
        elif e["type"] == "text":
            text.append(p.get("text", ""))
        elif e["type"] == "tool_use":
            inp = p.get("state", {}).get("input", {}) or {}
            _from_tool(reads, p.get("tool"), inp)
    return _finish(reads, "\n".join(text), steps)


def _from_tool(reads, tool, inp) -> None:
    s = json.dumps(inp)
    seen: dict[str, tuple | None] = {}
    fp = inp.get("filePath") or inp.get("file_path") if isinstance(inp, dict) else None
    if tool and tool.lower() == "read" and fp:
        m = FILE_RE.search(fp)
        if m:
            span = None
            if inp.get("limit"):
                a = int(inp.get("offset") or 1)
                span = (a, a + int(inp["limit"]) - 1)
            seen[m.group(1)] = span
    cmd = inp.get("command", "") if isinstance(inp, dict) else ""
    for a, b, f in SED_RE.findall(cmd or ""):
        m = FILE_RE.search(f)
        if m:
            seen[m.group(1)] = (int(a), int(b))
    for f in FILE_RE.findall(s):
        seen.setdefault(f, None)
    for f, span in seen.items():
        _touch(reads, f, span)


def _finish(reads, final: str, steps: int) -> dict:
    return {"reads": {f: {"n": v["n"], "spans": merge_spans(v["spans"])} for f, v in reads.items()},
            "concluded": _final_files(final), "steps": max(steps, 1), "final": final[-1500:]}


def parse_claude_transcript(path: Path, repo_root: str = "") -> dict:
    """A Claude Code session transcript (JSONL) -> the same record. Reads Read/Grep/Bash
    tool inputs; files are made repo-relative by stripping ``repo_root``. The
    conclusion is the files the session edited (Edit/Write/MultiEdit) or, failing
    that, a FILES: line in its last message."""
    reads: dict[str, dict] = defaultdict(lambda: {"n": 0, "spans": []})
    edited, steps, last = [], 0, ""
    root = repo_root.rstrip("/") + "/" if repo_root else ""
    for line in path.read_text().splitlines():
        try:
            e = json.loads(line)
        except ValueError:
            continue
        msg = e.get("message") or {}
        if e.get("type") != "assistant" or not isinstance(msg.get("content"), list):
            continue
        steps += 1
        for c in msg["content"]:
            if c.get("type") == "text":
                last = c.get("text", "")
            if c.get("type") != "tool_use":
                continue
            inp = dict(c.get("input") or {})
            for k in ("file_path", "path", "command", "pattern"):
                if isinstance(inp.get(k), str) and root:
                    inp[k] = inp[k].replace(root, "")
            f = inp.get("file_path")
            if c.get("name") in ("Edit", "Write", "MultiEdit", "NotebookEdit") and f:
                if f not in edited:
                    edited.append(f)
                _touch(reads, f)
                continue
            if c.get("name") == "Read" and f:
                span = None
                if inp.get("limit"):
                    a = int(inp.get("offset") or 1)
                    span = (a, a + int(inp["limit"]) - 1)
                _touch(reads, f, span)
                continue
            _from_tool(reads, c.get("name"), inp)
    out = _finish(reads, last, steps)
    if edited:
        out["concluded"] = edited[:5]
    return out


# ---------------------------------------------------------------- graph backends

class HydraGraph:
    """The handoff graph in one HydraDB scope."""

    def __init__(self, db: Hydra) -> None:
        self.db = db

    # write side
    def reset(self) -> None:
        for lab in ("HTerm", "HRun", "HFile", "HInfo"):
            while True:
                ids = [r[0] for r in self.db.query(f"MATCH (n:{lab}) RETURN n.id AS id LIMIT 1000")]
                if not ids:
                    break
                self.db.batch("UNWIND $rows AS row MATCH (n {id: row.id}) DETACH DELETE n", [{"id": i} for i in ids])

    def forget(self, key: str) -> None:
        """Delete one run (and its edges); its terms and files stay."""
        self.db.query("MATCH (n {id: $id}) DETACH DELETE n", {"id": node_id("HRun", key)})
        self.db.query("MATCH (n {id: $id}) DETACH DELETE n", {"id": node_id("HInfo", key)})

    def count_runs(self) -> int:
        return int(self.db.query("MATCH (n:HRun) RETURN count(n)")[0][0])

    def record(self, runs: list[dict], threads: int = 16) -> dict:
        """runs: {key, date, title, text, reads, concluded}. Nodes and plain edges are
        batched; READ edges carry line ranges, so they are one statement each."""
        terms, files, about, read_by, concl, reads = {}, {}, [], [], [], []
        for r in runs:
            rid = node_id("HRun", r["key"])
            for t in r.get("terms") or run_terms(r["text"]):
                terms[t] = node_id("HTerm", t)
                about.append({"s": terms[t], "d": rid})
            for f, v in r["reads"].items():
                files[f] = node_id("HFile", f)
                read_by.append({"s": files[f], "d": rid})
                reads.append({"a": rid, "b": files[f], "lines": ";".join(f"{a}-{b}" for a, b in v["spans"][:6]),
                              "n": v["n"]})
            for f in r["concluded"]:
                files[f] = node_id("HFile", f)
                concl.append({"s": rid, "d": files[f]})
        db = self.db
        db.batch("UNWIND $rows AS row MERGE (n {id: row.id}) SET n:HTerm, n.key = row.key",
                 [{"id": i, "key": k} for k, i in terms.items()])
        db.batch("UNWIND $rows AS row MERGE (n {id: row.id}) SET n:HFile, n.key = row.key",
                 [{"id": i, "key": k} for k, i in files.items()])
        # HRun carries only its key, so every traversal through it returns little; date and title
        # live on a separate HInfo node, read only for the few runs shown in a pack
        db.batch("UNWIND $rows AS row MERGE (n {id: row.id}) SET n:HRun, n.key = row.key",
                 [{"id": node_id("HRun", r["key"]), "key": r["key"]} for r in runs])
        db.batch("UNWIND $rows AS row MERGE (n {id: row.id}) SET n:HInfo, n.key = row.key, n.date = row.date, n.title = row.title",
                 [{"id": node_id("HInfo", r["key"]), "key": r["key"], "date": r.get("date", ""),
                   "title": (r.get("title") or (r["text"].strip().splitlines()[0] if r["text"].strip() else ""))[:160]}
                  for r in runs])
        for rel, rows in (("ABOUT", about), ("READ_BY", read_by), ("CONCLUDED", concl)):
            db.batch(f"UNWIND $rows AS row CREATE (a {{id: row.s}})-[:{rel}]->(b {{id: row.d}})", rows)

        def one(e):
            db.query("CREATE (a {id: $a})-[:READ {lines: $lines, n: $n}]->(b {id: $b})", e)
        with ThreadPoolExecutor(threads) as ex:
            list(ex.map(one, reads))
        return {"runs": len(runs), "terms": len(terms), "files": len(files),
                "edges": len(about) + len(read_by) + len(concl) + len(reads)}

    # read side: three primitives, each one length-1 MSpaths call
    def _hop(self, label: str, keys: list[str], rels: list[str]) -> list[tuple]:
        if not keys:
            return []
        q = ("CALL algo.MSpaths({" + f"sourceLabel: '{label}', sourceProperty: 'key', sourceValues: {cypher_strings(keys)}, "
             f"relTypes: {rels!r}, relDirection: 'outgoing', maxLen: 1, pathCount: 100000, pairwise: false"
             "}) YIELD path RETURN path")
        out = []
        for (path,) in self.db.query(q, page_size=4096):
            if len(path["rels"]) != 1:
                continue
            n, r = path["nodes"], path["rels"][0]
            out.append((n[0]["props"].get("key"), r["type"], n[1]["props"].get("key"), r["props"].get("lines", "") or "",
                        n[1]["props"]))
        return out

    def term_runs(self, terms):
        return [(a, b) for a, _, b, _, _ in self._hop("HTerm", terms, ["ABOUT"])]

    def file_runs(self, files):
        return [(a, b) for a, _, b, _, _ in self._hop("HFile", files, ["READ_BY"])]

    def run_files(self, runs):
        return [(a, rel, b, lines) for a, rel, b, lines, _ in self._hop("HRun", runs, ["READ", "CONCLUDED"])]

    def run_info(self, runs):
        q = "MATCH (n:HInfo) WHERE n.key IN $ks RETURN n.key, n.date, n.title"
        return {k: {"date": d, "title": t} for k, d, t in self.db.query(q, {"ks": list(runs)})} if runs else {}


class MemGraph:
    """The same graph in memory (reference implementation and dev-set tuning)."""

    def __init__(self, runs: list[dict]) -> None:
        self.runs = {r["key"]: r for r in runs}
        self.by_term = defaultdict(set)
        self.by_file = defaultdict(set)
        for r in runs:
            r.setdefault("terms", run_terms(r["text"]))
            for t in r["terms"]:
                self.by_term[t].add(r["key"])
            for f in r["reads"]:
                self.by_file[f].add(r["key"])

    def term_runs(self, terms):
        return [(t, k) for t in dict.fromkeys(terms) for k in self.by_term.get(t, ())]

    def file_runs(self, files):
        return [(f, k) for f in dict.fromkeys(files) for k in self.by_file.get(f, ())]

    def run_files(self, runs):
        out = []
        for k in dict.fromkeys(runs):
            r = self.runs[k]
            for f, v in r["reads"].items():
                out.append((k, "READ", f, ";".join(f"{a}-{b}" for a, b in v["spans"][:6])))
            for f in r["concluded"]:
                out.append((k, "CONCLUDED", f, ""))
        return out

    def run_info(self, runs):
        return {k: {"date": self.runs[k].get("date", ""), "title": self.runs[k]["text"].strip().splitlines()[0][:160]}
                for k in runs if k in self.runs}


# ---------------------------------------------------------------- pack

@dataclass
class Params:
    top_runs: int = 20        # runs kept after hop 1
    anchor_w: float = 2.0     # weight of a code-anchor link relative to an entity link
    hot_q: float = 1.0        # exponent of the file-specificity discount ln(1 + N/df)
    concl_c: float = 1.0      # extra weight when the run concluded its fix was in the file
    test_via: int = 3         # top source files the test hop starts from
    k_src: int = 5
    k_test: int = 3
    k_doc: int = 2
    via_sources: bool = True  # False forces test_mode "direct" (ablation)
    test_mode: str = "both"   # direct | via | both (see build_pack)
    via_base: float = 0.1
    use_terms: bool = True
    use_anchors: bool = True


def _idf(n: int, df: int) -> float:
    return math.log(1 + n / max(df, 1))


def build_pack(g, terms: list[str], anchors: list[str], allowed: set[str] | None = None,
               P: Params | None = None, n_total: int | None = None) -> dict:
    """The pack: ranked source files, test files and docs, each with the earlier runs
    behind it and the line ranges they read. ``allowed``: runs that may be used
    (the date rule); None = all. Frequencies are counted over allowed runs only."""
    P = P or Params()
    ok = (lambda k: True) if allowed is None else (lambda k: k in allowed)
    N = n_total or (len(allowed) if allowed is not None else None)
    with ThreadPoolExecutor(2) as ex:   # the two first-hop traversals are independent
        f_tr = ex.submit(g.term_runs, terms if P.use_terms else [])
        f_ar = ex.submit(g.file_runs, anchors if P.use_anchors else [])
        tr = [(t, k) for t, k in f_tr.result() if ok(k)]
        ar = [(f, k) for f, k in f_ar.result() if ok(k)]
    if N is None:
        N = max(len({k for _, k in tr} | {k for _, k in ar}), 1) * 4
    df_t, df_a = defaultdict(int), defaultdict(int)
    for t, _ in tr:
        df_t[t] += 1
    for f, _ in ar:
        df_a[f] += 1
    rel = defaultdict(float)
    for t, k in tr:
        rel[k] += _idf(N, df_t[t])
    for f, k in ar:
        rel[k] += P.anchor_w * _idf(N, df_a[f])
    top = sorted(rel, key=lambda k: (-round(rel[k], 9), k))[:P.top_runs]
    empty = {"source": [], "test": [], "doc": [], "runs": [], "n_runs": 0, "calls": 2}
    if not top:
        return empty
    rf = g.run_files(top)
    cand = defaultdict(lambda: {"score": 0.0, "runs": set(), "concluded": set(), "lines": set()})
    for k, r, f, lines in rf:
        d = cand[f]
        if r == "CONCLUDED":
            d["concluded"].add(k)
            d["score"] += rel[k] * P.concl_c
        else:
            d["runs"].add(k)
            d["score"] += rel[k]
            d["lines"].update(x for x in lines.split(";") if x)
    srcs = [f for f in cand if kind_of(f) == "source"]
    # one traversal for how often every candidate (source, test, doc) is opened, and by which runs
    fr = [(f, k) for f, k in g.file_runs([f for f in cand if kind_of(f) in ("source", "test", "doc")]) if ok(k)]
    df_f, readers = defaultdict(int), defaultdict(set)
    for f, k in fr:
        df_f[f] += 1
        readers[f].add(k)
    for f in srcs:
        cand[f]["score"] *= _idf(N, df_f[f]) ** P.hot_q
    source = sorted(((f, cand[f]) for f in srcs), key=lambda fd: (-round(fd[1]["score"], 9), fd[0]))[:P.k_src]
    calls = 3
    # tests and docs. direct: ranked like sources, from the top runs. via (hop 3): the chosen
    # sources -> every allowed run that opened them -> the tests/docs those runs opened, each run
    # weighted by its relevance to this task (plus via_base, so runs found only through the
    # source still count). both: the two scores, each scaled to its maximum, added.
    mode = P.test_mode if P.via_sources else "direct"
    direct = {f: cand[f] for f in cand if kind_of(f) in ("test", "doc")}
    tcand = defaultdict(lambda: {"score": 0.0, "runs": set(), "concluded": set(), "lines": set()})
    if mode in ("via", "both") and source:
        base = source[:P.test_via]
        smax = max(d["score"] for _, d in base) or 1.0
        rmax = max(rel.values()) or 1.0
        via_runs = sorted({k for f, _ in base for k in readers[f]})
        rf2 = g.run_files(via_runs)
        calls += 1
        opened = defaultdict(set)
        for k, r, f, lines in rf2:
            if r == "READ" and kind_of(f) in ("test", "doc"):
                opened[k].add(f)
                tcand[f]["lines"].update(x for x in lines.split(";") if x)
        for sname, d in base:
            ws = {k: rel.get(k, 0.0) / rmax + P.via_base for k in readers[sname]}
            tot = sum(ws.values()) or 1.0
            for k, wk in ws.items():
                for f in opened.get(k, ()):
                    tcand[f]["score"] += (d["score"] / smax) * wk / tot
                    tcand[f]["runs"].add(k)
    df2 = defaultdict(int, {f: df_f[f] for f in direct})
    extra = sorted(set(tcand) - set(direct))
    if extra:
        for f, k in g.file_runs(extra):
            if ok(k):
                df2[f] += 1
        calls += 1
    pool = {}
    for src_scores, wgt in ((direct, 1.0 if mode in ("direct", "both") else 0.0),
                            (tcand, 1.0 if mode in ("via", "both") else 0.0)):
        if not wgt or not src_scores:
            continue
        sc = {f: d["score"] * _idf(N, df2[f]) ** P.hot_q for f, d in src_scores.items()}
        mx = max(sc.values()) or 1.0
        for f, d in src_scores.items():
            e = pool.setdefault(f, {"score": 0.0, "runs": set(), "concluded": set(), "lines": set()})
            e["score"] += wgt * sc[f] / mx
            e["runs"] |= d["runs"]
            e["concluded"] |= d["concluded"]
            e["lines"] |= d["lines"]

    def top_kind(kind, n):
        xs = [(f, d) for f, d in pool.items() if kind_of(f) == kind]
        return sorted(xs, key=lambda fd: (-round(fd[1]["score"], 9), fd[0]))[:n]
    used = {k for _, d in source for k in d["runs"] | d["concluded"]}
    return {"source": source, "test": top_kind("test", P.k_test), "doc": top_kind("doc", P.k_doc),
            "runs": sorted(used), "n_runs": len(used), "calls": calls}


def render(pack: dict, info: dict | None = None) -> str:
    if not pack["source"] and not pack["test"]:
        return ""

    def row(f, d):
        n = len(d["runs"] | d["concluded"])
        spans = sorted(d["lines"], key=lambda s: int(s.split("-")[0]))[:4]
        s = f"  {f}  opened by {n} earlier run{'s' if n != 1 else ''}"
        if spans:
            s += " (lines " + ", ".join(spans) + ")"
        if d["concluded"]:
            s += f"; {len(d['concluded'])} concluded their fix belonged here"
        return s
    n = pack["n_runs"]
    out = [f"Handoff from {n} earlier agent run{'s' if n != 1 else ''} on this repository that worked on issues near this code "
           "(HandoffDB). What they opened and concluded; line numbers are from their checkouts and may have shifted. "
           "Start from these; search wider only if they do not fit."]
    if pack["source"]:
        out.append("Source files:")
        out += [row(f, d) for f, d in pack["source"]]
    if pack["test"]:
        out.append("Test files those runs opened for this code:")
        out += [row(f, d) for f, d in pack["test"]]
    if pack["doc"]:
        out.append("Docs they checked:")
        out += [row(f, d) for f, d in pack["doc"]]
    if info:
        titles = [info[k]["title"] for k in pack["runs"][:3] if k in info and info[k]["title"]]
        if titles:
            out.append("Earlier issues: " + " | ".join(t[:90] for t in titles))
    return "\n".join(out)


def tokens(s: str) -> int:
    return (len(s) + 3) // 4
