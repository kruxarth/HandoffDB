"""Build results/RESULTS.md and results/report.html from the committed result files.

  uv run python bench/report.py

Every number in the README comes from this script's output.
"""

from __future__ import annotations

import html
import re
import json
import math
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bench"))
from summarize import CONDS, ci, paired_diff  # noqa: E402

RES = ROOT / "results"
SIDE = {"without": "Without Bearings", "without-2": "Without Bearings (rerun)", "with": "Bearings v1 via MCP tool",
        "hook-v1": "Bearings v1 via prompt hook", "hook": "Bearings v2 via hooks (graph + code anchors)"}
LABEL = {"bm25": "Keyword search (BM25)", "dict": "Dictionary (no graph)", "bearings-1": "Bearings, one hop",
         "bearings": "Bearings, full", "frozen": "Frozen graph"}
COLOR = {"bearings": "--series-1", "dict": "--series-2", "bearings-1": "--series-3", "frozen": "--series-4",
         "bm25": "--series-5"}
METRICS = ("hit@1", "hit@3", "hit@5", "recall@5")


def rows(path: Path, split: str | None = "test", subset: str | None = None) -> list[dict]:
    if not path.exists():
        return []
    rs = [json.loads(line) for line in open(path)]
    fz = path.with_name(path.stem + "_frozen.jsonl")  # frozen condition run as its own process
    if fz.exists():
        frozen = {r["id"]: r for r in map(json.loads, open(fz))}
        for r in rs:
            if r["id"] in frozen:
                r["metrics"]["frozen"] = frozen[r["id"]]["metrics"]
                r["ranked"]["frozen"] = frozen[r["id"]]["ranked"]
    if split:
        rs = [r for r in rs if r["split"] == split]
    if subset:
        rs = [r for r in rs if r.get(subset)]
    return rs


def fmt(t) -> str:
    return f"{t[0]:.3f} [{t[1]:.3f}, {t[2]:.3f}]"


def l1_table(rs: list[dict]) -> str:
    out = ["| Condition | n | hit@1 | hit@3 | hit@5 | recall@5 |", "|---|---|---|---|---|---|"]
    for c in CONDS:
        sub = [r for r in rs if c in r["metrics"]]
        if not sub:
            continue
        out.append(f"| {LABEL[c]} | {len(sub)} | " + " | ".join(fmt(ci([r['metrics'][c][m] for r in sub])) for m in METRICS) + " |")
    return "\n".join(out)


def diffs(rs: list[dict]) -> str:
    out = ["| Comparison (paired, same tasks) | Δ hit@1 | Δ hit@5 |", "|---|---|---|"]
    for a, b in [("bearings", "dict"), ("bearings", "bearings-1"), ("bearings", "frozen"), ("bearings", "bm25"),
                 ("dict", "bm25")]:
        sub = [r for r in rs if a in r["metrics"] and b in r["metrics"]]
        if not sub:
            continue
        cells = []
        for m in ("hit@1", "hit@5"):
            d = paired_diff([r["metrics"][a][m] for r in sub], [r["metrics"][b][m] for r in sub])
            cells.append(f"{d[0]:+.3f} [{d[1]:+.3f}, {d[2]:+.3f}]")
        out.append(f"| {LABEL[a]} − {LABEL[b]} (n={len(sub)}) | " + " | ".join(cells) + " |")
    return "\n".join(out)


def where_differ(rs: list[dict], a: str, b: str, m: str = "hit@5") -> tuple[int, int]:
    win = sum(1 for r in rs if b in r["metrics"] and r["metrics"][a][m] > r["metrics"][b][m])
    loss = sum(1 for r in rs if b in r["metrics"] and r["metrics"][a][m] < r["metrics"][b][m])
    return win, loss


