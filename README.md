# Bearings

**Every coding agent starts cold. Bearings hands it what earlier agents on the same repository already worked out, as a graph in HydraDB.**

Each agent run is recorded in self-hosted [HydraDB](https://github.com/hydra-db/hydradb) as structure, straight from its tool calls: what it opened, at which lines, which tests and docs it found, what it concluded. No model call. The next agent, on the same task or a different one near the same code, gets a small pack from a few graph traversals instead of re-exploring, or reading a pile of handoff notes.

⟨HEADLINE⟩

Everything below was measured with **DeepSeek V4.1 Flash through OpenCode**, in a network-isolated sandbox, on real SWE-bench Django issues, with success checked in code. Pre-registered in [`bench/handoff_prereg.md`](bench/handoff_prereg.md) before any run on the targets. Full tables: [`results/RESULTS.md`](results/RESULTS.md). Dashboard with the charts and a live "paste a task" box: `uv run bearings-web`.

## The four judging questions

1. **Did we measure the right metrics, not a vanity number?** The primary metric is what a team pays for: **total input tokens per agent run**, summed from OpenCode's per-step usage, *including* the pack's own tokens and any notes the agent reads, paired by issue. It counts only alongside **success checked in code** (the agent must name every source file of the real fix and a test file the real fix extended), and a saving is claimed only at equal or better success. The rule, the targets and the exclusions were committed before any target run ([`bench/handoff_prereg.md`](bench/handoff_prereg.md)). The baseline is the one teams actually use, Markdown handoff notes written by the earlier agents, with the cost of writing them counted. ⟨Q1⟩ Files: `runs/handoff/results.jsonl`, `runs/handoff/same/results.jsonl`.
2. **Does it keep learning over a baseline?** Yes, as runs accumulate: with the first 0, 25, 50, 100, 200 and 300 recorded runs, the pack holds the fix files and a real test file for 0%, 9%, 14%, 24%, 31% and 34% of the 102 targets, against 22% for the best plain table built from all 301 runs (paired +12.7 points [+5.9, +20.6]). File: [`results/handoff_retrieval.txt`](results/handoff_retrieval.txt).
3. **Would it fall apart on a plain store?** On a word → file table built from the same runs, the hit rate halves (34% → 17%), and a table that also keys on code anchors reaches 22%. The difference is the run node: the graph picks the few earlier runs most specifically linked to the task and takes what *they* opened, instead of summing counts in which every run's `query.py` drowns the rest. HydraDB's traversals return exactly the in-memory reference on 102 of 102 targets. File: [`results/handoff_retrieval.txt`](results/handoff_retrieval.txt).
4. **Does it hold up under load?** ⟨LOAD⟩ File: [`results/handoff_load.json`](results/handoff_load.json).

## The story in three steps

1. **We measured where agent tokens go.** In 120 logged agent runs on 40 real issues (Level 2 below), the agent opened a file of the real fix within its first step or two in every condition, and **93–96% of tokens were spent afterwards**: on neighbouring source files (21–31%), hunting tests and docs (25–31%), and reading the fix file again (18–23%) ([`results/level2_decompose.txt`](results/level2_decompose.txt)).
2. **Our first product aimed at the wrong 5%.** Bearings v1 was a learned "where to start" pack. Its retrieval was good (it ranked the real fix first 49.2% of the time against 42.0% for keyword search, on 724 issues), but live agents saved nothing: median 76.6k input tokens without it, 79.7k with it.
3. **We rebuilt it for the rest.** The tokens go to work an earlier agent has often already done: which neighbouring files matter, where the tests live, what the fix looked like. So Bearings now records that work, and hands it on.

## How it works

```
(:HTerm {key})  -[:ABOUT]->            (:HRun {key})                an entity of the run's task (symbol, path, error, word)
(:HFile {key})  -[:READ_BY]->          (:HRun)                      the run opened this file
(:HRun)         -[:READ {lines, n}]->  (:HFile)                     what it opened, which line ranges, how often
(:HRun)         -[:CONCLUDED]->        (:HFile)                     files in its final answer (or that it edited)
(:HInfo {key, date, title})                                          kept off HRun so traversals through runs return little
```

**Write side, no model call.** `src/bearings/handoff.py` reads a run's tool calls (OpenCode's JSON event log, or a Claude Code transcript) and keeps the files it opened with their `sed -n` / read ranges, and the files it concluded or edited. The task text gives the entities (regular expressions; node ids are hashes of keys, since HydraDB has no text search). Nodes and plain edges are written in batched `UNWIND` statements; `READ` edges carry line ranges, which HydraDB cannot batch, so they go one statement each in parallel. Recording all 301 runs (17k edges) takes about 6 seconds; one finished session, a fraction of a second.

