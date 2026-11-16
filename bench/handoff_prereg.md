# Handoff graph: pre-registration (committed before any live run on the targets)

**Question.** When the next coding agent starts on a repository where earlier agents already worked, does a pack read from a HydraDB graph of those runs (what they opened, at which lines, which tests and docs they found, what they concluded) make it cheaper to plan a fix, at equal or better success, compared with (a) starting cold and (b) reading the earlier agents' Markdown handoff notes?

**What is known before this test, stated so it cannot be quietly dropped.**
- A first version of the pack was scored once on the same 102 targets, without model calls, before this file existed (`results/handoff_retrieval_v0.txt`). It tied a plain word → file table. Those targets have therefore been seen. Every design change since was chosen on the dev set below, never on the targets.
- The pack design was fixed on the dev set (`results/handoff_tune_dev.txt`, grid printed in full). Chosen setting, by a rule stated before looking (highest share of dev issues where the pack holds every fix file and a real test file; ties broken by fix files): `top_runs=10, anchor_w=4.0, hot_q=1.0, test_mode="both"` (0.349 on 83 dev issues, against 0.193 for a plain word → file table and 0.217 for a word + anchor → file table built from the same runs). The grid is flat: many settings score 0.31–0.35, within noise for 83 issues, so the choice matters little. The test hop through chosen sources (`via`) is part of the chosen `both` mode; on its own it did not beat ranking tests directly.

**Agent and model.** The locate-and-plan OpenCode agent (`bench/handoff.py`, `PROMPT`), OpenCode 1.18.35, step cap 25, timeout 900 s, in the bubblewrap sandbox with no network except an allow-list proxy to the model API (`scripts/netproxy.py`) and a history-free snapshot of Django at the issue's commit (`scripts/snapshot.sh`). Model: DeepSeek V4.1 Flash, `deepseek-v4.1-flash-fast` through the Refuseless OpenAI-compatible API. **Every condition of every experiment below runs fresh on this model and provider.** No token count is compared with runs from another model or provider.

**Task.** Name the source files to edit (`FILES:`, at most 5) and the existing test file where the regression test belongs (`TESTS:`, at most 3). Success, checked in code: every source file of the real fix is in `FILES`, and at least one test file that the real fix extended (and that exists at the issue's commit) is in `TESTS`.

**Memory (what earlier agents did).** Fixed date rule: one cold run on every SWE-bench Django issue dated 2021-01-01 to 2022-06-30 (261 issues), same agent, model and prompt. The graph also records the 40 Level 2 runs (dated 2022-07 to 2023-07, DeepSeek's own API): only what they opened and concluded is used, never their token counts. **Date rule:** a target may use only runs on issues dated strictly before it; enforced in `earlier()` and in the pack's `allowed` set, and the same rule selects which notes are placed in the notes condition.

**Handoff notes (the baseline people use).** One model call per recorded run (same model, `NOTE_PROMPT`: under 300 words, files and line ranges, tests and docs, what was ruled out, the conclusion), from the run's transcript. The tokens of these calls are logged (`runs/handoff/notes/usage.jsonl`) and reported as a cost the graph does not have.

## Experiment A: cross-task (primary)
- **Targets (fixed rule):** every SWE-bench Django issue dated from 2022-07-01 with no recorded run whose real fix changes a source file and extends an existing test file (`pool()`, 102 issues), in date order. All 102, one run per condition. A second repetition only if time allows, decided before seeing any result of the first.
- **Conditions:**
  - `cold`: nothing.
  - `notes`: the handoff notes of every allowed earlier run, as one Markdown file per session in `/work/repo/HANDOFF/`; the prompt says they are there and that they were written for other issues.
  - `graph`: the pack, built through HydraDB from the allowed runs, pasted into the prompt.
- **Primary metric:** total input tokens per run (uncached input + cache read + cache write, summed over OpenCode's per-step reports), which includes the pack and any notes the agent reads. Paired by issue. Reported as the median over issues of graph/cold and graph/notes, and the paired bootstrap mean difference with a 95% interval (2,000 resamples).
- **Decision rule (fixed now):** the graph is said to save tokens against a condition only if the 95% interval of the paired mean difference lies entirely below 0 **and** the graph's success rate is not lower than that condition's (point estimates). If the interval includes 0, the result is reported as a tie. If the graph is cheaper but less successful, no saving is claimed.
- **Secondary:** success rate with 95% intervals, source-file and test-file success separately, steps, wall time, and the note-writing tokens amortised per run.

## Experiment B: same task (the simple handoff)
- **Issues (fixed rule):** the 40 latest memory issues whose fix extends an existing test file (`same_tasks()`).
- **Conditions** (a second agent on the same issue, after the memory run): `cold` (a second cold run), `notes` (only that run's own note), `graph` (a pack built from that run's own record only).
- Same metric and decision rule as A. Expected beforehand: the largest saving against cold, and the note and the graph close to each other.

## Exclusions
- A run is excluded if it was rate-limited after its retries or never started (0 steps). An issue with any excluded condition is dropped from that experiment's paired comparison; counts are reported.
- Timeouts count as failures and their tokens count.
- Runs whose tool calls try to reach outside the sandbox (`outside_access`) are counted normally and their number is reported.

## No-model-call results (reported alongside)
- Retrieval on the 102 targets: does the pack hold every fix file (top 5) and a real test file (top 3)? Against a plain word → file table built from the same runs, an ablation (no anchors, no entities, no third hop, no hot-file discount), and a learning curve over the number of recorded runs (0, 25, 50, 100, 200, 300), with bootstrap intervals. HydraDB's answer against the in-memory reference.
- Accumulation: as runs pile up, total size of the handoff notes against the size of the pack.
- Load: 20 concurrent clients requesting packs for 60 s while runs are being recorded.

## Caveats stated in advance
- One repetition per condition; agent runs vary a lot (2× between runs of one issue was seen in Level 2), so only a large effect can show.
- The memory runs are cold runs by the same model, so their mistakes are recorded too. Nothing in the graph is filtered by whether a run was right.
- DeepSeek through OpenCode only. Nothing here is a claim about Claude Code.

**Commands**

    L2_MODEL=refuseless/deepseek-v4.1-flash-fast uv run python bench/handoff.py memory --parallel 14
    uv run python bench/handoff.py record && uv run python bench/handoff.py notes
    L2_MODEL=refuseless/deepseek-v4.1-flash-fast uv run python bench/handoff.py run --tasks 102 --parallel 14
    L2_MODEL=refuseless/deepseek-v4.1-flash-fast uv run python bench/handoff.py same --tasks 40 --parallel 14
