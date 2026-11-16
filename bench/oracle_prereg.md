# Oracle-pack test: pre-registration (written and committed before any run)

**Question.** Could *any* "where to look" pack save tokens for this agent on these issues? If even a pack holding the real answer saves nothing, no retrieval improvement to Bearings can, and Level 2 work on retrieval stops there.

**Why.** `bench/l2_decompose.py` (results/level2_decompose.txt) shows 93–96% of Level 2 tokens are spent *after* the agent first touches a real-fix file. The agent already reads small ranges (median 70–80 lines per read).

**Agent.** The same locate-only OpenCode agent, prompt, sandbox and step cap as Level 2. Model: `opencode/deepseek-v4.1-flash-free`, the same DeepSeek V4.1 Flash on OpenCode's free tier, so no paid spend. Both conditions are run fresh on this model; nothing is compared against the earlier paid runs.

**Issues.** 10 of the 40 Level 2 issues, chosen by a fixed rule: the 40 sorted by date, every 4th starting at the first (indices 0, 4, …, 36). Nothing about earlier outcomes is used.

**Conditions** (2 runs each per issue, run at the same time):
- `none`: no pack.
- `oracle`: a pack in Bearings' exact format and wording, but filled from the real fix:
  - every source file the fix changed;
  - the pre-fix line range of each hunk;
  - the test module from the fix's test patch.

**Primary metric.** Total input tokens per run, pack included, averaged over the 2 reps per issue. Reported as:
- the median over issues of oracle/none;
- the paired bootstrap mean difference with a 95% interval.

**Decision rule, fixed now.**
- If the median ratio is ≥ 0.80 (less than a 20% saving) **or** the 95% interval of the difference includes 0: a where-to-look pack cannot reliably save tokens for this agent on well-specified issues. Report that, and do no further retrieval tuning aimed at Level 2 tokens.
- Otherwise: report the ceiling, and treat the gap between it and Bearings' measured +3% as the room retrieval could still recover.

**Secondary** (reported, not decisive):
- named every real-fix file;
- steps;
- tokens until a real-fix file is first touched.

**Caveats stated in advance.**
- 10 issues × 2 reps is small. The result can rule out a large effect, not a small one.
- The oracle uses the real fix. It is a ceiling, not a product.

**Run / resume command** (free model, no paid spend; `--skip-done` skips finished issue/condition/rep runs):

    L2_RUNS=$PWD/runs/oracle uv run python bench/level2.py run --tasks 40 --stride 4 --conditions none,oracle --reps 2 --parallel 2 --skip-done