**Read side: three hops, each one length-1 `algo.MSpaths` call** (so nothing is truncated per source):

1. *task → earlier runs*: from the new task's entities over `ABOUT`, and from its **code anchors** (files that define identifiers the task names, by `git grep` in the checkout) over `READ_BY`. Each run is scored by how specific its links are: rare entities and rarely opened anchors count more.
2. *runs → files*: from the top runs over `READ` and `CONCLUDED`. A file's score is the sum of its runs' scores, with a bonus when a run concluded its fix was there, discounted by how many runs open that file anyway (`query.py` is opened by everyone).
3. *tests and docs*: ranked from the same top runs, plus a third hop from the top source files to every run that opened them and on to the tests those runs opened (each run weighted by its relevance to the task). The two scores are added; this setting was chosen on the dev set. On the targets the third hop adds 1 point, within noise (see below).

```cypher
CALL algo.MSpaths({sourceLabel: 'HTerm', sourceProperty: 'key',
                   sourceValues: ['sym:formfield_callback', 'word:modelform', ...],
                   relTypes: ['ABOUT'], relDirection: 'outgoing', maxLen: 1, pathCount: 100000, pairwise: false})
YIELD path RETURN path
```

A real pack, for SWE-bench `django__django-15863` (floatformat drops precision for `Decimal`), built only from runs on issues dated before it. This one is chosen as an example where the pack held the fix: the real fix changed `django/template/defaultfilters.py` and extended `tests/template_tests/filter_tests/test_floatformat.py`. Across all 102 targets the pack holds both 34% of the time (below).

```
Handoff from 5 earlier agent runs on this repository that worked on issues near this code (Bearings). What they opened and concluded; line numbers are from their checkouts and may have shifted. Start from these; search wider only if they do not fit.
Source files:
  django/template/base.py  opened by 3 earlier runs (lines 850-950, 990-1095, 1035-1074); 1 concluded their fix belonged here
  django/template/autoreload.py  opened by 2 earlier runs (lines 1-200); 2 concluded their fix belonged here
  django/template/backends/django.py  opened by 3 earlier runs (lines 1-130)
  django/template/defaultfilters.py  opened by 1 earlier run (lines 1-260); 1 concluded their fix belonged here
  django/template/engine.py  opened by 2 earlier runs (lines 1-130)
Test files those runs opened for this code:
  tests/template_tests/filter_tests/test_filesizeformat.py  opened by 1 earlier run (lines 1-80)
  tests/template_tests/filter_tests/test_floatformat.py  opened by 1 earlier run (lines 1-120)
  tests/template_tests/test_l10n.py  opened by 1 earlier run
Docs they checked:
  docs/ref/templates/builtins.txt  opened by 1 earlier run (lines 1670-1760)
  docs/ref/settings.txt  opened by 1 earlier run (lines 2770-2800)
Earlier issues: Template changes cause dev server to reload | Make floatformat template filter independent of USE_L10N and allow forcing unlocalized for | Django 3.2.4+ autoreload breaks on empty string in TEMPLATES DIRS.
```

**Delivery.** In Claude Code, two hooks: `Stop` records the session from its transcript (`bearings handoff-stop`, no agent turn, no model call) and `UserPromptSubmit` injects the pack (`bearings handoff-hook`). `bearings handoff-hooks-config` prints the settings block. Tenant and subtenant scopes map to team and repository, so every agent on a team reads and writes one graph per repo.

## What the graph adds, as measured

**Over a plain store** (no model calls, the 102 pre-registered targets, [`results/handoff_retrieval.txt`](results/handoff_retrieval.txt)). Does the pack hold every source file of the real fix (top 5) and a test file the real fix extended (top 3)? All three are built from the same 301 recorded runs, same entities, same hot-file discount, same date rule:

| | every fix file | a real test file | both |
|---|---|---|---|
| **Bearings graph** (entities and code anchors → runs → files) | **51%** [42, 61] | **43%** [33, 53] | **34%** [25, 44] |
| Plain word → file table | 36% [26, 45] | 28% [21, 37] | 17% [10, 24] |
| Plain word + code-anchor → file table | 47% [37, 57] | 32% [24, 41] | 22% [14, 29] |