def curve(path: Path, metric: str = "hit@5", window: int = 100) -> dict[str, list[tuple[int, float]]]:
    """Rolling mean of metric over the task stream (dev + test), x = tasks learned."""
    rs = rows(path, split=None)
    out = {}
    for c in CONDS:
        pts = [(r["learned_tasks"], r["metrics"][c][metric]) for r in rs if c in r["metrics"]]
        series = []
        for i in range(window, len(pts) + 1, 10):
            chunk = pts[i - window:i]
            series.append((chunk[-1][0], sum(v for _, v in chunk) / window))
        if series:
            out[c] = series
    return out


def svg_lines(series: dict, title: str, ylab: str, cid: str, ymin=None, ymax=None) -> str:
    W, H, L, R, T, B = 760, 360, 52, 205, 34, 44
    xs = [x for s in series.values() for x, _ in s]
    ys = [y for s in series.values() for _, y in s]
    if not xs:
        return "<p>(no data yet)</p>"
    x0, x1 = min(xs), max(xs)
    lo = ymin if ymin is not None else math.floor(min(ys) * 10) / 10
    hi = ymax if ymax is not None else math.ceil(max(ys) * 10) / 10
    sx = lambda x: L + (x - x0) / max(1, x1 - x0) * (W - L - R)  # noqa: E731
    sy = lambda y: T + (hi - y) / max(1e-9, hi - lo) * (H - T - B)  # noqa: E731
    parts = [f'<svg viewBox="0 0 {W} {H}" class="chart" role="img" aria-label="{html.escape(title)}" data-chart="{cid}">']
    step = 0.1 if hi - lo > 0.3 else 0.05
    y = lo
    while y <= hi + 1e-9:
        parts.append(f'<line x1="{L}" x2="{W - R}" y1="{sy(y):.1f}" y2="{sy(y):.1f}" class="grid"/>'
                     f'<text x="{L - 8}" y="{sy(y) + 4:.1f}" class="tick" text-anchor="end">{y:.2f}</text>')
        y += step
    for xv in range(0, x1 + 1, 100):
        if xv >= x0:
            parts.append(f'<text x="{sx(xv):.1f}" y="{H - B + 18}" class="tick" text-anchor="middle">{xv}</text>')
    parts.append(f'<text x="{(L + W - R) / 2}" y="{H - 6}" class="axis" text-anchor="middle">tasks learned</text>')
    parts.append(f'<text x="12" y="{T - 16}" class="axis">{html.escape(ylab)}</text>')
    labels = []
    for c, s in series.items():
        pts = " ".join(f"{sx(x):.1f},{sy(y):.1f}" for x, y in s)
        parts.append(f'<polyline points="{pts}" fill="none" stroke="var({COLOR[c]})" stroke-width="2" '
                     f'stroke-linejoin="round" stroke-linecap="round"><title>{LABEL[c]}</title></polyline>')
        labels.append([sy(s[-1][1]), c, s[-1][1]])
    labels.sort()
    for i in range(1, len(labels)):  # de-collide end labels
        labels[i][0] = max(labels[i][0], labels[i - 1][0] + 16)
    for yv, c, v in labels:
        parts.append(f'<text x="{W - R + 8}" y="{yv + 4:.1f}" class="dlabel">{LABEL[c]} {v:.2f}</text>')
    parts.append(f'<line class="xhair" x1="0" x2="0" y1="{T}" y2="{H - B}" visibility="hidden"/>')
    parts.append(f'<rect class="hit" x="{L}" y="{T}" width="{W - L - R}" height="{H - T - B}" fill="transparent"/>')
    parts.append("</svg>")
    data = {c: s for c, s in series.items()}
    parts.append(f'<script type="application/json" id="data-{cid}">{json.dumps({"series": data, "labels": LABEL, "x0": x0, "x1": x1, "L": L, "R": R, "W": W})}</script>')
    return "".join(parts)


