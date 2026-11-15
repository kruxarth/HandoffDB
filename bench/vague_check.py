"""Retrieval only, no model calls: the 40 Level 2 issues as written, and as
"vague reports" (src/bearings/vague.py: code, paths and identifiers removed).
Graph, dictionary and keyword search all learn from events before the cutoff.
  uv run python bench/vague_check.py   -> results/vague_check.txt
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "bench"))
import level2  # noqa: E402
from bearings.baselines import BM25Baseline  # noqa: E402
from bearings.vague import vague  # noqa: E402

ts = level2.sample(40, 0)
dic, bm = level2.DictBaseline(), BM25Baseline()
for e in level2.events_before(level2.CUTOFF):
    dic.ingest(e["text"], e["files"])
    bm.ingest(e["text"], e["files"])
eng = level2.bearings_engine()
R = ROOT / "data/repos/django"
res = {}
for mode in ("as written", "vague"):
    for t in ts:
        txt = t["text"] if mode == "as written" else vague(t["text"])
        g = set(t["files"])
        b = [f["path"] for f in eng.context_pack(txt, k=5, repo=R, commit=t["base_commit"]).files]
        for name, lst in (("Bearings", b), ("dictionary", dic.rank(txt, k=5)), ("keyword search (BM25)", bm.rank(txt, k=5))):
            r = res.setdefault((mode, name), [0, 0])
            r[0] += bool(g & set(lst[:1]))
            r[1] += bool(g & set(lst))
out = [f"{len(ts)} Level 2 issues (SWE-bench Verified, after the graph's cutoff). Retrieval only.", ""]
out += [f"{m:11s} {n:22s} hit@1={h1 / len(ts):.2f} hit@5={h5 / len(ts):.2f}" for (m, n), (h1, h5) in res.items()]
(ROOT / "results" / "vague_check.txt").write_text("\n".join(out) + "\n")
print("\n".join(out))
