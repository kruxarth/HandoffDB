"""HandoffDB dashboard: result charts plus a "try a task" view.

  uv run bearings-web            # http://127.0.0.1:8765  (scope: $BEARINGS_TEAM/$BEARINGS_REPO)

Serves results/report.html (built by bench/report.py) and GET /api/pack?task=...
which runs the real path query against HydraDB.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import FileResponse, HTMLResponse, JSONResponse
from starlette.routing import Route

from .core import Bearings, Params
from .db import Hydra

ROOT = Path(__file__).resolve().parents[2]
TEAM = os.environ.get("BEARINGS_TEAM", "bench")
REPO = os.environ.get("BEARINGS_REPO", "django-l2")
# checkout used for code anchors: $BEARINGS_CHECKOUT, else the bundled Django clone if present
CHECKOUT = os.environ.get("BEARINGS_CHECKOUT") or (str(ROOT / "data/repos/django") if (ROOT / "data/repos/django").exists() else None)
_eng: Bearings | None = None


def eng() -> Bearings:
    global _eng
    if _eng is None:
        _eng = Bearings(Hydra(tenant=TEAM, subtenant=REPO), Params())
        _eng.load(full=False)
    return _eng


async def index(_: Request):
    p = ROOT / "results" / "report.html"
    if p.exists():
        return FileResponse(p)
    return HTMLResponse("<p>Run <code>uv run python bench/report.py</code> first.</p>")


async def asset(request: Request):
    p = (ROOT / "results" / request.path_params["path"]).resolve()
    if ROOT / "results" not in p.parents or not p.exists():
        return HTMLResponse("not found", status_code=404)
    return FileResponse(p)


async def pack(request: Request):
    task = request.query_params.get("task", "")[:20000]
    hops = int(request.query_params.get("hops", "2"))
    commit = request.query_params.get("commit") or None
    if commit and not commit.isalnum():
        commit = None
    t0 = time.time()
    e = eng()
    p = e.context_pack(task, k=5, hops=hops, repo=CHECKOUT, commit=commit)
    from .db import cypher_strings
    cypher = ("CALL algo.MSpaths({sourceLabel: 'Term', sourceProperty: 'key',\n"
              f"  sourceValues: {cypher_strings(p.entities[:8])[:-1]}, ...],\n"
              "  relTypes: ['POINTS_TO', 'CO_CHANGED'], relDirection: 'outgoing',\n"
              "  maxLen: 2, weightProp: 'w', pathCount: 20, pairwise: false})\nYIELD path, pathWeight")
    return JSONResponse({
        "scope": f"{TEAM}/{REPO}",
        "ms": round((time.time() - t0) * 1000),
        "entities": p.entities[:30],
        "files": [{"path": f["path"], "score": round(f["score"], 3), "why": f["why"], "lines": f.get("lines", [])}
                  for f in p.files],
        "code": (f"{Path(CHECKOUT).name}@{commit[:8]}" if commit else Path(CHECKOUT).name) if CHECKOUT else None,
        "cypher": cypher,
        "test_command": p.test_command,
        "pack_text": p.render(),
        "graph_tasks": e.n_events,
    })


HO_TEAM = os.environ.get("BEARINGS_HANDOFF_TEAM", "bench")
HO_REPO = os.environ.get("BEARINGS_HANDOFF_REPO", "handoff-v2")


async def handoff_pack(request: Request):
    """The handoff pack, live from HydraDB: what earlier agent runs opened and concluded near this task.
    With ``before`` (an ISO date) only runs on issues dated before it are used, as in the experiments."""
    from . import handoff as HO
    from .anchors import definitions
    task = request.query_params.get("task", "")[:20000]
    commit = request.query_params.get("commit") or None
    if commit and not commit.isalnum():
        commit = None
    before = request.query_params.get("before") or None
    t0 = time.time()
    g = HO.HydraGraph(Hydra(tenant=HO_TEAM, subtenant=HO_REPO))
    anchors = []
    if CHECKOUT:
        sc = definitions(Path(CHECKOUT), commit or "HEAD", task)
        anchors = [f for f, _ in sorted(sc.items(), key=lambda kv: (-kv[1], kv[0]))[:8]]
    allowed = None
    if before:
        allowed = {k for k, d in g.db.query("MATCH (n:HInfo) RETURN n.key, n.date") if (d or "") < before}
    terms = HO.run_terms(task)
    t1 = time.time()
    pk = HO.build_pack(g, terms, anchors, allowed, HO.Params())
    ms_graph = round((time.time() - t1) * 1000)
    info = g.run_info(pk["runs"][:5])
    rows = lambda xs: [{"path": f, "runs": sorted(d["runs"] | d["concluded"]), "concluded": len(d["concluded"]),  # noqa: E731
                        "lines": sorted(d["lines"], key=lambda x: int(x.split("-")[0]))[:4]} for f, d in xs]
    txt = HO.render(pk, info)
    return JSONResponse({"scope": f"{HO_TEAM}/{HO_REPO}", "ms": round((time.time() - t0) * 1000), "ms_graph": ms_graph,
                         "calls": pk.get("calls"), "entities": terms[:20], "anchors": anchors,
                         "source": rows(pk["source"]), "test": rows(pk["test"]), "doc": rows(pk["doc"]),
                         "runs": [{"key": k, **info.get(k, {})} for k in pk["runs"][:5]], "n_runs": pk["n_runs"],
                         "pack_text": txt, "tokens": HO.tokens(txt)})


async def handoff_examples(_: Request):
    rows = []
    for line in open(ROOT / "data/derived/tasks.jsonl"):
        t = json.loads(line)
        if t["date"] >= "2022-07-01":
            rows.append({"id": t["id"], "text": t["text"][:3000], "gold": t["files"], "gold_tests": t["test_files"],
                         "base_commit": t["base_commit"], "date": t["date"]})
    return JSONResponse(rows[:60])


async def examples(_: Request):
    rows = []
    for line in open(ROOT / "data/derived/tasks.jsonl"):
        t = json.loads(line)
        if t["verified"] and t["date"] >= "2022-07-01":
            rows.append({"id": t["id"], "text": t["text"][:3000], "gold": t["files"], "base_commit": t["base_commit"]})
    return JSONResponse(rows[:40])


app = Starlette(routes=[
    Route("/", index),
    Route("/api/pack", pack),
    Route("/api/examples", examples),
    Route("/api/handoff/pack", handoff_pack),
    Route("/api/handoff/examples", handoff_examples),
    Route("/results/{path:path}", asset),
])


def main() -> None:
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("BEARINGS_WEB_PORT", "8765")), log_level="warning")


if __name__ == "__main__":
    main()
