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

from rank_bm25 import BM25Okapi

from .core import is_source
from .entities import extract, path_candidates


def _tokens(text: str) -> list[str]:
    toks = []
    for k, c in extract(text).items():
        toks += [k] * c
    return toks


class BM25Baseline:
    def __init__(self, neighbours: int = 50) -> None:
        self.docs: list[list[str]] = []
        self.files: list[list[str]] = []
        self.k = neighbours
        self._index: BM25Okapi | None = None

    def ingest(self, text: str, changed: list[str]) -> None:
        src = [f for f in changed if is_source(f)]
        if not src:
            return
        self.docs.append(_tokens(text) or ["<empty>"])
        self.files.append(src)
        self._index = None

    def rank(self, text: str, k: int = 5) -> list[str]:
        if not self.docs:
            return []
        if self._index is None:
            self._index = BM25Okapi(self.docs)
        scores = self._index.get_scores(_tokens(text) or ["<empty>"])
        top = sorted(range(len(scores)), key=lambda i: -scores[i])[: self.k]
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