def svg_bars(groups: list[tuple[str, list[tuple[str, float, float, float]]]], cid: str) -> str:
    """Grouped horizontal bars with CI whiskers. groups: (group label, [(cond, mean, lo, hi)])."""
    W, rowh, L = 720, 22, 210
    n = sum(len(g) + 1 for _, g in groups)
    H = n * rowh + 30
    sx = lambda v: L + v * (W - L - 60)  # noqa: E731
    parts = [f'<svg viewBox="0 0 {W} {H}" class="chart" role="img" aria-label="hit rates by condition">']
    y = 10
    for gl, items in groups:
        parts.append(f'<text x="0" y="{y + 14}" class="glabel">{html.escape(gl)}</text>')
        y += rowh
        for c, m, lo, hi in items:
            parts.append(f'<text x="{L - 8}" y="{y + 12}" class="tick" text-anchor="end">{LABEL[c]}</text>'
                         f'<rect x="{L}" y="{y + 2}" width="{max(0, sx(m) - L):.1f}" height="14" rx="4" fill="var({COLOR[c]})">'
                         f'<title>{LABEL[c]} {gl}: {m:.3f} (95% CI {lo:.3f}-{hi:.3f})</title></rect>'
                         f'<line x1="{sx(lo):.1f}" x2="{sx(hi):.1f}" y1="{y + 9}" y2="{y + 9}" class="whisker"/>'
                         f'<text x="{sx(hi) + 6:.1f}" y="{y + 13}" class="tick">{m:.2f}</text>')
            y += rowh
    for v in (0, 0.25, 0.5, 0.75, 1.0):
        parts.append(f'<line x1="{sx(v):.1f}" x2="{sx(v):.1f}" y1="6" y2="{H - 20}" class="grid"/>'
                     f'<text x="{sx(v):.1f}" y="{H - 6}" class="tick" text-anchor="middle">{v:.2f}</text>')
    parts.append("</svg>")
    return "".join(parts)


L2_LAB = {"none": "No memory", "dict": "Dictionary pack in prompt", "anchors": "Code anchors in prompt",
          "bearings": "Bearings pack in prompt", "bearings-mcp": "Bearings via MCP tool (v1)"}
L2_ORDER = ["none", "dict", "anchors", "bearings", "bearings-mcp"]


