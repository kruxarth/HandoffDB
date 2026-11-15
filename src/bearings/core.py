"""Bearings core: a learned context layer for coding agents, stored in HydraDB.

Graph (one scope per team/repo):

    (:Term {key, kind, df})  -[:POINTS_TO {n, miss, w}]->  (:File {path, changes})
    (:File)                  -[:CO_CHANGED {n, w}]->        (:File)       top-K per file
    (:File)                  -[:TESTED_BY {n}]->            (:TestCmd {cmd})
    (:Task {key, date, passed}) -[:MENTIONS]-> (:Term)
    (:Task) -[:CHANGED]-> (:File)   (:Task) -[:READ]-> (:File)   (:Task) -[:VERIFIED_BY]-> (:TestCmd)

Edge weights are costs (lower = stronger), so HydraDB's weighted path
procedures rank the best-supported routes first:

    POINTS_TO.w  = ln(SCALE / n) + beta * ln(1 + miss)
    CO_CHANGED.w = hop_penalty + ln((changes_src + 1) / n)

A link that led to the right file (``n``) gets cheaper; a link that was
suggested and led nowhere (``miss``) gets dearer.

Read side: one ``algo.MSpaths`` call from the task's entity nodes over
POINTS_TO (+ CO_CHANGED for the second hop). Each returned path is both the
evidence for a file and its explanation.
"""

from __future__ import annotations

import math
import re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from .db import Hydra, cypher_strings
from .entities import extract, node_id, path_candidates

SCALE = 1000.0
LN_SCALE = math.log(SCALE)


@dataclass
class Params:
    beta: float = 1.0          # miss penalty strength
    hop_penalty: float = 1.5   # extra cost of a CO_CHANGED hop
    co_top_k: int = 8          # CO_CHANGED edges kept per file
    max_terms: int = 80        # query entities used (rarest first)
    max_df_frac: float = 0.04  # ignore entities in more than this share of tasks
    paths_per_term: int = 20   # pathCount per entity in MSpaths
    hops: int = 2              # 1 = POINTS_TO only, 2 = + CO_CHANGED
    learn_misses: bool = True
    miss_top: int = 5          # suggested-but-wrong files penalised per task


def is_test(path: str) -> bool:
    return path.startswith("tests/") or "/tests/" in path or path.split("/")[-1].startswith("test_")


def is_source(path: str) -> bool:
    if is_test(path) or path.startswith("docs/") or path.startswith("."):
        return False
    return path.endswith((".py", ".js", ".html", ".ts", ".go", ".rs", ".java", ".rb", ".c", ".h"))


def test_command(path: str) -> str | None:
    """Django-style: tests/<app>/... -> './tests/runtests.py <app>'; otherwise pytest."""
    m = re.match(r"tests/(?:regressiontests/|modeltests/)?([^/]+)/", path)
    if m:
        return f"./tests/runtests.py {m.group(1)}"
    m = re.match(r"django/contrib/([^/]+)/tests/", path)
    if m:
        return f"./tests/runtests.py {m.group(1)}"
    if is_test(path):
        return f"pytest {path}"
    return None


@dataclass
class Pack:
    files: list[dict] = field(default_factory=list)
    test_command: str | None = None
    entities: list[str] = field(default_factory=list)

    def render(self) -> str:
        lines = ["Bearings context pack (from past work on this repo):", "Start in:"]
        for f in self.files:
            lines.append(f"  {f['path']}  (score {f['score']:.2f})")
            for why in f["why"][:2]:
                lines.append(f"      because {why}")
        if self.test_command:
            lines.append(f"Verify with: {self.test_command}")
        return "\n".join(lines)


