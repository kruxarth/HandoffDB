#!/usr/bin/env bash
# Run `opencode run ...` in a bubblewrap sandbox for benchmarks.
# The agent sees: system dirs read-only, the repo snapshot at /work/repo, its
# config at /work/opencode.json, and a fresh empty OpenCode data dir. Nothing
# else of $HOME (no other checkouts, no git history, no past sessions).
# The sandbox has no network of its own (--unshare-net). <net-dir> must hold
# proxy.sock (scripts/netproxy.py, allow-list HTTPS proxy for the model API)
# and optionally mcp.sock (relay to the Bearings MCP server). Inside, socat
# exposes them on 127.0.0.1:3128 and 127.0.0.1:8766.
#   scripts/sandbox_opencode.sh <snapshot-dir> <config.json> <data-dir> <net-dir> -- <opencode args...>
set -euo pipefail
snap=$1; cfg=$2; data=$3; net=$4; shift 4; [[ "${1:-}" == "--" ]] && shift
mkdir -p "$data/share" "$data/state" "$data/cache"
cp -r "$HOME/.cache/opencode/." "$data/cache/" 2>/dev/null || true
args=(
  --ro-bind /usr /usr --symlink usr/bin /bin --symlink usr/lib /lib --symlink usr/lib /lib64 --symlink usr/bin /sbin
  --ro-bind /etc /etc --proc /proc --dev /dev --tmpfs /tmp --tmpfs /run
  --tmpfs "$HOME"
  --ro-bind "$HOME/.opencode" "$HOME/.opencode"
  --bind "$data/share" "$HOME/.local/share/opencode"
  --bind "$data/state" "$HOME/.local/state/opencode"
  --bind "$data/cache" "$HOME/.cache/opencode"
  --bind "$snap" /work/repo
  --bind "$net" /work/net
  --ro-bind "$cfg" /work/opencode.json
  --setenv HOME "$HOME" --setenv OPENCODE_CONFIG /work/opencode.json
  --setenv OPENCODE_DISABLE_CLAUDE_CODE 1 --setenv OPENCODE_DISABLE_CLAUDE_CODE_SKILLS 1
  --setenv OPENCODE_DISABLE_CLAUDE_CODE_PROMPT 1
  --setenv HTTPS_PROXY http://127.0.0.1:3128 --setenv https_proxy http://127.0.0.1:3128
  --setenv HTTP_PROXY http://127.0.0.1:3128 --setenv http_proxy http://127.0.0.1:3128
  --setenv NO_PROXY 127.0.0.1,localhost --setenv no_proxy 127.0.0.1,localhost
  --unshare-pid --unshare-ipc --unshare-net --die-with-parent --chdir /work/repo
)
inner='socat TCP-LISTEN:3128,bind=127.0.0.1,fork,reuseaddr UNIX-CONNECT:/work/net/proxy.sock & 
if [ -S /work/net/mcp.sock ]; then socat TCP-LISTEN:8766,bind=127.0.0.1,fork,reuseaddr UNIX-CONNECT:/work/net/mcp.sock & fi
sleep 0.3; exec "$0" "$@"'
exec bwrap "${args[@]}" /bin/sh -c "$inner" "$HOME/.opencode/bin/opencode" "$@"