def level2() -> tuple[str, dict]:
    """Markdown + structured stats. A run counts unless it was rate-limited or the
    agent never ran (infrastructure failure); timeouts count as failures."""
    p = ROOT / "runs" / "level2" / "results.jsonl"
    if not p.exists():
        return "(Level 2 not run yet)", {}
    rs = [json.loads(line) for line in open(p)]
    latest: dict[tuple[str, str], dict] = {}
    for r in rs:
        latest[(r["id"], r["condition"])] = r
    rs = list(latest.values())
    valid = [r for r in rs if not r["rate_limited"] and r["steps"] > 0]
    excluded = len(rs) - len(valid)
    conds = [c for c in L2_ORDER if any(r["condition"] == c for r in valid)]
    main = [c for c in ("none", "dict", "bearings") if c in conds]
    ids = set.intersection(*[{r["id"] for r in valid if r["condition"] == c} for c in main]) if main else set()
    by = {c: {r["id"]: r for r in valid if r["condition"] == c} for c in conds}
    # extra conditions (ablations, pilots) are paired with no memory on their own, smaller task sets
    sub_ids = {c: (ids if c in main else ids & set(by[c])) for c in conds}
    timeouts = sum(1 for r in valid if r["exit"] == "timeout" and r["id"] in ids)
    escapes = sum(1 for r in valid if r.get("outside_access") and r["id"] in ids)
    model = valid[0]["model"] if valid else "?"
    out = [f"Model: `{model}` via OpenCode 1.18.35, step cap 25, sandboxed (no network except the model API). "
           f"Paired tasks (a counted run in no memory, dictionary and Bearings): {len(ids)}; the code-anchors-only ablation ran on the first tasks only (budget). Runs excluded (rate-limited or the agent never "
           f"started): {excluded} of {len(rs)}. Timeouts counted as failures: {timeouts}. Runs where the agent tried to "
           f"reach outside the sandbox (blocked, counted normally): {escapes}.", "",
           "| Condition | success (all gold files named) | hit (≥1 gold file) | total input tokens, median [IQR] | tokens until first real-fix file opened, median | uncached input | output+reasoning | tool calls | wall s |",
           "|---|---|---|---|---|---|---|---|---|"]
    stats: dict = {"conds": {}, "n": len(ids), "excluded": excluded, "total": len(rs), "timeouts": timeouts,
                   "escapes": escapes, "model": model}
    for c in conds:
        rr = [by[c][i] for i in sorted(sub_ids[c])]
        if not rr:
            continue
        ti = sorted(r["total_input"] for r in rr)
        q = statistics.quantiles(ti, n=4) if len(ti) >= 4 else [ti[0], statistics.median(ti), ti[-1]]
        st = {"succ": ci([r["all"] for r in rr]), "hit": ci([r["hit"] for r in rr]), "median_in": statistics.median(ti),
              "q1": q[0], "q3": q[2], "mean_in": sum(ti) / len(ti), "n": len(rr),
              "tools": round(statistics.median([r["tool_calls"] for r in rr])),
              "wall": round(statistics.median([r["wall_s"] for r in rr])), "ratio": None, "dsucc": None, "dtok": None}
        if c != "none" and "none" in conds:
            b = [by["none"][i] for i in sorted(sub_ids[c])]
            st["dsucc"] = paired_diff([x["all"] for x in rr], [y["all"] for y in b])
            st["dtok"] = paired_diff([x["total_input"] for x in rr], [y["total_input"] for y in b])
            st["ratio"] = statistics.median([x["total_input"] / max(1, y["total_input"]) for x, y in zip(rr, b)])
        ftg = [r["tokens_to_first_gold"] if r.get("tokens_to_first_gold") is not None else r["total_input"] for r in rr]
        st["first_gold"] = statistics.median(ftg)
        st["never_gold"] = sum(1 for r in rr if r.get("tokens_to_first_gold") is None)
        if c != "none" and "none" in conds:
            fb = [y["tokens_to_first_gold"] if y.get("tokens_to_first_gold") is not None else y["total_input"] for y in b]
            st["first_gold_ratio"] = statistics.median([x / max(1, y) for x, y in zip(ftg, fb)])
            st["dfirst"] = paired_diff(ftg, fb)
        stats["conds"][c] = st
        out.append(f"| {L2_LAB[c]}{'' if c in main else f' (n={len(rr)}, ablation)'} | {fmt(st['succ'])} | {fmt(st['hit'])} | {st['median_in']:,.0f} [{q[0]:,.0f}–{q[2]:,.0f}] | "
                   f"{st['first_gold']:,.0f} ({st['never_gold']} never) | "
                   f"{statistics.median([r['tokens']['input'] for r in rr]):,.0f} | "
                   f"{statistics.median([r['tokens']['output'] + r['tokens']['reasoning'] for r in rr]):,.0f} | "
                   f"{st['tools']} | {st['wall']} |")
    if "none" in conds and ids:
        out += ["", "| Paired difference vs no memory | Δ success | Δ total input tokens (mean, 95% CI) | median per-task ratio | "
                "Δ tokens until first real-fix file (mean, 95% CI) | median per-task ratio |",
                "|---|---|---|---|---|---|"]
        for c in conds:
            if c == "none" or c not in stats["conds"]:
                continue
            st = stats["conds"][c]
            ds, dt = st["dsucc"], st["dtok"]
            df_ = st["dfirst"]
            out.append(f"| {L2_LAB[c]} | {ds[0]:+.3f} [{ds[1]:+.3f}, {ds[2]:+.3f}] | {dt[0]:+,.0f} [{dt[1]:+,.0f}, {dt[2]:+,.0f}] | "
                       f"{st['ratio']:.2f} | {df_[0]:+,.0f} [{df_[1]:+,.0f}, {df_[2]:+,.0f}] | {st['first_gold_ratio']:.2f} |")
    return "\n".join(out), stats


