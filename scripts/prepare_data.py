"""Build the benchmark inputs from SWE-bench and the Django git history.

Outputs (committed, so every later step is reproducible without network):
  data/derived/tasks.jsonl    SWE-bench Django tasks, date order
  data/derived/history.jsonl  Django issue-fix commits, date order

Inputs (downloaded, not committed):
  data/raw/full.parquet, data/raw/verified.parquet, data/raw/lite.parquet
      from huggingface.co/datasets/princeton-nlp/SWE-bench{,_Verified,_Lite}
  data/repos/django   git clone https://github.com/django/django
"""

import json
import re
import sys
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from bearings.history import git_history  # noqa: E402

RAW = ROOT / "data/raw"
OUT = ROOT / "data/derived"
DIFF_RE = re.compile(r"^diff --git a/(\S+) b/", re.M)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    verified = {r["instance_id"] for r in pq.read_table(RAW / "verified.parquet").to_pylist()}
    lite = {r["instance_id"] for r in pq.read_table(RAW / "lite.parquet").to_pylist()}
    rows = [r for r in pq.read_table(RAW / "full.parquet").to_pylist() if r["repo"] == "django/django"]
    rows.sort(key=lambda r: (r["created_at"], r["instance_id"]))
    with open(OUT / "tasks.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps({
                "id": r["instance_id"],
                "date": r["created_at"],
                "base_commit": r["base_commit"],
                "text": r["problem_statement"],
                "files": DIFF_RE.findall(r["patch"]),
                "test_files": DIFF_RE.findall(r["test_patch"]),
                "verified": r["instance_id"] in verified,
                "lite": r["instance_id"] in lite,
            }) + "\n")
    print("tasks", len(rows))
    n = 0
    with open(OUT / "history.jsonl", "w") as f:
        for ev in git_history(str(ROOT / "data/repos/django"), branch="main"):
            f.write(json.dumps(ev) + "\n")
            n += 1
    print("history", n)


if __name__ == "__main__":
    main()