class Bearings:
    """Write and read the context graph for one team/repo scope."""

    def __init__(self, db: Hydra | None, params: Params | None = None) -> None:
        self.db = db
        self.p = params or Params()
        # write-through mirror of the counts stored on the graph; rebuilt by load()
        self.df: dict[str, int] = defaultdict(int)
        self.n_events = 0
        self.n: dict[tuple[str, str], int] = defaultdict(int)
        self.miss: dict[tuple[str, str], int] = defaultdict(int)
        self.changes: dict[str, int] = defaultdict(int)
        self.co: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.co_written: dict[str, set[str]] = defaultdict(set)
        self.tested: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.files: set[str] = set()
        self.t_files: dict[str, set[str]] = defaultdict(set)
        self._pool = ThreadPoolExecutor(16)
        self._lazy = False
        self._df_loaded: set[str] = set()
        self._edges_loaded: set[str] = set()
        self._co_loaded: set[str] = set()
        self._init_pending()

    # ------------------------------------------------------------------ write
    # Writes are coalesced: ingest() updates the mirror and queues graph
    # writes; flush() sends them (node/provenance batches, then one statement
    # per weighted edge, in parallel - HydraDB batches cannot carry edge
    # properties). context_pack() flushes first, so reads always see writes.

    def _w_points(self, t: str, f: str) -> float:
        return max(0.001, math.log(SCALE / max(1, self.n[(t, f)])) + self.p.beta * math.log(1 + self.miss[(t, f)]))

    def _queue_points(self, t: str, f: str) -> None:
        self._pend_edges[("POINTS_TO", node_id("term", t), node_id("file", f))] = {
            "n": self.n[(t, f)], "miss": self.miss[(t, f)], "w": self._w_points(t, f)}

    def ingest(
        self,
        task_id: str,
        text: str,
        changed: list[str],
        read: list[str] | None = None,
        test_cmd: str | None = None,
        passed: bool = True,
        date: str = "",
        source: str = "task",
        flush: bool = True,
    ) -> dict:
        """Record a finished task and learn from its outcome."""
        read = read or []
        terms = sorted(extract(text))
        src_files = [f for f in changed if is_source(f)]
        tests = [f for f in changed if is_test(f)]
        cmds = sorted({c for c in (test_command(t) for t in tests) if c} | ({test_cmd} if test_cmd else set()))
        self._hydrate_for_write(terms, src_files + [f for f in read if f not in src_files])
        self.n_events += 1
        for t in terms:
            self.df[t] += 1
        all_files = sorted(set(changed) | set(read))
        self.files.update(all_files)
        for f in changed:
            self.changes[f] += 1
        self._pend_terms.update(terms)
        self._pend_files.update(all_files)
        tid = node_id("task", task_id)
        self._pend_tasks.append({"id": tid, "key": task_id, "date": date, "passed": passed, "source": source})
        self._pend_cmds.update(cmds)
        prov = self._pend_prov
        prov["MENTIONS"] += [(tid, node_id("term", t)) for t in terms]
        prov["CHANGED"] += [(tid, node_id("file", f)) for f in changed]
        prov["READ"] += [(tid, node_id("file", f)) for f in read]
        prov["VERIFIED_BY"] += [(tid, node_id("cmd", c)) for c in cmds]

        # learned links: entity -> changed source file. Cheaper when the task
        # passed; dearer when it failed.
        for t in terms:
            for f in src_files:
                if passed:
                    self.n[(t, f)] += 1
                    self.t_files[t].add(f)
                else:
                    self.miss[(t, f)] += 1
                    if self.n[(t, f)] == 0:
                        continue
                self._queue_points(t, f)
        # files the agent read but did not change: the links that sent it there
        # led nowhere this time
        if passed:
            for t in terms:
                for f in read:
                    if f not in changed and self.n[(t, f)] > 0:
                        self.miss[(t, f)] += 1
                        self._queue_points(t, f)

        # second hop: files that change together (top-K per file)
        if passed and len(src_files) > 1:
            for a in src_files:
                for b in src_files:
                    if a != b:
                        self.co[a][b] += 1
            self._pend_co.update(src_files)
        for f in src_files:
            for c in cmds:
                self.tested[f][c] += 1
                self._pend_edges[("TESTED_BY", node_id("file", f), node_id("cmd", c))] = {"n": self.tested[f][c]}
        if flush:
            self.flush()
        return {"task": task_id, "entities": len(terms), "files": len(changed), "tests": cmds}

    def _init_pending(self) -> None:
        self._pend_terms: set[str] = set()
        self._pend_files: set[str] = set()
        self._pend_tasks: list[dict] = []
        self._pend_cmds: set[str] = set()
        self._pend_prov: dict[str, list[tuple[int, int]]] = defaultdict(list)
        self._pend_edges: dict[tuple[str, int, int], dict] = {}
        self._pend_co: set[str] = set()
        self._exists: set[tuple[str, int, int]] = getattr(self, "_exists", set())

    def pending(self) -> bool:
        return bool(self._pend_terms or self._pend_files or self._pend_tasks or self._pend_edges or self._pend_co)

    def flush(self) -> int:
        db = self.db
        if db is None:  # in-memory mode (dev tuning)
            for a in sorted(self._pend_co):
                top = sorted(self.co[a].items(), key=lambda kv: (-kv[1], kv[0]))[: self.p.co_top_k]
                self.co_written[a] = {b for b, _ in top}
            self._init_pending()
            return 0
        # rewrite top-K co-change edges of touched files
        for a in sorted(self._pend_co):
            top = sorted(self.co[a].items(), key=lambda kv: (-kv[1], kv[0]))[: self.p.co_top_k]
            keep = {b for b, _ in top}
            for b in self.co_written[a] - keep:
                key = ("CO_CHANGED", node_id("file", a), node_id("file", b))
                self._pend_edges[key] = None  # delete
            for b, c in top:
                self._pend_edges[("CO_CHANGED", node_id("file", a), node_id("file", b))] = {
                    "n": c, "w": self.p.hop_penalty + math.log((self.changes[a] + 1) / c)}
            self.co_written[a] = keep
        # nodes first (labels + properties), then edges
        db.batch("UNWIND $rows AS row MERGE (n {id: row.id}) SET n:Term, n.key = row.key, n.kind = row.kind, n.df = row.df",
                 [{"id": node_id("term", t), "key": t, "kind": t.split(":")[0], "df": self.df[t]} for t in sorted(self._pend_terms)])
        db.batch("UNWIND $rows AS row MERGE (n {id: row.id}) SET n:File, n.path = row.path, n.changes = row.changes, n.kind = row.kind",
                 [{"id": node_id("file", f), "path": f, "changes": self.changes[f], "kind": "file"} for f in sorted(self._pend_files)])
        db.batch("UNWIND $rows AS row MERGE (n {id: row.id}) SET n:Task, n.key = row.key, n.date = row.date, n.passed = row.passed, n.source = row.source",
                 self._pend_tasks)
        db.batch("UNWIND $rows AS row MERGE (n {id: row.id}) SET n:TestCmd, n.cmd = row.cmd",
                 [{"id": node_id("cmd", c), "cmd": c} for c in sorted(self._pend_cmds)])
        for rel, pairs in self._pend_prov.items():
            if pairs:
                db.batch(f"UNWIND $rows AS row CREATE (a {{id: row.src}})-[:{rel}]->(b {{id: row.dst}})",
                         [{"src": s, "dst": d} for s, d in pairs])
        edges = list(self._pend_edges.items())
        n = len(edges)

        def write(item):
            (rel, s, d), props = item
            if props is None:
                if (rel, s, d) in self._exists:
                    db.query(f"MATCH (a {{id: $s}})-[r:{rel}]->(b {{id: $d}}) DELETE r", {"s": s, "d": d})
                    self._exists.discard((rel, s, d))
                return
            params = {"s": s, "d": d, **props}
            if (rel, s, d) in self._exists:
                sets = ", ".join(f"r.{k} = ${k}" for k in props)
                db.query(f"MATCH (a {{id: $s}})-[r:{rel}]->(b {{id: $d}}) SET {sets}", params)
            else:
                inline = ", ".join(f"{k}: ${k}" for k in props)
                db.query(f"CREATE (a {{id: $s}})-[:{rel} {{{inline}}}]->(b {{id: $d}})", params)
                self._exists.add((rel, s, d))

        if len(edges) > 8:
            list(self._pool.map(write, edges))
        else:
            for e in edges:
                write(e)
        self._init_pending()
        return n

    def feedback(self, pack: Pack, correct: list[str]) -> int:
        """Penalise links behind suggested files that turned out wrong."""
        if not self.p.learn_misses:
            return 0
        good = set(correct)
        k = 0
        top = pack.files[: self.p.miss_top]
        self._hydrate_for_write(sorted({t for f in top for t in f["terms"]}), [])
        for f in top:
            if f["path"] in good:
                continue
            for t in f["terms"]:
                if self.n[(t, f["path"])] > 0:
                    self.miss[(t, f["path"])] += 1
                    self._queue_points(t, f["path"])
                    k += 1
        self.flush()
        return k

    # ------------------------------------------------------------------- read
    def select_terms(self, text: str) -> list[str]:
        ents = extract(text)
        self._hydrate_df(list(ents))
        cap = max(5, int(self.p.max_df_frac * max(1, self.n_events)))
        known = [t for t in ents if 0 < self.df.get(t, 0) <= cap]
        known.sort(key=lambda t: (self.df[t], t))
        return known[: self.p.max_terms]

    def context_pack(self, text: str, k: int = 5, hops: int | None = None, backend: str | None = None) -> Pack:
        """Rank files for a task. ``backend='db'`` runs the HydraDB path query;
        ``'local'`` is an in-memory reference implementation of the same query
        (used for dev-split tuning and to check the database's answers)."""
        hops = self.p.hops if hops is None else hops
        backend = backend or ("db" if self.db is not None else "local")
        if backend == "db" and self.pending():
            self.flush()
        terms = self.select_terms(text)
        pack = Pack(entities=terms)
        if not terms:
            return pack
        rows = self._db_paths(terms, hops) if backend == "db" else self._local_paths(terms, hops)
        n_ev = max(1, self.n_events)
        best: dict[tuple[str, str], tuple[float, dict]] = {}
        for path, weight in rows:
            nodes = path["nodes"]
            term = nodes[0]["props"].get("key")
            target = nodes[-1]["props"].get("path")
            if not term or not target or not is_source(target):
                continue
            df = nodes[0]["props"].get("df") or self.df.get(term, 1)
            cost = weight - LN_SCALE + math.log(df + 1)
            key = (term, target)
            if key not in best or cost < best[key][0]:
                best[key] = (cost, path)
        scores: dict[str, float] = defaultdict(float)
        evidence: dict[str, list[tuple[float, str, str]]] = defaultdict(list)
        for (term, target), (cost, path) in best.items():
            idf = math.log(n_ev / self.df.get(term, 1)) + 1
            s = idf * math.exp(-cost)
            scores[target] += s
            evidence[target].append((s, term, explain(path)))
        # entities that literally name a file get a direct structural boost
        for t in extract(text):
            for f in path_candidates(t):
                if f in self.files and is_source(f):
                    scores[f] += 2.0
                    evidence[f].append((2.0, t, f"the task names {f}"))
        ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))[:k]
        for f, s in ranked:
            ev = sorted(evidence[f], reverse=True)
            pack.files.append({"path": f, "score": s, "why": [e[2] for e in ev[:3]], "terms": [e[1] for e in ev]})
        cmds: dict[str, float] = defaultdict(float)
        for f in pack.files[:3]:
            tests = self.tested.get(f["path"], {})
            total = sum(tests.values()) or 1
            for c, n in tests.items():
                cmds[c] += n / total * f["score"]
        if cmds:
            pack.test_command = max(cmds.items(), key=lambda kv: kv[1])[0]
        return pack

    def _db_paths(self, terms: list[str], hops: int) -> list:
        rel = "['POINTS_TO', 'CO_CHANGED']" if hops >= 2 else "['POINTS_TO']"
        q = (
            "CALL algo.MSpaths({sourceLabel: 'Term', sourceProperty: 'key', "
            f"sourceValues: {cypher_strings(terms)}, relTypes: {rel}, relDirection: 'outgoing', "
            f"maxLen: {hops}, weightProp: 'w', pathCount: {self.p.paths_per_term}, pairwise: false}}) "
            "YIELD path, pathWeight RETURN path, pathWeight"
        )
        return self.db.query(q, page_size=4096)

    def _local_paths(self, terms: list[str], hops: int) -> list:
        """Same answer as the MSpaths call, computed from the mirror."""
        by_term = self.t_files
        out = []
        for t in terms:
            tnode = {"id": node_id("term", t), "props": {"key": t, "df": self.df[t]}}
            cands = []
            for f in by_term.get(t, []):
                w1 = self._w_points(t, f)
                fid = node_id("file", f)
                cands.append((w1, 1, [tnode["id"], fid], t, [f]))
                if hops >= 2:
                    for g in self.co_written.get(f, ()):
                        c = self.co[f][g]
                        w2 = self.p.hop_penalty + math.log((self.changes[f] + 1) / c)
                        cands.append((w1 + w2, 2, [tnode["id"], fid, node_id("file", g)], t, [f, g]))
            cands.sort(key=lambda c: (c[0], c[1], c[2]))
            for w, ln, _, term, files in cands[: self.p.paths_per_term]:
                nodes = [tnode] + [{"id": node_id("file", f), "props": {"path": f}} for f in files]
                rels = [{"type": "POINTS_TO"}] + ([{"type": "CO_CHANGED"}] if ln == 2 else [])
                out.append(({"nodes": nodes, "rels": rels}, w))
        return out

    # ----------------------------------------------------------------- load
    # ------------------------------------------------------------ lazy mirror
    def _hydrate_df(self, terms: list[str]) -> None:
        todo = [t for t in terms if t not in self._df_loaded]
        if not todo or not self._lazy:
            return

        def get(t):
            rows = self.db.query("MATCH (t:Term {id: $id}) RETURN t.df AS df", {"id": node_id("term", t)})
            return t, (rows[0][0] if rows else 0) or 0
        for t, df in self._pool.map(get, todo):
            self.df[t] = df
            self._df_loaded.add(t)

    def _hydrate_for_write(self, terms: list[str], files: list[str]) -> None:
        if not self._lazy:
            return
        self._hydrate_df(terms)
        todo = [t for t in terms if t not in self._edges_loaded]

        def edges(t):
            return t, self.db.query("MATCH (t {id: $id})-[r:POINTS_TO]->(f) RETURN f.path AS p, r.n AS n, r.miss AS m",
                                    {"id": node_id("term", t)})
        for t, rows in self._pool.map(edges, todo):
            for path, n, m in rows:
                self.n[(t, path)] = n or 0
                self.t_files[t].add(path)
                self.miss[(t, path)] = m or 0
                self._exists.add(("POINTS_TO", node_id("term", t), node_id("file", path)))
            self._edges_loaded.add(t)
        for f in files:
            if f in self._co_loaded:
                continue
            rows = self.db.query("MATCH (f:File {id: $id}) RETURN f.changes AS c", {"id": node_id("file", f)})
            self.changes[f] = (rows[0][0] if rows else 0) or 0
            for path, n in self.db.query("MATCH (a {id: $id})-[r:CO_CHANGED]->(b) RETURN b.path AS p, r.n AS n",
                                         {"id": node_id("file", f)}):
                self.co[f][path] = n or 0
                self.co_written[f].add(path)
                self._exists.add(("CO_CHANGED", node_id("file", f), node_id("file", path)))
            self._co_loaded.add(f)

    def load(self, full: bool = True) -> None:
        """Rebuild the mirror from the graph. ``full=False`` loads only what reads
        need (task count, file list, test links); the rest is fetched lazily per
        entity/file when a task is reported."""
        db = self.db
        if not full:
            self._lazy = True
            for (path,) in db.query("MATCH (f:File) RETURN f.path AS path", page_size=4096):
                self.files.add(path)
            for path, cmd, n in db.query("MATCH (f:File)-[r:TESTED_BY]->(c) RETURN f.path AS p, c.cmd AS cmd, r.n AS n", page_size=4096):
                if path and cmd:
                    self.tested[path][cmd] = n or 0
                    self._exists.add(("TESTED_BY", node_id("file", path), node_id("cmd", cmd)))
            rows = db.query("MATCH (t:Task) RETURN count(*) AS n")
            self.n_events = rows[0][0] if rows else 0
            return
        for tid, key, df in db.query("MATCH (t:Term) RETURN t.id AS id, t.key AS key, t.df AS df", page_size=4096):
            self.df[key] = df or 0
        id2term = {node_id("term", k): k for k in self.df}
        for fid, path, ch in db.query("MATCH (f:File) RETURN f.id AS id, f.path AS path, f.changes AS c", page_size=4096):
            self.files.add(path)
            self.changes[path] = ch or 0
        id2file = {node_id("file", f): f for f in self.files}
        for s, d, n, m in db.query("MATCH (t:Term)-[r:POINTS_TO]->(f) RETURN t.id AS s, f.id AS d, r.n AS n, r.miss AS m", page_size=4096):
            if s in id2term and d in id2file:
                self._exists.add(("POINTS_TO", s, d))
                self.n[(id2term[s], id2file[d])] = n or 0
                self.t_files[id2term[s]].add(id2file[d])
                self.miss[(id2term[s], id2file[d])] = m or 0
        for s, d, n in db.query("MATCH (a:File)-[r:CO_CHANGED]->(b) RETURN a.id AS s, b.id AS d, r.n AS n", page_size=4096):
            if s in id2file and d in id2file:
                self.co[id2file[s]][id2file[d]] = n or 0
                self.co_written[id2file[s]].add(id2file[d])
                self._exists.add(("CO_CHANGED", s, d))
        for s, cmd, n in db.query("MATCH (f:File)-[r:TESTED_BY]->(c) RETURN f.id AS s, c.cmd AS cmd, r.n AS n", page_size=4096):
            if s in id2file and cmd:
                self.tested[id2file[s]][cmd] = n or 0
                self._exists.add(("TESTED_BY", s, node_id("cmd", cmd)))
        rows = db.query("MATCH (t:Task) RETURN count(*) AS n")
        self.n_events = rows[0][0] if rows else 0


def explain(path: dict) -> str:
    nodes = path["nodes"]
    parts = []
    for n in nodes:
        p = n["props"]
        parts.append(p.get("key") or p.get("path") or str(n["id"]))
    rels = [r["type"] for r in path["rels"]]
    s = parts[0]
    for r, n in zip(rels, parts[1:]):
        s += f" -{r}-> {n}"
    return s