- Paired, "both": graph − word table **+17.6 points** [+8.8, +27.5]; graph − word + anchor table **+12.7** [+5.9, +20.6]. The gain is mostly in finding the test file (+10.8 [+2.9, +18.6]); for the fix files alone the anchor table comes close (+3.9 [−3.9, +11.8]).
- **Why the graph wins:** a table adds up word → file counts across all runs, so files every run opens drown the specific ones. The graph first picks the few earlier runs most specifically linked to this task (rare entities, rarely opened anchors), then takes what *those* runs opened and concluded, tests included. The run node is what keeps the evidence together.
- **What did not add anything:** the third hop (chosen source files → every run that opened them → their tests) adds +1.0 point [−3.9, +5.9] over ranking tests from the top runs directly; the hot-file discount is neutral. Both are reported, neither is claimed. Without code anchors the graph drops to 19%; without task entities, to 26%.
- **It keeps learning:** the same 102 targets with only the first 0, 25, 50, 100, 200 and 300 recorded runs available: 0%, 9%, 14%, 24%, 31%, 34% "both". (The first version of this pack, before pre-registration, managed 6% on the test file: [`results/handoff_retrieval_v0.txt`](results/handoff_retrieval_v0.txt).)
- **HydraDB returns exactly the in-memory reference** on 102 of 102 targets. The first version matched only 82 of 102 because `algo.MSpaths` returns simple paths only (it never returns *anchor file → run → the same file*), which the reference included; the read side now uses length-1 hops only.

**Over a handoff file** ([`results/handoff_accumulation.json`](results/handoff_accumulation.json)): every note costs a model call to write (302 calls for 301 notes, one first attempt having looped into 262k output tokens: 1.68M input and 747k output tokens in all, $0.077 at list price, [`runs/handoff/notes/usage.jsonl`](runs/handoff/notes/usage.jsonl)), and they pile up. After 301 recorded runs the notes total **146k tokens** in 301 files; the pack for a new task is **334 tokens** (median over the 102 targets) and was 296–334 tokens at every point from 10 to 301 runs. ⟨LIVEADDS⟩

## Go to market

- **Buyer.** Teams that run many agent sessions on one repository: planner → implementer → reviewer handoffs, and teammates' agents working near the same code. The cost they feel is each agent re-exploring what the last one found; the alternative they use today is Markdown handoff files, which cost a model call to write and pile up.
- **Wedge.** The two Claude Code hooks. Install, keep working, and the graph fills itself from sessions that already happen; nothing to write, no model calls, self-hosted HydraDB, so code never leaves the team's machines.
- **Pricing (a proposal, not tested with customers).** Free and open source for one repository on your own HydraDB. A team tier per active repository for shared scopes across machines, retention, and the dashboard; usage priced on recorded runs, not tokens, because the layer itself makes no model calls.
- **Not built.** Hosted multi-tenant service and auth; a recorder for agents other than OpenCode and Claude Code; pruning of stale records when code moves (line ranges are stored as the earlier agent saw them and may shift); any test with real teams.

## Quick start

