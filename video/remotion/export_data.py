"""Export every number and text the Remotion video shows into public/data.json.

  uv run python video/remotion/export_data.py      (needs HydraDB running for the real pack)

Reuses video/build.py (the same logic as bench/report.py) so the video and
results/RESULTS.md can never disagree.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(ROOT / "bench"))
sys.path.insert(0, str(ROOT / "src"))

import build  # noqa: E402
import report as rep  # noqa: E402


def replay() -> dict:
    """Per-issue hit@1 for the history-seeded replay, in date order (dev + test)."""
    rs = rep.rows(rep.RES / "level1_history.jsonl", split=None)
    return {"date": [r["date"][:7] for r in rs], "split": [r["split"] for r in rs],
            "bearings": [int(r["metrics"]["bearings"]["hit@1"]) for r in rs],
            "bm25": [int(r["metrics"]["bm25"]["hit@1"]) for r in rs]}


def handoff() -> dict:
    """Everything the handoff scenes show, from committed result files and the live graph."""
    import re
    import time
    import report_handoff as RH
    import handoff as H
    from bearings import handoff as HO
    md, h = RH.section()
    A, B = h["A"], h["B"]
    # the decomposition (results/level2_decompose.txt), cold-start row
    txt = (rep.RES / "level2_decompose.txt").read_text()
    after = int(re.search(r"^none\s+[\d,]+\s+[\d,]+\s+[\d,]+\s+(\d+)%", txt, re.M).group(1))
    row = re.search(r"^none\s+(\d+)%\s+(\d+)%\s+(\d+)%", txt.split("aimed at")[1], re.M)
    pivot = {"after_pct": after, "parts": [{"label": "neighbouring source", "pct": int(row.group(1))},
                                           {"label": "tests and docs", "pct": int(row.group(2))},
                                           {"label": "re-reading the fix file", "pct": int(row.group(3))}],
             "source": "40 live runs without memory (DeepSeek through OpenCode), results/level2_decompose.txt"}
    # one real recorded run: the first memory run (date order) that succeeded and opened 6-9 files incl. a test
    runs = H.prior_runs()
    res = {r["id"]: r for r in map(json.loads, open(H.PRIOR / "results.jsonl"))}
    pick = next(r for r in runs if r["src"] == "refuseless" and res.get(r["issue"], {}).get("success")
                and 6 <= len(r["reads"]) <= 9 and any(f.startswith("tests/") for f in r["reads"]))
    calls = []
    for line in pick["path"].read_text().splitlines():
        e = json.loads(line)
        if e["type"] == "tool_use":
            inp = e["part"]["state"].get("input", {}) or {}
            c = inp.get("command") or (f"read {inp.get('filePath', '')}" if inp.get("filePath") else json.dumps(inp))
            calls.append(c.replace("/work/repo/", "").replace("cd /work/repo && ", "")[:90])
    reads = [{"f": f, "lines": ", ".join(f"{a}-{b}" for a, b in v["spans"][:2]), "concluded": f in pick["concluded"]}
             for f, v in sorted(pick["reads"].items(), key=lambda kv: (kv[0] not in pick["concluded"], kv[0].startswith("tests/"), kv[0]))][:8]
    g = HO.HydraGraph(H.Hydra(tenant="bench", subtenant="handoff-video"))
    g.reset()
    t0 = time.time()
    g.record([pick])
    rec_ms = round((time.time() - t0) * 1000)
    g.reset()
    # a real pack from Experiment A (first target whose graph run succeeded), rebuilt live for timing
    rows = [json.loads(x) for x in open(H.RUNS / "results.jsonl")] if (H.RUNS / "results.jsonl").exists() else []
    gr = next((r for r in rows if r["condition"] == "graph" and r["id"] == "django__django-15863"), None)
    pack = {}
    if gr:
        t = next(t for t in H.pool(runs) if t["id"] == gr["id"])
        hg = HO.HydraGraph(H.Hydra(tenant=H.SCOPE[0], subtenant=H.SCOPE[1]))
        t1 = time.time()
        pk = H.build_pack(hg, t, H.earlier(runs, t), H.FINAL)
        ms = round((time.time() - t1) * 1000)
        info = hg.run_info(pk["runs"][:4])
        pack = {"id": gr["id"].replace("django__", ""), "text": gr["pack"], "tokens": gr["pack_tokens"], "ms": ms,
                "terms": [x.split(":", 1)[1] for x in HO.run_terms(t["text"])[:5]],
                "runs": [(info.get(k, {}).get("title") or k)[:34] for k in pk["runs"][:4]],
                "source": [f for f, _ in pk["source"]], "test": [f for f, _ in pk["test"]]}
    lab = {"cold": "Cold start", "notes": "Handoff notes", "graph": "Bearings pack"}

    def bars(E):
        return [{"key": c, "label": lab[c], "median_in": E["conds"][c]["median_in"],
                 "note": f"{E['conds'][c]['succ'][0]:.0%} success"} for c in ("cold", "notes", "graph") if c in E["conds"]]
    acc = RH.accumulation(A)
    import re
    txt = (rep.RES / "handoff_retrieval.txt").read_text().split("targets whose fix files")[0]
    both = lambda name: float(re.search(re.escape(name) + r"\s+\S+ \[[^]]*\]\s+\S+ \[[^]]*\]\s+(\S+)", txt).group(1))
    curve = [[int(m.group(1)), float(m.group(2))] for m in re.finditer(r"Graph, first (\d+) recorded runs\s+\S+ \[[^]]*\]\s+\S+ \[[^]]*\]\s+(\S+)", txt)]
    ld = json.load(open(rep.RES / "handoff_load.json"))
    store = {"bars": [{"label": "Plain word → file table", "v": both("Plain word -> file table")},
                      {"label": "Word + code anchor table", "v": both("Plain word+anchor -> file table")},
                      {"label": "Bearings graph", "v": both("Graph (final)")}],
             "curve": curve,
             "load": {k: ld[k] for k in ("clients", "requests", "errors", "p50_ms", "p95_ms", "rps", "runs_recorded_during_test")},
             "foot": "Share of 102 later issues where the pack holds every fix file and a real test file, no model calls (results/handoff_retrieval.txt, handoff_load.json)"}
    return {"store": store, "pivot": pivot, "record": {"issue": pick["issue"].replace("django__", ""), "calls": calls[:24], "reads": reads},
            "record_ms": rec_ms, "pack": pack, "A": A, "B": B, "acc": json.load(open(rep.RES / "handoff_accumulation.json")),
            "acc_foot": "Total size of the earlier runs' handoff notes vs the median pack over 102 targets built from the same runs (results/handoff_accumulation.json)",
            "results": {"A": bars(A) if A.get("n") else [], "B": bars(B) if B.get("n") else []}}


def main() -> None:
    d = build.build_data()
    d["replay"] = replay()
    d["handoff"] = handoff()
    d["handoff"]["results"].update(json.load(open(HERE / "results_text.json")) if (HERE / "results_text.json").exists() else {})
    (HERE / "public" / "data.json").write_text(json.dumps(d, default=str))
    print("wrote", HERE / "public" / "data.json")


if __name__ == "__main__":
    main()