def reach_section() -> str:
    p = RES / "second_hop_reach.json"
    if not p.exists():
        return ""
    d = json.loads(p.read_text())
    lines = ["| Seed | gold source files | 1 hop from a task entity | reachable only by 2nd hop | unreachable | 2nd-hop-only that reached top 5 |",
             "|---|---|---|---|---|---|"]
    for seed, s in d.items():
        lines.append(f"| {seed} | {s['gold']} | {s['hop1']} | {s['hop2only']} | {s['none']} | {s['hop2only_in_pack']} |")
    return "\n".join(lines)


L1_ORDER = ["bearings", "bearings-1", "graph", "anchors", "bm25", "dict", "frozen"]
LABEL.update({"anchors": "Code anchors only", "graph": "Learned graph only", "bearings": "Bearings (graph + anchors)",
              "bearings-1": "Bearings, no second hop", "frozen": "Bearings, frozen graph"})
COLORS = {"bearings": "s1", "bm25": "s2", "graph": "s3", "frozen": "s4", "dict": "s5", "anchors": "s7", "bearings-1": "s6",
          "l2:none": "s4", "l2:dict": "s5", "l2:anchors": "s7", "l2:bearings": "s1", "l2:bearings-mcp": "s3"}
SEED_TITLE = {"history": "Seeded from history", "tasks": "Empty start"}
SEED_LONG = {"history": "Seeded from Django's commit history, then learning from the task stream",
             "tasks": "Learning from the task stream only (a team starting from an empty graph)"}


def latency_text(lat: list[float]) -> str:
    busy = f"During this benchmark (three runs sharing one HydraDB): p50 {lat[len(lat)//2]:.0f} ms, p95 {lat[int(len(lat)*.95)]:.0f} ms."
    p = RES / "latency.json"
    if not p.exists():
        return busy
    q = json.loads(p.read_text())
    return (f"Quiet machine, {q['graph_events']:,}-event graph: whole pack p50 {q['context_pack_ms']['p50']:.0f} ms "
            f"(HydraDB path query {q['hydradb_path_query_ms']['p50']:.0f} ms, code anchors {q['code_anchors_ms']['p50']:.0f} ms). "
            + busy)


