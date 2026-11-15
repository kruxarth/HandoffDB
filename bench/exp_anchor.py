"""Dev-split experiment: does combining the learned graph with code anchors
(files in the checkout that define a symbol the task names) find files better?

Dev tasks only (before level1.TEST_FROM); in-memory reference backend.
  uv run python bench/exp_anchor.py [--seed history]
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "bench"))
from bearings.anchors import definitions  # noqa: E402
from bearings.baselines import BM25Baseline  # noqa: E402
from bearings.core import Bearings, Params  # noqa: E402
from level1 import metrics  # noqa: E402
from tune_dev import stream  # noqa: E402

REPO = ROOT / "data/repos/django"


def fuse(graph: list[dict], anchors: dict[str, float], w: float, k: int = 5) -> list[str]:
    sc: dict[str, float] = defaultdict(float)
    top = max([f["score"] for f in graph] or [1.0])
    for f in graph:
        sc[f["path"]] += f["score"] / top
    atop = max(anchors.values() or [1.0])
    for f, v in anchors.items():
        sc[f] += w * v / atop
    return [f for f, _ in sorted(sc.items(), key=lambda kv: (-kv[1], kv[0]))[:k]]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", default="history")
    ap.add_argument("--plain", type=int, default=0)
    a = ap.parse_args()
    import bearings.anchors as A
    A.PLAIN = bool(a.plain)
    eng = Bearings(None, Params())
    bm = BM25Baseline()
    W = [0.0, 0.5, 1.0, 2.0]
    res: dict[str, list] = defaultdict(list)
    for ev in stream(a.seed):
        if ev["kind"] == "task":
            pk = eng.context_pack(ev["text"], k=20, hops=2)
            anc = definitions(REPO, ev["base_commit"], ev["text"])
            for w in W:
                m = metrics(fuse(pk.files, anc, w), ev["files"])
                res[f"fused w={w}"].append(m)
            br = bm.rank(ev["text"], k=10)
            bsc = {f: 1.0 / (i + 2) for i, f in enumerate(br)}
            for wb in (0.5, 1.0):
                res[f"fused w=1 +bm25 {wb}"].append(metrics(fuse(pk.files, {f: anc.get(f, 0) / max(anc.values() or [1]) + wb * bsc.get(f, 0) * 2
                                                                         for f in set(anc) | set(bsc)}, 1.0), ev["files"]))
            res["core v2"].append(metrics([f["path"] for f in eng.context_pack(ev["text"], k=5, repo=REPO, commit=ev["base_commit"]).files], ev["files"]))
            res["anchors only"].append(metrics(fuse([], anc, 1.0), ev["files"]))
            res["bm25"].append(metrics(bm.rank(ev["text"]), ev["files"]))
            eng.feedback(eng.context_pack(ev["text"], k=5, hops=2), ev["files"])
        eng.ingest(ev["id"], ev["text"], ev["files"] + ev.get("test_files", []), flush=True)
        bm.ingest(ev["text"], ev["files"])
    for k, ms in res.items():
        n = len(ms)
        print(f"{k:16s} n={n} " + " ".join(f"{m}={sum(x[m] for x in ms) / n:.3f}" for m in ("hit@1", "hit@3", "hit@5")))


if __name__ == "__main__":
    main()
