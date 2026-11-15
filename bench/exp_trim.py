"""Dev-split experiment for v2.1: (a) skip Python builtins as code anchors,
(b) show only files whose fused score is at least tau x the top file's.

Measures, on dev tasks only, whether the real fix is among the files *shown*
and how many files are shown. Rule fixed before running: pick the largest tau
whose shown-set hit rate is within 1 point of tau=0 (the untrimmed top 5).
  uv run python bench/exp_trim.py [--seed history]
"""
import argparse
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "bench"))
import bearings.anchors as A  # noqa: E402
from bearings.core import Bearings, Params  # noqa: E402
from tune_dev import stream  # noqa: E402

REPO = ROOT / "data/repos/django"
TAUS = [0.0, 0.2, 0.3, 0.4, 0.5, 0.6]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", default="history")
    a = ap.parse_args()
    eng = Bearings(None, Params())
    res = defaultdict(lambda: [0, 0, 0])  # hits, shown, n
    for ev in stream(a.seed):
        if ev["kind"] == "task":
            gold = set(ev["files"])
            for sb in (False, True):
                A.SKIP_BUILTINS = sb
                pk = eng.context_pack(ev["text"], k=5, repo=REPO, commit=ev["base_commit"])
                if not pk.files:
                    continue
                top = pk.files[0]["score"]
                for t in TAUS:
                    shown = [f["path"] for f in pk.files if f["score"] >= t * top]
                    r = res[(sb, t)]
                    r[0] += bool(gold & set(shown)); r[1] += len(shown); r[2] += 1
            A.SKIP_BUILTINS = True
            eng.feedback(eng.context_pack(ev["text"], k=5, hops=2), ev["files"])
        eng.ingest(ev["id"], ev["text"], ev["files"] + ev.get("test_files", []), flush=True)
    for (sb, t), (h, s, n) in sorted(res.items()):
        print(f"skip_builtins={sb!s:5} tau={t:.1f}  any-real-file-shown={h / n:.3f}  files shown={s / n:.2f}  n={n}")


if __name__ == "__main__":
    main()
