# Bearings

**Coding agents re-explore a repository from scratch on every task. Bearings remembers where past work landed, so the next agent starts there.**

Bearings is a learned context layer for coding agents. It keeps a graph of finished tasks in self-hosted [HydraDB](https://github.com/hydra-db/hydradb): the entities in each task (symbols, file paths, error names, distinctive words), the files that were changed, the files that were read, the test that verified it, and whether it passed. When a new task arrives, one weighted path query walks from the task's entities to files and returns a small **context pack**: the few files to start in, the test command, and the graph path that justifies each file.

- Links that led to a correct outcome get cheaper. Links that were suggested and led nowhere get dearer.
- The graph is shared by a team. HydraDB's tenant and subtenant scopes map to team and repo, so what one person's agent learns, every agent on the team starts from.
- A repo's merged history seeds the graph before any agent has run, so a new team gets value on day one.
- **Bearings makes no model calls.** Entity extraction and routing are plain code. The context layer is free to run and needs no API key.

Bearings does not cache answers and does not make repeated prompts free. The agent still does the work. The saving is the exploration it skips on tasks that are different but touch the same code.

{{RESULTS_SUMMARY}}

## How it works

```
(:Term {key, df}) -[:POINTS_TO {n, miss, w}]-> (:File {path})        learned: entity -> changed file
(:File)           -[:CO_CHANGED {n, w}]->      (:File)               learned: files that change together (top 8 per file)
(:File)           -[:TESTED_BY {n}]->          (:TestCmd {cmd})      learned: where a file's tests live
(:Task) -[:MENTIONS]-> (:Term)   (:Task) -[:CHANGED|READ]-> (:File)   (:Task) -[:VERIFIED_BY]-> (:TestCmd)
```

Edge weights are costs, so lower is stronger:

- `POINTS_TO.w = ln(1000 / n) + ln(1 + miss)`: `n` counts tasks where the entity appeared and the file was changed; `miss` counts tasks where the link was suggested (or the file was read) and the file turned out not to need changing.
- `CO_CHANGED.w = 1.5 + ln((changes(src) + 1) / n)`.

**Read side.** Entities are extracted from the task text with plain regular expressions; node ids are a hash of the normalised entity, because HydraDB has no text search. One `algo.MSpaths` call starts from the task's entity nodes and returns the cheapest paths over `POINTS_TO` (and `CO_CHANGED` for the second hop):

```cypher
CALL algo.MSpaths({sourceLabel: 'Term', sourceProperty: 'key', sourceValues: ['sym:floatformat', 'err:invalidoperation', ...],
                   relTypes: ['POINTS_TO', 'CO_CHANGED'], relDirection: 'outgoing', maxLen: 2,
                   weightProp: 'w', pathCount: 20, pairwise: false})
YIELD path, pathWeight RETURN path, pathWeight
```

The client turns each path's weight into `-ln P(file | entity)` (the entity's `df` comes back on the path), sums `idf × P` per file, and keeps the top 5. Every suggestion carries the path that produced it, for example
`symbol 'floatformat' -> django/template/defaultfilters.py (together in 7 past changes)`.

**Write side.** `report_task` records the task node and its provenance edges in batches, then updates the weighted edges one statement each (HydraDB cannot batch edge properties). Writes are coalesced and sent in parallel.

## Quick start

Requirements: Linux or macOS, Docker, [uv](https://docs.astral.sh/uv/), git. About 15 minutes for the first HydraDB build.

```bash
git clone https://github.com/hydra-db/hydradb.git          # next to this repo
git clone <this repo> bearings && cd bearings
uv sync
```

**1. Start HydraDB** (builds the open-source image from your checkout on first run; data lives in `.hydradb/`):

```bash
scripts/start_hydradb.sh
```

**2. Seed the graph from your repo's history** (issue-fixing commits; or `--github owner/name` for merged PRs through `gh`):

```bash
uv run bearings --team myteam --repo myrepo import-history /path/to/myrepo
```

**3. Connect your agent.** Claude Code:

```bash
claude mcp add bearings -e BEARINGS_TEAM=myteam -e BEARINGS_REPO=myrepo -- uv run --quiet --directory "$PWD" bearings-mcp
```

OpenCode (`opencode.json`):

```json
{"mcp": {"bearings": {"type": "local", "command": ["uv", "run", "--quiet", "--directory", "/abs/path/to/bearings", "bearings-mcp"],
                      "environment": {"BEARINGS_TEAM": "myteam", "BEARINGS_REPO": "myrepo"}}}}
```

Any MCP client works the same way: the server is stdio and has two tools, `get_context_pack(task)` and `report_task(task, changed_files, read_files, test_command, passed)`.

**4. Dashboard** (charts plus a "try a task" view against the live graph):

```bash
BEARINGS_TEAM=myteam BEARINGS_REPO=myrepo uv run bearings-web     # http://127.0.0.1:8765
```

CLI: `bearings pack "<task>"`, `bearings report "<task>" --changed a.py --test "pytest tests/test_a.py"`, `bearings stats`.

## Reproducing the numbers

All result files are committed under `results/` and `runs/level2/`. `uv run python bench/report.py` regenerates `results/RESULTS.md` and `results/report.html` from them; every number in this README comes from that output.

To rerun from scratch:

```bash
# inputs: SWE-bench parquet files + a Django clone (not committed)
mkdir -p data/raw data/repos
for s in SWE-bench SWE-bench_Verified SWE-bench_Lite; do
  curl -L -o data/raw/$(echo $s | sed 's/SWE-bench_//;s/SWE-bench/full/' | tr A-Z a-z).parquet \
    https://huggingface.co/datasets/princeton-nlp/$s/resolve/main/data/test-00000-of-00001.parquet
done
git clone https://github.com/django/django data/repos/django
uv run python scripts/prepare_data.py          # -> data/derived/{tasks,history}.jsonl (committed)

scripts/start_hydradb.sh
uv run python bench/level1.py --seed history --out results/level1_history.jsonl    # ~1.5 h
uv run python bench/level1.py --seed tasks   --out results/level1_tasks.jsonl      # ~15 min
uv run python bench/second_hop.py
uv run python bench/level2.py build-graph
uv run python bench/level2.py run --tasks 40                                       # live agents, ~2 h
uv run python bench/report.py
```

{{METHOD_AND_RESULTS}}

## Licence

Bearings is MIT licensed. HydraDB is licensed under the Elastic License 2.0 and is used here unmodified, self-hosted, built from its public repository.
