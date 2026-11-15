"""Baselines for the Level 1 benchmark. In-memory, no graph.

* ``BM25Baseline``: keyword search over past task texts; a file's score is the
  sum of BM25 scores of the past tasks that changed it (top 50 neighbours).
* ``DictBaseline``: a plain table of learned entity->file counts, scored with
  the same formula Bearings uses for one hop (idf * n/df). It sees exactly the
  same entities and events as Bearings, so the only differences are the graph
  features: miss feedback, the second hop, and the query-time caps.
"""

from __future__ import annotations

import math
from collections import defaultdict


from .core import is_source
from .entities import extract, path_candidates


def _tokens(text: str) -> list[str]:
    toks = []
    for k, c in extract(text).items():
        toks += [k] * c
    return toks


class IncrementalBM25:
    """Exactly rank_bm25.BM25Okapi's scores (k1=1.5, b=0.75, epsilon idf floor),
    maintained incrementally with postings instead of rebuilt per query."""

    def __init__(self, k1: float = 1.5, b: float = 0.75, epsilon: float = 0.25) -> None:
        self.k1, self.b, self.eps = k1, b, epsilon
        self.nd: dict[str, int] = defaultdict(int)
        self.post: dict[str, list[tuple[int, int]]] = defaultdict(list)
        self.doc_len: list[int] = []
        self.total = 0

    def add(self, doc: list[str]) -> None:
        i = len(self.doc_len)
        freqs: dict[str, int] = defaultdict(int)
        for w in doc:
            freqs[w] += 1
        for w, f in freqs.items():
            self.nd[w] += 1
            self.post[w].append((i, f))
        self.doc_len.append(len(doc))
        self.total += len(doc)

    def scores(self, query: list[str]) -> dict[int, float]:
        n = len(self.doc_len)
        idf_sum, neg = 0.0, set()
        idf = {}
        qs = set(query)
        for w, f in self.nd.items():
            v = math.log(n - f + 0.5) - math.log(f + 0.5)
            idf_sum += v
            if v < 0:
                neg.add(w)
            if w in qs:
                idf[w] = v
        eps = self.eps * idf_sum / len(self.nd)
        for w in list(idf):
            if w in neg:
                idf[w] = eps
        avgdl = self.total / n
        out: dict[int, float] = defaultdict(float)
        for q in query:
            if q not in idf:
                continue
            for i, f in self.post[q]:
                out[i] += idf[q] * (f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * self.doc_len[i] / avgdl)))
        return out


class BM25Baseline:
    def __init__(self, neighbours: int = 50) -> None:
        self.files: list[list[str]] = []
        self.k = neighbours
        self.index = IncrementalBM25()

    def ingest(self, text: str, changed: list[str]) -> None:
        src = [f for f in changed if is_source(f)]
        if not src:
            return
        self.index.add(_tokens(text) or ["<empty>"])
        self.files.append(src)

    def rank(self, text: str, k: int = 5) -> list[str]:
        if not self.files:
            return []
        sc = self.index.scores(_tokens(text) or ["<empty>"])
        top = sorted(sc, key=lambda i: (-sc[i], i))[: self.k]
        scores = sc
        agg: dict[str, float] = defaultdict(float)
        for i in top:
            if scores[i] <= 0:
                continue
            for f in self.files[i]:
                agg[f] += scores[i]
        return [f for f, _ in sorted(agg.items(), key=lambda kv: (-kv[1], kv[0]))[:k]]


class DictBaseline:
    def __init__(self) -> None:
        self.n: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.df: dict[str, int] = defaultdict(int)
        self.events = 0
        self.files: set[str] = set()

    def ingest(self, text: str, changed: list[str]) -> None:
        terms = extract(text)
        self.events += 1
        src = [f for f in changed if is_source(f)]
        self.files.update(changed)
        for t in terms:
            self.df[t] += 1
            for f in src:
                self.n[t][f] += 1

    def rank(self, text: str, k: int = 5) -> list[str]:
        agg: dict[str, float] = defaultdict(float)
        ents = extract(text)
        for t in ents:
            df = self.df.get(t, 0)
            if not df:
                continue
            idf = math.log(max(1, self.events) / df) + 1
            for f, c in self.n[t].items():
                agg[f] += idf * c / (df + 1)
            for f in path_candidates(t):
                if f in self.files and is_source(f):
                    agg[f] += 2.0
        return [f for f, _ in sorted(agg.items(), key=lambda kv: (-kv[1], kv[0]))[:k]]
