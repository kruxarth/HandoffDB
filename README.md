# Bearings

**Coding agents re-explore a repository from scratch on every task. Bearings remembers where past work landed, so the next agent starts there.**

Bearings is a learned context layer for coding agents, stored as a graph in self-hosted [HydraDB](https://github.com/hydra-db/hydradb). Every finished task is written as structure: the entities in it (symbols, paths, error names, distinctive words), the files it changed, the test that verified it. When a new task arrives, one weighted path query walks from its entities to files, and Bearings joins that with where the task's identifiers are defined in the current checkout. The agent gets a small **context pack**: the files to start in, the exact lines to read, the test to run, and the reason behind each file.

- **It learns.** Links that led to the real fix get cheaper; links that were suggested and led nowhere get dearer.
- **It is shared.** HydraDB's tenant and subtenant scopes map to team and repo: what one person's agent learns, every agent on the team starts from.
- **It starts on day one.** A repo's merged history (issue-fixing commits or merged PRs) seeds the graph before any agent has run.
- **It makes no model calls.** Entity extraction, routing and code anchors are plain code. The layer is free to run and needs no API key.

Bearings does not cache answers and does not make repeated prompts free. The agent still does the work; what Bearings adds is a ranked starting point. **What we can show:** it ranks the real fix first more often than keyword search, and learns fast from an empty start (Level 1). **What we could not show:** a token saving for live agents. On SWE-bench Verified issues the agent finds the file in its first step anyway, with or without a pack (Level 2).

## Results

Measured on Django, the project with the most SWE-bench issues. Full tables with 95% bootstrap intervals: [`results/RESULTS.md`](results/RESULTS.md). Dashboard with charts and a live "try a task" view: `uv run bearings-web`.

**Retrieval (Level 1).** All 850 SWE-bench Django issues replayed in date order; each is answered using only what was learned before it, then learned from. Scored on the 724 issues from 2019-07 on (tuning used only the 126 before).

| top-5 hit rate / top-1 hit rate | seeded from history | empty start |
|---|---|---|
| **Bearings** (learned graph + code anchors) | **76.7% / 49.2%** | **70.7% / 45.4%** |
| Keyword search (BM25) over past issues | 76.0% / 42.0% | 55.1% / 29.8% |
| Dictionary: word → file counts, no graph | 68.1% / 39.9% | 49.0% / 25.4% |
| Learned graph only (Bearings v1) | 68.0% / 39.5% | 50.3% / 26.7% |
| Code anchors only | 52.5% / 37.8% | 52.5% / 37.8% |
| Bearings, frozen graph (never learns) | 76.4% / 45.2% | 64.0% / 40.9% |
| Bearings without the second hop | 76.4% / 49.2% | 70.7% / 45.4% |

- Seeded from history, Bearings puts the real fix **first 7.2 points more often than keyword search** (paired, [+2.9, +11.6]) and ties it at top 5 (+0.7 [−2.5, +4.0]).
- From an empty graph it beats keyword search by **15.6 points at top 5** ([+11.3, +19.8]), and beats the same graph frozen at the start by 6.8 points ([+4.3, +9.1]): that is what learning as tasks arrive adds.
- The graph and the code anchors need each other: together they beat the graph alone by 8.7 points and the anchors alone by 24.2 points (history seed, top 5).
- **The second hop** (files that change together) is in the query and measured: **+0.3 points** at top 5 ([−0.3, +1.0]). It rarely changes the top five.

**Live agents (Level 2): tokens to locate the right files.** Measured with DeepSeek V4.1 Flash through OpenCode.

40 SWE-bench Verified issues from after the graph's cutoff, each run once with no memory, with a dictionary pack, and with the Bearings pack pasted into the prompt. **Result: no token saving.**

| | named every real-fix file | total input tokens, median [IQR] | tokens until a real-fix file is opened, median |
|---|---|---|---|
| No memory | 92.5% | 76,626 [45k–329k] | 6,928 |
| Dictionary pack | 95.0% | 112,149 [33k–309k] | 6,809 |
| **Bearings pack** | **95.0%** | 79,749 [45k–339k] | 7,061 |

- Paired vs no memory, Bearings: success +2.5 points [+0, +7.5]; whole-run tokens +20k mean [−20k, +61k], median per-issue ratio 1.03. Flat within noise.
- Why: on these issues the agent opens a real-fix file within its first step or two in **every** condition (~7k tokens, most of it the prompt). There is little search left for a pack to remove. Whole runs are dominated by how long the agent double-checks, which varies more than 2× between conditions on the same issue. The mean Δ for "tokens until a real-fix file" (−5.4k [−13.4k, −0.8k]) comes from one issue where the agent without memory wandered for 150k tokens; the median ratio is 1.06, so we do not claim it.
- A wrong pack can mislead: on two issues the pack's low-ranked files were unrelated (one matched the builtin name `max`) and the agent checked each before answering. Builtins are now skipped; trimming low-confidence files was tried on dev and lost real fixes, so it is not shipped.
- **Vague reports, checked before spending any agent runs** (`bench/vague_check.py`, retrieval only, the same 40 issues with code, paths and identifiers stripped by `src/bearings/vague.py`): Bearings' top-5 hit rate falls from 75% to 38%, the dictionary's from 68% to 38%, and keyword search's from 85% to 53%. On these 40 issues keyword search ranks better than Bearings both as written and vague; on the 724 Level 1 issues Bearings is ahead at top 1 and tied at top 5. So a context pack would not have helped live agents on vague reports either, and we did not run them.
- Where Bearings does help is ranking (Level 1): which file to open first among many plausible ones, and starting from an empty graph.

**Claude Code** (a demo, not a statistic): on two real issues fixed end to end, Bearings did **not** reduce tokens. Sonnet already knew where to look, and every extra turn re-reads ~35k tokens of context, so the pack's value was smaller than one turn. Details below.

## How it works

```
(:Term {key, df}) -[:POINTS_TO {n, miss, w}]-> (:File {path, changes})     entity -> file it was changed with
(:File)           -[:CO_CHANGED {n, w}]->      (:File)                     files that change together (top 8 per file)
(:File)           -[:TESTED_BY {n}]->          (:TestCmd {cmd})            where a file's tests live
(:Task) -[:MENTIONS]-> (:Term)   (:Task) -[:CHANGED|READ]-> (:File)   (:Task) -[:VERIFIED_BY]-> (:TestCmd)
```

Edge weights are costs, so lower is stronger:

- `POINTS_TO.w = ln(1000 / n) + ln(1 + miss)`: `n` counts tasks where the entity appeared and the file was changed; `miss` counts tasks where the link was suggested and the file turned out not to need changing.
- `CO_CHANGED.w = 1.5 + ln((changes(src) + 1) / n)`.

**Read side.** Entities are extracted from the task text with plain regular expressions; node ids are a hash of the normalised entity, because HydraDB has no text search. One `algo.MSpaths` call starts from the task's entity nodes and returns the cheapest paths over `POINTS_TO` (and `CO_CHANGED` for the second hop):

```cypher
CALL algo.MSpaths({sourceLabel: 'Term', sourceProperty: 'key', sourceValues: ['sym:formfield_callback', 'word:modelform', ...],
                   relTypes: ['POINTS_TO', 'CO_CHANGED'], relDirection: 'outgoing', maxLen: 2,
                   weightProp: 'w', pathCount: 20, pairwise: false})
YIELD path, pathWeight RETURN path, pathWeight
```

The client turns each path's weight into `-ln P(file | entity)` (the entity's `df` comes back on the path) and sums `idf × P` per file. Then **code anchors**: `git grep` in the agent's checkout for `def`/`class` definitions of identifiers the task names (`formfield_callback`, `ModelForm`), each weighted by how few files define it. The two scores are fused (anchor weight 2, chosen on the dev split), and the top files get line numbers. A pack looks like this:

