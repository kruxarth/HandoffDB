#!/usr/bin/env bash
# Start a self-hosted HydraDB node (open-source build) in Docker.
#   scripts/start_hydradb.sh          build image if missing, start, wait for ready
#   scripts/start_hydradb.sh stop     stop and remove the container (data is kept)
#   scripts/start_hydradb.sh reset    stop and delete the local store
# Env: HYDRADB_SRC (path to a hydradb checkout, default ../hydradb)
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="${HYDRADB_SRC:-$HERE/../hydradb}"
IMAGE=bearings-hydradb:0.4.0
NAME=bearings-hydradb
STATE="$HERE/.hydradb"
TOKEN=local-development-token-32-bytes

case "${1:-start}" in
  stop) docker rm -f "$NAME" >/dev/null 2>&1 || true; echo "hydradb: stopped"; exit 0 ;;
  reset) docker rm -f "$NAME" >/dev/null 2>&1 || true; rm -rf "$STATE"; echo "hydradb: store deleted"; exit 0 ;;
  start) ;;
  *) echo "usage: $0 [start|stop|reset]" >&2; exit 2 ;;
esac

if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
  echo "hydradb: building $IMAGE from $SRC (first build takes several minutes)"
  DOCKER_BUILDKIT=0 docker build -f "$HERE/docker/hydradb.Dockerfile" -t "$IMAGE" "$SRC"
fi

if docker ps --format '{{.Names}}' | grep -qx "$NAME"; then
  echo "hydradb: already running"
else
  docker rm -f "$NAME" >/dev/null 2>&1 || true
  mkdir -p "$STATE/store" "$STATE/cache"
  printf '%s\n' "$TOKEN" > "$STATE/auth-token"
  chmod -R a+rwX "$STATE"
  docker run -d --name "$NAME" --user "$(id -u):$(id -g)" \
    -p 127.0.0.1:7687:7687 -p 127.0.0.1:8443:8443 -p 127.0.0.1:9090:9090 \
    -v "$STATE:/data" \
    -e CLOUD_PROVIDER=local -e LOCAL_PATH=/data/store \
    -e GRAPH_NAMESPACE=default -e GRAPH_ID=default \
    -e GRAPH_CELL_ID=cell-0 -e GRAPH_CELLS=cell-0 -e GRAPH_NODE_ID=node-0 \
    -e GRAPH_BOLT_ADDR=0.0.0.0:7687 -e GRAPH_HTTP_ADDR=0.0.0.0:8443 -e GRAPH_ADMIN_ADDR=0.0.0.0:9090 \
    -e GRAPH_BOLT_NODE_ADDRESSES=node-0=127.0.0.1:7687 -e GRAPH_ADVERTISED_BOLT_ADDR=127.0.0.1:7687 \
    -e GRAPH_DATA_CACHE_DIR=/data/cache -e GRAPH_AUTH_TOKEN_FILE=/data/auth-token \
    -e GRAPH_ALLOW_PLAINTEXT=true -e RUST_MIN_STACK=33554432 -e RUST_LOG=warn \
    "$IMAGE" >/dev/null
fi

for _ in $(seq 1 120); do
  if curl -fsS -o /dev/null http://127.0.0.1:9090/readyz 2>/dev/null; then
    echo "hydradb: ready (bolt 7687, http 8443, admin 9090, token $TOKEN)"
    exit 0
  fi
  sleep 1
done
echo "hydradb: not ready after 120s; logs:" >&2
docker logs --tail 30 "$NAME" >&2
exit 1
