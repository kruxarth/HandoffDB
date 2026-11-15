"""Can the second hop reach gold files the first hop cannot? (dev split, reference backend)

  uv run python bench/second_hop.py   -> results/second_hop_reach.json
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "bench"))
from bearings.core import Bearings, Params, is_source  # noqa: E402
from tune_dev import stream  # noqa: E402


def reach(seed: str) -> dict:
    eng = Bearings(None, Params())
    s = {"gold": 0, "hop1": 0, "hop2only": 0, "none": 0, "hop2only_in_pack": 0}
    for ev in stream(seed):
        if ev["kind"] == "task":
            h1 = set()
            for t in eng.select_terms(ev["text"]):
                h1 |= eng.t_files.get(t, set())
            h2 = set()
            for f in h1:
                h2 |= eng.co_written.get(f, set())
            pack = [f["path"] for f in eng.context_pack(ev["text"], k=5, hops=2).files]
            for g in ev["files"]:
                if not is_source(g):
                    continue
                s["gold"] += 1
                if g in h1:
                    s["hop1"] += 1
                elif g in h2:
                    s["hop2only"] += 1
                    s["hop2only_in_pack"] += g in pack
                else:
                    s["none"] += 1
        eng.ingest(ev["id"], ev["text"], ev["files"] + ev.get("test_files", []))
    return s


if __name__ == "__main__":
    out = {seed: reach(seed) for seed in ("history", "tasks")}
    (ROOT / "results" / "second_hop_reach.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