```
Start in:
  1. django/forms/models.py  defines ModelForm (line 559), modelform_factory (line 563)
      because symbol 'modelform_factory' -> django/forms/models.py (together in 6 past changes)
  2. django/db/models/fields/__init__.py  defines formfield (line 1008), formfield (line 1095), ...
      because word 'formfield' -> django/db/models/fields/__init__.py (together in 13 past changes)
  ...
Verify with: ./tests/runtests.py model_forms
```
(The real pack for SWE-bench `django__django-15916`, an issue the graph never saw; the real fix changed `django/forms/models.py`.)

**Write side.** `report_task` (MCP) or the Claude Code stop hook records the task node and its provenance edges in batches, then updates the weighted edges one statement each (HydraDB cannot batch edge properties). Suggested files that were not changed get a miss. Writes are coalesced and sent in parallel.

**Delivery.** In Claude Code the pack arrives through a `UserPromptSubmit` hook and learning happens in a `Stop` hook (from `git status`), so neither costs the agent a turn. An MCP server with `get_context_pack` and `report_task` serves every other agent.

## Quick start

Requirements: Linux or macOS, Docker, [uv](https://docs.astral.sh/uv/), git. The first HydraDB build takes about 15 minutes.

```bash
git clone https://github.com/hydra-db/hydradb.git          # next to this repo
git clone https://github.com/kruxarth/bearings-hydradb.git bearings && cd bearings
uv sync
```

**1. Start HydraDB** (builds the open-source image from the checkout next door on first run; data lives in `.hydradb/`):

```bash
scripts/start_hydradb.sh
```

**2. Seed the graph from your repo's history** (issue-fixing commits; `--github owner/name` uses merged PRs through `gh`):

```bash
uv run bearings --team myteam --repo myrepo import-history /path/to/myrepo
```

**3. Connect your agent.**

Claude Code, recommended: hooks, so the pack is in the prompt and learning needs no tool call. Print the block and paste it into your repo's `.claude/settings.json`:

```bash
uv run bearings --team myteam --repo myrepo hooks-config
```

Claude Code via MCP instead (run from your repo, so code anchors read your checkout):

```bash
claude mcp add bearings -e BEARINGS_TEAM=myteam -e BEARINGS_REPO=myrepo -- uv run --quiet --directory /abs/path/to/bearings bearings-mcp
```

OpenCode (`opencode.json`):

```json
{"mcp": {"bearings": {"type": "local", "command": ["uv", "run", "--quiet", "--directory", "/abs/path/to/bearings", "bearings-mcp"],
                      "environment": {"BEARINGS_TEAM": "myteam", "BEARINGS_REPO": "myrepo", "BEARINGS_CHECKOUT": "/abs/path/to/myrepo"}}}}
```

**4. Dashboard** (charts plus a "try a task" view against the live graph):

```bash
BEARINGS_TEAM=myteam BEARINGS_REPO=myrepo BEARINGS_CHECKOUT=/path/to/myrepo uv run bearings-web     # http://127.0.0.1:8765
```

CLI: `bearings pack "<task>"`, `bearings report "<task>" --changed a.py --test "pytest tests/test_a.py"`, `bearings stats`.

## The benchmark in detail

**Data.** SWE-bench (full test split) has 850 Django issues from 2015 to 2023, each with its base commit and the files its real fix changed. Django's own history adds 21,217 issue-fixing commits ("Fixed #N") as the seed for the history scenario. Only the dataset is used: no SWE-bench Docker images, no test suites.

**The graph is seeded from the dataset's real fixes.** In Level 1 each issue is answered first, then its real fix is learned, the way a team's graph learns from its own merged work. Nothing from an issue's own fix is visible before it is answered. In Level 2 the graph is built once from history and issues before 2022-07-01 and is read-only; nothing is learned from the agents' own runs.

**Split and tuning.** Dev = the 126 issues before 2019-07-01; test = the 724 after. Every tuned value (anchor weight, edge-cost constants, entity caps) was chosen on dev. Test issues cannot be near-copies of learning issues in a way that leaks the answer: each test issue is answered from strictly earlier events, and the score is whether the files of *its own* later fix come back.

**Level 1 conditions** (all on identical issues, all seeing the same events): keyword search (BM25 over past issue texts, a file scores the sum of its issues' scores), dictionary (word → file counts, same entities and same formula as Bearings' first hop), learned graph only, code anchors only, Bearings without the second hop, Bearings, and Bearings with a graph frozen at the first test issue. HydraDB's answer is checked against an in-memory reference implementation of the same query on every issue.

**Level 2.** Real SWE-bench Verified issues from after the graph's cutoff (2022-07-01), taken in date order. For each issue an OpenCode agent (DeepSeek V4.1 Flash, the same model throughout) gets the issue text and a history-free snapshot of Django at the issue's commit, explores with shell tools, and names the files it would change. It does not write the fix, so the run measures *locating* the right files, which is the part a context layer can help with.

- **Conditions**, all on identical issues: no memory; a dictionary pack (word → file counts) pasted into the prompt; Bearings' pack pasted into the prompt (the same text the Claude Code hook injects: files, line anchors, a test command); and, on the first issues only, code anchors alone (an ablation dropped later to stay within budget).
- **Success** = the agent's final answer contains every file the real fix changed. Timeouts count as failures; runs that were rate-limited or never started are excluded and counted in the report.
- **Tokens** are OpenCode's own usage reports, summed over the run (fresh + cached input), and include the pack. Two token figures are reported. *Whole run*: everything the agent read. *Until a real-fix file is opened*: input tokens up to the step where the agent first reads a file the fix changed. We added the second after the pilot runs showed agents finding the file in a few steps and then spending most of the run double-checking it, which a context pack cannot shorten. It is a post-hoc metric and labelled as such. Runs that never open a real-fix file count at their full total.
- **Sandbox**: a bubblewrap sandbox with no network except an allow-list proxy to the model API; web search, web fetch and paths outside the snapshot are denied. The prompt also asks the agent to stop once it has identified the files (added after pilots where agents spent 20 steps hunting for the upstream fix in git objects). Both pilots, the run with the MCP tool instead of a pasted pack and the run before the stop line, are committed as `results/level2_pilot_*.jsonl` and excluded from the main table.
- **Model access**: the runs started on OpenCode's free tier and moved to the DeepSeek API (same model, `deepseek/deepseek-flash`) when the free tier's limit was reached. Each row records the model it used.

**Leaks found and closed.** Early live runs were contaminated, and all of them were discarded:
1. Worktrees exposed the future fix through `git log --all`. Each run now gets a fresh single-commit snapshot of the repo at the issue's commit (`scripts/snapshot.sh`).
2. Agents ran `find /` and read other checkouts on the machine. Runs now happen in a bubblewrap sandbox that sees only the snapshot and a fresh OpenCode data dir (`scripts/sandbox_opencode.sh`).
3. Agents used web search and `curl` to fetch the upstream commit. The sandbox now has no network except an allow-list proxy to the model API (`scripts/netproxy.py`); every attempt to reach out is blocked and logged.

**What we tried that did not help** (all on dev, none shipped): a "past similar tasks" channel through `Task` nodes (no reliable gain over the direct links); adding keyword-search scores to the fusion (no reliable gain); treating plain lower-case words as identifiers for code anchors (hit@5 .778 → .683); tuning the miss penalty and hop cost (flat within noise); showing only files scored within a fraction of the top file, to cut noise in the pack (the real fix is among the shown files less often: .778 → .754 at the mildest cut; `results/dev/exp_trim_history.txt`). Delivering the pack through an MCP tool call made agents spend extra turns; see the Claude Code results.

**Claude Code demo.** `bench/claude_demo.py` runs one real issue through headless Claude Code (`claude -p`, sonnet, Claude Code 2.1.325) without and with Bearings and prints the usage block side by side. Claude Code reports `input_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens`, `output_tokens`, `num_turns` and a list-price `total_cost_usd`.

| Issue | Run | total input tokens | vs first run without | turns | right files |
|---|---|---|---|---|---|
| django__django-15863 | without Bearings | 108,493 | | 4 | yes |
| | without Bearings (rerun) | 142,809 | +32% | 5 | yes |
| | v1, MCP tool | 185,137 | +71% | 7 | yes |
| | v1, prompt hook | 144,424 | +33% | 5 | yes |
| | v2, hooks (graph + code anchors) | 144,292 | +33% | 5 | yes |
| django__django-16560 | without Bearings | 253,968 | | 6 | yes |
| | without Bearings (rerun) | 304,542 | +20% | 7 | yes |
| | v1, MCP tool | 295,771 | +16% | 8 | yes |
| | v1, prompt hook | 316,110 | +24% | 8 | yes |
| | v2, hooks (graph + code anchors) | 408,458 | +61% | 11 | yes |

Total input = uncached + cache write + cache read, from Claude Code's own usage block (sonnet). Full columns and list-price arithmetic: `results/RESULTS.md`.

Bearings v1 (MCP tool, graph only) and v2 (hooks, graph + code anchors) both cost more than running without it on these two issues, and a second run without Bearings shows ±20–30% run-to-run noise. Both issues name the function to change, and Sonnet went straight to it. In Claude Code every turn re-reads the whole context (~35k tokens here), so a context layer pays off only when it removes turns: on issues where the agent would otherwise search. Two demo issues cannot show that either way. Level 2 measured it on 40 issues with DeepSeek and found no saving there either, for the same reason: the issues already point at the code.

## Reproducing the numbers

All result files are committed: `results/level1_*.jsonl`, `runs/level2/` (every agent's full event log), `results/claude_demo/`. One command regenerates `results/RESULTS.md` and the dashboard from them:

```bash
uv run python bench/report.py
```

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
uv run python bench/level1.py --seed history --no-frozen --scope django-history-v2 --out results/level1_history.jsonl   # ~1.5 h
uv run python bench/level1_frozen.py --seed history --out results/level1_history_frozen.jsonl
uv run python bench/level1.py --seed tasks --no-frozen --scope django-tasks-v2 --out results/level1_tasks.jsonl          # ~25 min
uv run python bench/level1_frozen.py --seed tasks --out results/level1_tasks_frozen.jsonl
uv run python bench/level2.py build-graph
L2_MODEL=deepseek/deepseek-flash uv run python bench/level2.py run --tasks 40 --conditions none,dict,anchors,bearings
uv run python bench/latency.py
uv run python bench/report.py
```

Dev-split experiments: `uv run python bench/exp_anchor.py --seed history` (code anchors) and `bench/tune_dev.py`.

## Licence

Bearings is MIT licensed (see `LICENSE`). HydraDB is licensed under the Elastic License 2.0 and is used here unmodified, self-hosted, built from its public repository.
