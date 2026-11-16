#!/usr/bin/env bash
# Before committing run logs: make sure no API key or local home path is in tracked files.
#   scripts/check_secrets.sh            # report
#   scripts/check_secrets.sh --scrub    # also rewrite home paths in result/run logs to <home>
set -euo pipefail
cd "$(dirname "$0")/.."
fail=0
# 1. API keys from .env and the OpenCode auth file must not appear anywhere tracked or staged
keys=()
for envf in .env ../.env; do
  [[ -f $envf ]] && while IFS='=' read -r k v; do [[ -n "${v:-}" ]] && keys+=("${v//\"/}"); done < <(grep -v '^#' "$envf" | grep '=')
done
if [[ -f "$HOME/.local/share/opencode/auth.json" ]]; then
  while read -r v; do keys+=("$v"); done < <(python3 -c "import json,os;[print(v['key']) for v in json.load(open(os.path.expanduser('~/.local/share/opencode/auth.json'))).values() if v.get('key')]")
fi
for k in "${keys[@]}"; do
  [[ ${#k} -lt 12 ]] && continue
  if git grep -q -F -- "$k" $(git ls-files) 2>/dev/null || grep -rqF -- "$k" runs/level2 runs/handoff results bench video/remotion/public 2>/dev/null; then
    echo "SECRET FOUND (value hidden) in tracked files or run logs"; fail=1
  fi
done
# 2. local home paths
# the checkout may live outside $HOME (e.g. /data/<user>/...): scrub that prefix too
alt=$(pwd -P | cut -d/ -f1-3)
[[ "$alt" == "$HOME" ]] && alt=""
if [[ "${1:-}" == "--scrub" ]]; then
  for pfx in "$HOME" $alt; do
    grep -rlF "$pfx" results runs/level2 runs/handoff 2>/dev/null | while read -r f; do sed -i "s#$pfx#<home>#g" "$f"; done
  done
fi
n=0
for pfx in "$HOME" $alt; do n=$((n + $(grep -rlF "$pfx" $(git ls-files) 2>/dev/null | wc -l || true))); done
echo "files with home paths: $n"; [[ $n -gt 0 ]] && grep -rlF -e "$HOME" ${alt:+-e "$alt"} $(git ls-files) | head
exit $fail
