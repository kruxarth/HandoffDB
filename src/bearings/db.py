"""Minimal HydraDB HTTP client with tenant/subtenant scopes.

HydraDB maps a (tenant, subtenant) scope onto the HTTP namespace
``<namespace>/<b64url(tenant)>/<b64url(subtenant)>``. Bearings uses
tenant = team, subtenant = repository, so every team's graph is isolated and
everyone on a team shares one graph per repo.
"""

from __future__ import annotations

import base64
import os
from typing import Any

import httpx


def _b64(s: str) -> str:
    return base64.urlsafe_b64encode(s.encode()).decode().rstrip("=")


class HydraError(RuntimeError):
    pass


class Hydra:
    def __init__(
        self,
        url: str | None = None,
        token: str | None = None,
        graph: str = "default",
        cell: str = "cell-0",
        namespace: str = "default",
        tenant: str | None = None,
        subtenant: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        self.url = (url or os.environ.get("BEARINGS_HYDRADB_URL", "http://127.0.0.1:8443")).rstrip("/")
        self.token = token or os.environ.get("BEARINGS_HYDRADB_TOKEN", "local-development-token-32-bytes")
        self.graph = graph
        self.cell = cell
        self.namespace = namespace
        if tenant and subtenant:
            self.namespace = f"{namespace}/{_b64(tenant)}/{_b64(subtenant)}"
        self.http = httpx.Client(
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {self.token}",
                "X-Graph-Namespace": self.namespace,
                "Content-Type": "application/json",
            },
        )
        self.requests = 0

    def query(self, cypher: str, params: dict[str, Any] | None = None, page_size: int | None = None) -> list[list[Any]]:
        """Run one statement; return rows of plain values (all pages)."""
        body: dict[str, Any] = {"cell_id": self.cell, "query": cypher}
        if params:
            body["parameters"] = params
        if page_size:
            body["page_size"] = page_size
        rows: list[list[Any]] = []
        while True:
            self.requests += 1
            r = self.http.post(f"{self.url}/v1/graphs/{self.graph}/query", json=body)
            try:
                payload = r.json()
            except ValueError as exc:
                raise HydraError(f"HTTP {r.status_code}: {r.text[:300]}") from exc
            if "error" in payload:
                raise HydraError(f"{payload['error'].get('code')}: {payload['error'].get('message')}\n{cypher[:400]}")
            if "rows" not in payload:
                raise HydraError(f"unexpected response {r.status_code}: {str(payload)[:300]}")
            rows.extend([decode(c) for c in row] for row in payload["rows"])
            cur = payload.get("next_cursor")
            if cur is None:
                return rows
            body["cursor"] = cur
            body["query_id"] = payload["query_id"]
            body.setdefault("page_size", 1024)

    def batch(self, cypher: str, rows: list[dict], chunk: int = 1000) -> None:
        for i in range(0, len(rows), chunk):
            self.query(cypher, {"rows": rows[i : i + chunk]})

    def ready(self) -> bool:
        try:
            return self.http.get(f"{self.url}/healthz", timeout=2).status_code == 200
        except httpx.HTTPError:
            return False


def decode(cell: dict) -> Any:
    t = cell.get("type")
    if t == "null":
        return None
    if t == "list":
        return [decode(c) for c in cell["value"]]
    if t == "path":
        v = cell["value"]
        return {
            "nodes": [
                {
                    "id": n["id"],
                    "labels": n.get("labels", []),
                    "props": {k: next(iter(p.values())) for k, p in n.get("properties", {}).items()},
                }
                for n in v["nodes"]
            ],
            "rels": [
                {
                    "type": e["edge_type"],
                    "src": e["src"],
                    "dst": e["dst"],
                    "props": {k: next(iter(p.values())) for k, p in (e.get("properties") or {}).items()},
                }
                for e in v["relationships"]
            ],
        }
    return cell.get("value")


def cypher_strings(values: list[str]) -> str:
    """Inline a list of strings as a Cypher literal (list params are rejected in procedures)."""
    return "[" + ", ".join("'" + v.replace("\\", "\\\\").replace("'", "\\'") + "'" for v in values) + "]"
