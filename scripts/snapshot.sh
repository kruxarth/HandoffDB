#!/usr/bin/env bash
# Create a history-free checkout of a repo at one commit, so an agent cannot
# find the future fix with `git log --all`.
#   scripts/snapshot.sh <repo> <commit> <dest>
set -euo pipefail
repo=$1; commit=$2; dest=$3
rm -rf "$dest"; mkdir -p "$dest"
git -C "$repo" archive "$commit" | tar -x -C "$dest"
git -C "$dest" init -q
git -C "$dest" add -A
git -C "$dest" -c user.name=bench -c user.email=bench@localhost commit -q -m "snapshot"