def seed_block(seed: str) -> tuple[list[str], dict]:
    path = RES / f"level1_{seed}.jsonl"
    test = rows(path)
    if not test:
        return [], {}
    ver = rows(path, subset="verified")
    md = [f"## Level 1, {SEED_LONG[seed]}", "", f"Test split: SWE-bench Django tasks from 2019-07-01 on (n={len(test)}). "
          f"Retrieval only, no model calls.", "", l1_table(test), "", diffs(test), "",
          f"SWE-bench Verified subset (n={len(ver)}):", "", l1_table(ver), ""]
    lat = sorted(r["latency_full_ms"] for r in test)
    agree = [r["db_matches_reference"] for r in test if "db_matches_reference" in r]
    tc = [r["test_cmd_hit"] for r in test]
    pc = sorted(r["pack_chars"] for r in test)
    w2, l2 = where_differ(test, "bearings", "bearings-1")
    facts = [
        {"title": "Query latency", "text": latency_text(lat)},
        {"title": "Second hop", "text": f"Adding the co-changed-file hop changed hit@5 on {w2 + l2} of {len(test)} tasks "
                                        f"({w2} better, {l2} worse). Measured, and close to zero."},
        {"title": "Test command", "text": f"The suggested test command names the module where the real fix's tests live on "
                                          f"{sum(tc)/len(tc):.0%} of tasks."},
        {"title": "Database vs reference", "text": f"HydraDB's ranking equals an in-memory reference implementation of the same "
                                                   f"query on {sum(agree)}/{len(agree)} tasks (ties broken differently on the rest). "
                                                   f"Pack size: median {pc[len(pc)//2]//4} tokens."},
    ]
    md += [f"- {f['title']}: {re.sub('<[^>]+>', '', f['text'])}" for f in facts] + [""]
    conds = {}
    for c in CONDS:
        sub = [r for r in test if c in r["metrics"]]
        if sub:
            conds[c] = {m: ci([r["metrics"][c][m] for r in sub]) for m in METRICS}
    dd = []
    reading = {("bearings", "bm25"): "vs keyword search over past tasks", ("bearings", "graph"): "what the code anchors add",
               ("bearings", "anchors"): "what the learned graph adds", ("bearings", "frozen"): "what learning as tasks arrive adds",
               ("bearings", "bearings-1"): "what the second hop adds", ("bearings", "dict"): "vs a plain word-to-file table"}
    for (a, b), txt in reading.items():
        sub = [r for r in test if a in r["metrics"] and b in r["metrics"]]
        if not sub:
            continue
        d = {m: paired_diff([r["metrics"][a][m] for r in sub], [r["metrics"][b][m] for r in sub]) for m in ("hit@1", "hit@5")}
        dd.append({"label": f"{LABEL[a]} − {LABEL[b]}", "reading": txt, "hl": b in ("bm25", "frozen"), **d})
    curves = {}
    for m in ("hit@1", "hit@3", "hit@5"):
        cv = curve(path, m)
        curves[m] = {c: [[x, round(y, 4)] for x, y in cv[c]] for c in ("bearings", "graph", "bm25", "frozen") if c in cv}
    return md, {"title": SEED_TITLE[seed], "n": len(test), "test_from": "2019-07-01", "conds": conds, "diffs": dd,
                "curves": curves, "facts": facts, "lat_p50": lat[len(lat)//2]}


def main() -> None:
    md = ["# Results", "", "Generated by `uv run python bench/report.py` from the files in `results/` and `runs/level2/`. "
          "Brackets are 95% bootstrap confidence intervals. hit@k = the real fix changed at least one of the top k suggested "
          "source files.", ""]
    data: dict = {"level1": {}, "labels": dict(LABEL), "colors": COLORS, "l1_order": L1_ORDER,
                  "curve_hidden": [], "demo": [], "notes": [], "pills": [], "kpis": []}
    for seed in ("history", "tasks"):
        m, d = seed_block(seed)
        md += m
        if d:
            data["level1"][seed] = d
    rs = reach_section()
    if rs:
        md += ["## Does the second hop reach files the first hop cannot?", "",
               "Measured on the dev split (graph only): for each gold source file, is it linked in one hop from any of the task's "
               "entities, only through a CO_CHANGED hop, or not at all?", "", rs, ""]
    l2md, l2 = level2()
    md += ["## Level 2, live agent runs: tokens to locate the right files", "",
           "The agent (DeepSeek V4.1 Flash through OpenCode) reads the issue, explores a history-free snapshot of the repo "
           "at the issue's commit, and names the files it would edit. Success is checked in code against the real fix. "
           "Token counts are OpenCode's per-step usage, summed, and include the context pack. Packs come from a graph built "
           "only from events before 2022-07-01; tasks are SWE-bench Verified issues from after it.", "", l2md, ""]
    demo = [json.loads(p.read_text()) for p in sorted((RES / "claude_demo").glob("*.json"))] \
        if (RES / "claude_demo").exists() else []
    demo = sorted((d for d in demo if "side" in d), key=lambda d: (d["task"], list(SIDE).index(d["side"])))
    if demo:
        md += ["## Claude Code demo (a few tasks, not a statistic)", "",
               "Headless Claude Code (`claude -p`, sonnet) fixing the issue end to end. Usage is Claude Code's own `usage` "
               "block from the final result event; total input = uncached input + cache write + cache read. The dollar "
               "column is Claude Code's list-price arithmetic, not measured spend (these runs used a Pro plan).", "",
               "| Task | Side | total input | vs without | uncached input | cache write | cache read | output | turns | tool calls | right files | list-price arithmetic |",
               "|---|---|---|---|---|---|---|---|---|---|---|---|"]
        base = {d["task"]: d["total_input"] for d in demo if d["side"] == "without"}
        for d in demo:
            rel = round((d["total_input"] / base[d["task"]] - 1) * 100) if d["side"] != "without" and d["task"] in base else None
            md.append(f"| {d['task']} | {SIDE.get(d['side'], d['side'])} | {d['total_input']:,} | {'' if rel is None else f'{rel:+d}%'} | "
                      f"{d['input_tokens']:,} | {d['cache_creation_input_tokens']:,} | {d['cache_read_input_tokens']:,} | "
                      f"{d['output_tokens']:,} | {d['num_turns']} | {d['tool_calls']} | {d['correct_files']} | ${d['list_price_usd']:.2f} |")
            data["demo"].append({"task": d["task"].replace("django__", ""), "side": d["side"], "label": SIDE.get(d["side"], d["side"]),
                                 "total_input": d["total_input"], "rel": rel, "num_turns": d["num_turns"],
                                 "tool_calls": d["tool_calls"], "output_tokens": d["output_tokens"], "correct": d["correct_files"]})
        md.append("")
    (RES / "RESULTS.md").write_text("\n".join(md))
    dashboard(data, l2)
    print("\n".join(md))


def dashboard(data: dict, l2: dict) -> None:
    h = data["level1"].get("history") or next(iter(data["level1"].values()), None)
    t = data["level1"].get("tasks")
    data["labels"].update({f"l2:{k}": v for k, v in L2_LAB.items()})
    data["pills"] = ["Self-hosted HydraDB (open source)", "One weighted path query per task", "No model calls",
                     "Every number from committed result files"]
    k = []
    if h:
        b, kw = h["conds"]["bearings"], h["conds"]["bm25"]
        d1 = (b["hit@1"][0] - kw["hit@1"][0]) * 100
        k.append({"label": "Right file ranked first", "value": f"{b['hit@1'][0]:.0%}",
                  "delta": f"{d1:+.0f} pts", "dir": "up" if d1 > 0 else "down",
                  "sub": f"vs {kw['hit@1'][0]:.0%} for keyword search · {h['n']} real Django issues"})
        k.append({"label": "Real fix in top 5", "value": f"{b['hit@5'][0]:.0%}", "delta": "", "dir": "flat",
                  "sub": f"graph alone {h['conds']['graph']['hit@5'][0]:.0%} · code anchors alone {h['conds']['anchors']['hit@5'][0]:.0%}"})
    if t:
        b, kw = t["conds"]["bearings"], t["conds"]["bm25"]
        k.append({"label": "Starting from an empty graph", "value": f"{b['hit@5'][0]:.0%}",
                  "delta": f"{(b['hit@5'][0] - kw['hit@5'][0]) * 100:+.0f} pts", "dir": "up",
                  "sub": f"top-5 hit rate vs {kw['hit@5'][0]:.0%} for keyword search"})
    c = l2.get("conds", {})
    if "bearings" in c and "none" in c:
        r = c["bearings"]
        k.append({"label": "Tokens to locate, live agents", "value": f"{r['ratio']:.2f}×",
                  "delta": f"{r['dsucc'][0] * 100:+.0f} pts success",
                  "dir": "flat" if abs(r["dsucc"][0]) < 0.005 else "up" if r["dsucc"][0] > 0 else "down",
                  "sub": f"median per-task ratio vs no memory · {l2['n']} paired tasks"})
    elif (RES / "latency.json").exists():
        q = json.loads((RES / "latency.json").read_text())
        k.append({"label": "Context pack latency", "value": f"{q['context_pack_ms']['p50']:.0f} ms", "delta": "", "dir": "flat",
                  "sub": f"median on a laptop · HydraDB path query {q['hydradb_path_query_ms']['p50']:.0f} ms"})
    data["kpis"] = k
    data["l1_intro"] = (f"Every SWE-bench task on Django ({sum(1 for _ in open(ROOT / 'data/derived/tasks.jsonl'))} issues, 2015–2023) "
                        "replayed in date order. For each issue Bearings suggests five files using only what it learned "
                        "<em>before</em> that issue, then learns from the real fix. Scored on the 724 issues from 2019-07 on; "
                        "tuning used only the earlier 126. <b>The graph learns from the dataset's own real fixes</b>, as a team's "
                        "graph would learn from its merged work.")
    if c:
        data["level2"] = {
            "intro": (f"A coding agent (DeepSeek V4.1 Flash through OpenCode) gets a real issue and a history-free snapshot "
                      f"of Django at that issue's commit, explores, and names the files it would change. {l2['n']} SWE-bench "
                      f"Verified issues from after the graph's cutoff, each run once in every condition. Token counts are "
                      f"OpenCode's own usage reports and include the context pack."),
            "warn": (f"Excluded: {l2['excluded']} of {l2['total']} runs (rate-limited, or the agent never started). "
                     f"Timeouts count as failures ({l2['timeouts']}). The sandbox has no network except the model API; "
                     f"{l2['escapes']} runs tried to reach outside it (web, other checkouts) and were blocked."),
            "order": [f"l2:{x}" for x in L2_ORDER if x in c],
            "conds": {f"l2:{x}": v for x, v in c.items()},
            "cap": "Paired: the same tasks in every condition. Ratio = median over tasks of this condition's tokens divided by no memory's.",
        }
    data["demo_note"] = ("Total input = uncached + cache write + cache read tokens, as Claude Code reports them. In Claude Code "
                         "every turn re-reads a ~35k-token system prompt, so what matters is the number of turns, not the "
                         "size of the pack.")
    data["notes"] = [
        "<b>Data.</b> SWE-bench (full test split) Django issues with their real fixes, and 21k issue-fixing commits from "
        "Django's history as the seed. The graph is seeded from these real fixes; nothing from an issue's own fix is visible "
        "before it is answered.",
        "<b>No tuning on the test split.</b> The only tuned values (anchor weight, a few graph constants) were chosen on the 126 "
        "issues before 2019-07. Ideas that did not help on dev are listed in the README, not shipped.",
        "<b>Code anchors.</b> Files in the checkout that define an identifier the issue names (<code>git grep</code> for "
        "<code>def</code>/<code>class</code>). Fused with the graph's learned scores; neither alone is as good.",
        "<b>Second hop.</b> The co-changed-file hop is in the query and measured. It rarely changes the top 5.",
        "<b>Live agents.</b> One run per task and condition, so small differences are noise; intervals are shown. "
        "The agent runs in a sandbox with no network except the model API, after earlier runs were caught fetching the real "
        "fix from GitHub and reading other checkouts. Those runs were discarded.",
        "<b>Claude Code.</b> A few end-to-end examples with a different model. Delivered through an MCP tool, Bearings cost "
        "extra turns and more tokens; that is why it now injects the pack through a prompt hook and learns through a stop hook.",
        "<b>Money.</b> Any dollar figure is list-price arithmetic from token counts, not a measured bill.",
    ]
    data["footer"] = ("Generated by <code>uv run python bench/report.py</code>. Raw rows: <code>results/level1_*.jsonl</code>, "
                      "<code>runs/level2/results.jsonl</code>, <code>results/claude_demo/</code>.")
    page = (ROOT / "bench" / "dashboard.html").read_text().replace("__DATA__", json.dumps(data).replace("</", "<\\/"))
    (RES / "report.html").write_text(page)


if __name__ == "__main__":
    main()
