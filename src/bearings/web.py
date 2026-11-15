"""Bearings dashboard: result charts plus a "try a task" view.

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
    t0 = time.time()
    e = eng()
    p = e.context_pack(task, k=5, hops=hops)
    return JSONResponse({
        "scope": f"{TEAM}/{REPO}",
        "ms": round((time.time() - t0) * 1000),
        "entities": p.entities[:30],
        "files": [{"path": f["path"], "score": round(f["score"], 3), "why": f["why"]} for f in p.files],
        "test_command": p.test_command,
        "pack_text": p.render(),
        "graph_tasks": e.n_events,
    })


async def examples(_: Request):
    rows = []
    for line in open(ROOT / "data/derived/tasks.jsonl"):
        t = json.loads(line)
        if t["verified"] and t["date"] >= "2022-07-01":
            rows.append({"id": t["id"], "text": t["text"][:3000], "gold": t["files"]})
    return JSONResponse(rows[:40])


app = Starlette(routes=[
    Route("/", index),
    Route("/api/pack", pack),
    Route("/api/examples", examples),
    Route("/results/{path:path}", asset),
])


def main() -> None:
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("BEARINGS_WEB_PORT", "8765")), log_level="warning")


if __name__ == "__main__":
    main()
