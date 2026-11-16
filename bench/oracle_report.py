"""Analysis of the oracle-pack ceiling test, exactly as pre-registered in
bench/oracle_prereg.md. Reads runs/oracle/results.jsonl.

  uv run python bench/oracle_report.py     # writes results/oracle_test.txt
"""
from __future__ import annotations

import json
import random
import statistics as st
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "runs" / "oracle" / "results.jsonl"


def boot_ci(diffs: list[float], n: int = 10000, seed: int = 0) -> tuple[float, float]:
    rnd = random.Random(seed)
    ms = sorted(st.mean(rnd.choices(diffs, k=len(diffs))) for _ in range(n))
    return ms[int(0.025 * n)], ms[int(0.975 * n)]


def main() -> None:
    rows = [json.loads(x) for x in open(RES)]
    rows = [r for r in rows if not r["rate_limited"]]
    by = defaultdict(lambda: defaultdict(list))
    for r in rows:
        by[r["id"]][r["condition"]].append(r)
    ids = sorted(i for i, c in by.items() if c["none"] and c["oracle"])
    out = []
    w = out.append
    w("Oracle-pack ceiling test (pre-registered: bench/oracle_prereg.md)")
    w(f"Model: {rows[0]['model']}. Issues with both conditions: {len(ids)}; "
      f"runs: {sum(len(by[i]['none']) + len(by[i]['oracle']) for i in ids)} (rate-limited runs excluded: "
      f"{sum(1 for x in open(RES) if json.loads(x)['rate_limited'])}).\n")

    def m(rs, k):
        vals = [r[k] for r in rs if r[k] is not None]
        return st.mean(vals) if vals else None

    w(f"{'issue':24} {'none tokens':>12} {'oracle tokens':>14} {'ratio':>6} {'none steps':>11} {'oracle steps':>13}")
    ratios, diffs = [], []
    for i in ids:
        n, o = m(by[i]["none"], "total_input"), m(by[i]["oracle"], "total_input")
        ratios.append(o / n)
        diffs.append(o - n)
        w(f"{i:24} {n:12,.0f} {o:14,.0f} {o / n:6.2f} {m(by[i]['none'], 'steps'):11.1f} {m(by[i]['oracle'], 'steps'):13.1f}")
    lo, hi = boot_ci(diffs)
    med = st.median(ratios)
    w(f"\nPrimary: median oracle/none ratio {med:.2f}; mean difference {st.mean(diffs):+,.0f} tokens "
      f"[{lo:+,.0f}, {hi:+,.0f}] (paired bootstrap, 95%).")
    for c in ("none", "oracle"):
        rs = [r for i in ids for r in by[i][c]]
        tfg = [r["tokens_to_first_gold"] for r in rs if r["tokens_to_first_gold"] is not None]
        w(f"Secondary, {c}: named every real-fix file {st.mean(r['all'] for r in rs):.0%}; "
          f"median steps {st.median(r['steps'] for r in rs):.0f}; "
          f"median tokens until a real-fix file is touched {st.median(tfg) if tfg else float('nan'):,.0f}")
    saves = med < 0.80 and hi < 0
    if len(ids) < 10:
        w(f"\nINCOMPLETE: {len(ids)} of the 10 pre-registered issues finished (OpenCode's free usage limit was "
          "reached). The decision rule is not applied to a partial sample; resume with the command in "
          "bench/oracle_prereg.md when the free quota resets.")
        (ROOT / "results" / "oracle_test.txt").write_text("\n".join(out) + "\n")
        print("\n".join(out))
        return
    w("\nDecision (rule fixed before the runs): " + (
        f"the oracle saves tokens reliably (median ratio {med:.2f} < 0.80 and the interval excludes 0). "
        "That is the ceiling; Bearings' Level 2 result (+3%) leaves that room for retrieval to recover."
        if saves else
        f"the oracle does NOT reliably save tokens (median ratio {med:.2f}; interval "
        f"[{lo:+,.0f}, {hi:+,.0f}]). Even a pack holding the real answer cannot reliably cut this agent's "
        "tokens on these issues, so no retrieval improvement to Bearings can; Level 2 retrieval tuning stops here."))
    w("Caveat: 10 issues x 2 runs; rules out a large effect, not a small one. The oracle uses the real fix: a ceiling, not a product.")
    (ROOT / "results" / "oracle_test.txt").write_text("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
