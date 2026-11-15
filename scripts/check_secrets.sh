#!/usr/bin/env bash
# Before committing run logs: make sure no API key or local home path is in tracked files.
#   scripts/check_secrets.sh            # report
#   scripts/check_secrets.sh --scrub    # also rewrite home paths in result/run logs to <home>
set -euo pipefail
cd "$(dirname "$0")/.."
fail=0
# 1. API keys from .env and the OpenCode auth file must not appear anywhere tracked or staged
keys=()
[[ -f .env ]] && while IFS='=' read -r k v; do [[ -n "${v:-}" ]] && keys+=("${v//\"/}"); done < <(grep -v '^#' .env)
if [[ -f "$HOME/.local/share/opencode/auth.json" ]]; then
  while read -r v; do keys+=("$v"); done < <(python3 -c "import json,os;[print(v['key']) for v in json.load(open(os.path.expanduser('~/.local/share/opencode/auth.json'))).values() if v.get('key')]")
fi
for k in "${keys[@]}"; do
  [[ ${#k} -lt 12 ]] && continue
  if git grep -q -F -- "$k" $(git ls-files) 2>/dev/null || grep -rqF -- "$k" runs/level2 results 2>/dev/null; then
    echo "SECRET FOUND (value hidden) in tracked files or run logs"; fail=1
  fi
done
# 2. local home paths
if [[ "${1:-}" == "--scrub" ]]; then
  grep -rlF "$HOME" results runs/level2 2>/dev/null | while read -r f; do sed -i "s#$HOME#<home>#g" "$f"; done
fi
n=$(grep -rlF "$HOME" $(git ls-files) 2>/dev/null | wc -l || true)
echo "files with home paths: $n"; [[ $n -gt 0 ]] && grep -rlF "$HOME" $(git ls-files) | head
exit $fail
