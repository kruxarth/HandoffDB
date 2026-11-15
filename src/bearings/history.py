"""History importer: turn a repository's merged-change history into learning events.

Two sources:

* ``git_history``: the local git log of the default branch. Every commit that
  closes an issue ("Fixed #123 -- ...", "fixes #123", "(#123)") becomes an
  event whose text is the commit message and whose files are the files it
  changed. Works offline on any clone.
* ``github_prs``: merged pull requests through the ``gh`` CLI (title + body ->
  changed files). Optional; needs ``gh auth``.

An event is a plain dict: ``{"id", "date", "text", "files", "source"}``.
"""

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Iterator

ISSUE_REF = re.compile(r"(?:fixe[sd]|close[sd]|refs?)\s+#\d+|\(#\d+\)", re.I)
SEP = "\x1e"  # record separator between commits


def git_history(
    repo: str,
    branch: str = "HEAD",
    only_issue_fixes: bool = True,
    since: str | None = None,
) -> Iterator[dict]:
    """Yield commits on the first-parent line of ``branch``, oldest first."""
    cmd = [
        "git", "-C", repo, "log", branch, "--first-parent", "--no-merges",
        "--reverse", "--name-only", f"--format={SEP}%H%x00%cI%x00%B%x00",
    ]
    if since:
        cmd.append(f"--since={since}")
    out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    for chunk in out.split(SEP):
        if not chunk.strip():
            continue
        sha, date, body, files = chunk.split("\x00", 3)
        files = [f for f in files.split("\n") if f.strip()]
        if only_issue_fixes and not ISSUE_REF.search(body):
            continue
        if not files:
            continue
        yield {
            "id": f"commit:{sha[:12]}",
            "sha": sha,
            "date": date,
            "text": body.strip(),
            "files": files,
            "source": "git",
        }


def github_prs(owner_repo: str, limit: int = 1000) -> Iterator[dict]:
    """Yield merged PRs (oldest first) using the GitHub CLI."""
    out = subprocess.run(
        [
            "gh", "pr", "list", "-R", owner_repo, "--state", "merged",
            "--limit", str(limit), "--json", "number,title,body,mergedAt,files",
        ],
        capture_output=True, text=True, check=True,
    ).stdout
    prs = sorted(json.loads(out), key=lambda p: p["mergedAt"])
    for pr in prs:
        files = [f["path"] for f in pr.get("files", [])]
        if not files:
            continue
        yield {
            "id": f"pr:{pr['number']}",
            "date": pr["mergedAt"],
            "text": f"{pr['title']}\n\n{pr.get('body') or ''}".strip(),
            "files": files,
            "source": "github",
        }