Requirements: Linux or macOS, Docker, [uv](https://docs.astral.sh/uv/), git. The first HydraDB build takes about 15 minutes.

```bash
git clone https://github.com/hydra-db/hydradb.git          # next to this repo
git clone https://github.com/kruxarth/bearings-hydradb.git bearings && cd bearings
uv sync
scripts/start_hydradb.sh                                   # builds and starts HydraDB (data in .hydradb/)
```

Connect Claude Code: print the hooks block and paste it into your repository's `.claude/settings.json`. Every finished session is recorded; every new prompt gets the pack.

```bash
uv run bearings --team myteam --repo myrepo handoff-hooks-config
```

By hand: `bearings handoff-record <transcript.jsonl> "<task>"` records a session, `bearings handoff-pack "<task>"` prints the pack. Dashboard: `uv run bearings-web` (http://127.0.0.1:8765).

## Reproducing the numbers

Every result file is committed: `runs/handoff/` (every agent's full event log and `results.jsonl` rows, the notes and their usage), `results/handoff_*`. One command regenerates `results/RESULTS.md` and the dashboard:

```bash
uv run python bench/report.py
```

From scratch (needs the SWE-bench parquet files and a Django clone, see `scripts/prepare_data.py`, and a provider key in `../.env`):

```bash
export L2_MODEL=refuseless/deepseek-v4.1-flash-fast
uv run python bench/handoff.py memory --parallel 10      # 261 cold runs, the memory
uv run python bench/handoff.py record                    # into HydraDB, scope bench/handoff-v2
uv run python bench/handoff.py notes                     # the handoff-note baseline (one model call per run)
uv run python bench/handoff.py tune                      # dev set only
uv run python bench/handoff.py retrieval                 # no-model-call tables
uv run python bench/handoff.py run --tasks 102           # Experiment A
uv run python bench/handoff.py same --tasks 40           # Experiment B
uv run python bench/handoff_load.py --clients 20 --seconds 60
uv run python bench/report.py
```

## Limits

- **One model, one repository.** DeepSeek V4.1 Flash through OpenCode, on Django. Nothing here is a claim about Claude Code or other models; the Claude Code hooks are built and tested end to end, but not measured.
- **One run per issue and condition.** Agent runs vary a lot from run to run (2× on the same issue was seen in Level 2), so only large effects can show; intervals are reported for everything.
- **The memory is cold runs by the same model**, mistakes included. Nothing is filtered by whether a run was right, as in real use.
- **The targets were seen once** by an earlier version of the pack, before pre-registration ([`results/handoff_retrieval_v0.txt`](results/handoff_retrieval_v0.txt)). Every later design choice was made on a separate dev set ([`results/handoff_tune_dev.txt`](results/handoff_tune_dev.txt)).
- **Line ranges age.** They are stored as the earlier agent saw them; the pack says so. There is no pruning yet.
- **Money** is list-price arithmetic from token counts, never a measured bill.

## What we learned first (Bearings v1: a learned "where to start" pack)

Bearings started as a learned context layer: each finished task wrote its entities and the files its fix changed into HydraDB, and a new task got a ranked "where to start" pack from one weighted `algo.MSpaths` query plus code anchors. The full write-up of that version, its tables and its Claude Code demo are in [`results/RESULTS.md`](results/RESULTS.md) (second half) and the git history of this README.

- **Retrieval worked (Level 1).** All 850 SWE-bench Django issues replayed in date order, each answered only from what came before it, scored on the 724 from 2019-07 on. Seeded from Django's history, Bearings ranked the real fix first **49.2%** of the time against **42.0%** for keyword search (BM25), +7.2 points [+2.9, +11.6], and tied it at top 5 (76.7% vs 76.0%). From an empty graph it reached 70.7% top-5 against 55.1%, and beat the same graph frozen at the start by 6.8 points: learning as tasks arrive was real.
- **Live agents saved nothing (Level 2).** 40 SWE-bench Verified issues, OpenCode with DeepSeek V4.1 Flash, sandboxed: median total input 76.6k tokens without a pack, 79.7k with the Bearings pack, 112.1k with a dictionary pack; success 92.5% / 95.0% / 95.0%. Flat within noise.
- **Why** ([`results/level2_decompose.txt`](results/level2_decompose.txt), from those 120 logs, no model calls): the agent opened a real-fix file within its first step or two in every condition, at about 7k tokens. 93–96% of tokens came after that. An oracle pack holding the real fix was pre-registered to test the ceiling ([`bench/oracle_prereg.md`](bench/oracle_prereg.md)); it was cut short by the free tier's limit after 3 of 10 issues and is reported as incomplete in [`results/oracle_test.txt`](results/oracle_test.txt).
- **Dropped without spending agent runs:** vague-report retrieval, where keyword search beat Bearings on the same 40 issues ([`results/vague_check.txt`](results/vague_check.txt)).
- **Claude Code demo** (two issues, sonnet, not a statistic): v1 and v2 both cost more tokens than running without them (+16% to +71%), within ±20–30% run-to-run noise; Sonnet went straight to the named function.
- **Leaks found and closed** along the way, all contaminated runs discarded: `git log --all` in worktrees exposed future fixes (now single-commit snapshots, `scripts/snapshot.sh`); agents read other checkouts (now a bubblewrap sandbox, `scripts/sandbox_opencode.sh`); agents fetched the upstream fix with `curl` and web search (now no network except an allow-list proxy to the model API, `scripts/netproxy.py`, every attempt logged).

## Licence

Bearings is MIT licensed (see `LICENSE`). HydraDB is licensed under the Elastic License 2.0 and is used here unmodified, self-hosted, built from its public repository.
