"""Build results/RESULTS.md and results/report.html from the committed result files.

  uv run python bench/report.py

Every number in the README comes from this script's output.
"""

from __future__ import annotations

import html
import json
import math
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bench"))
from summarize import CONDS, ci, paired_diff  # noqa: E402

RES = ROOT / "results"
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
    W, H, L, R, T, B = 720, 340, 52, 150, 16, 44
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
    parts.append(f'<text x="12" y="{T + 4}" class="axis">{html.escape(ylab)}</text>')
    labels = []
    for c, s in series.items():
        pts = " ".join(f"{sx(x):.1f},{sy(y):.1f}" for x, y in s)
        parts.append(f'<polyline points="{pts}" fill="none" stroke="var({COLOR[c]})" stroke-width="2" '
                     f'stroke-linejoin="round" stroke-linecap="round"><title>{LABEL[c]}</title></polyline>')
        labels.append([sy(s[-1][1]), c, s[-1][1]])
    labels.sort()
    for i in range(1, len(labels)):  # de-collide end labels
        labels[i][0] = max(labels[i][0], labels[i - 1][0] + 14)
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


def level2() -> tuple[str, list[dict], dict]:
    p = ROOT / "runs" / "level2" / "results.jsonl"
    rp = RES / "level2_results.jsonl"
    src = rp if rp.exists() else p
    if not src.exists():
        return "(Level 2 not run yet)", [], {}
    rs = [json.loads(line) for line in open(src)]
    valid = [r for r in rs if not r["rate_limited"] and r["exit"] == 0]
    excluded = len(rs) - len(valid)
    conds = [c for c in ("none", "dict", "bearings") if any(r["condition"] == c for r in valid)]
    # paired: only tasks with a valid run in every condition
    ids = set.intersection(*[{r["id"] for r in valid if r["condition"] == c} for c in conds]) if conds else set()
    by = {c: {r["id"]: r for r in valid if r["condition"] == c} for c in conds}
    lab = {"none": "No memory", "dict": "Dictionary pack in prompt", "bearings": "Bearings (MCP)"}
    out = [f"Model: `{valid[0]['model'] if valid else '?'}` via OpenCode. Paired tasks: {len(ids)}. "
           f"Runs excluded (rate limit / crash / timeout): {excluded} of {len(rs)}.", "",
           "| Condition | success (all gold files named) | hit (≥1 gold file) | total input tokens, median [IQR] | uncached input | output+reasoning | tool calls | wall s |",
           "|---|---|---|---|---|---|---|---|"]
    stats = {}
    for c in conds:
        rr = [by[c][i] for i in sorted(ids)]
        if not rr:
            continue
        ti = sorted(r["total_input"] for r in rr)
        q = statistics.quantiles(ti, n=4) if len(ti) >= 4 else [ti[0], statistics.median(ti), ti[-1]]
        succ = ci([r["all"] for r in rr])
        hit = ci([r["hit"] for r in rr])
        stats[c] = {"succ": succ, "hit": hit, "median_in": statistics.median(ti), "mean_in": sum(ti) / len(ti), "n": len(rr)}
        out.append(f"| {lab[c]} | {fmt(succ)} | {fmt(hit)} | {statistics.median(ti):,.0f} [{q[0]:,.0f}–{q[2]:,.0f}] | "
                   f"{statistics.median([r['tokens']['input'] for r in rr]):,.0f} | "
                   f"{statistics.median([r['tokens']['output'] + r['tokens']['reasoning'] for r in rr]):,.0f} | "
                   f"{statistics.median([r['tool_calls'] for r in rr]):.0f} | {statistics.median([r['wall_s'] for r in rr]):.0f} |")
    if "none" in conds:
        out += ["", "| Paired difference vs no memory | Δ success | Δ total input tokens (mean, 95% CI) | median ratio |", "|---|---|---|---|"]
        for c in conds:
            if c == "none":
                continue
            a = [by[c][i] for i in sorted(ids)]
            b = [by["none"][i] for i in sorted(ids)]
            ds = paired_diff([x["all"] for x in a], [y["all"] for y in b])
            dt = paired_diff([x["total_input"] for x in a], [y["total_input"] for y in b])
            ratio = statistics.median([x["total_input"] / max(1, y["total_input"]) for x, y in zip(a, b)])
            out.append(f"| {lab[c]} | {ds[0]:+.3f} [{ds[1]:+.3f}, {ds[2]:+.3f}] | {dt[0]:+,.0f} [{dt[1]:+,.0f}, {dt[2]:+,.0f}] | {ratio:.2f} |")
    return "\n".join(out), valid, stats


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


def main() -> None:
    md = ["# Results", "", "Generated by `uv run python bench/report.py` from the files in `results/`. "
          "Brackets are 95% bootstrap confidence intervals.", ""]
    body_html = []
    for seed, title in (("history", "Seeded from Django's commit history, then learning from the task stream"),
                        ("tasks", "Learning from the task stream only (a team starting from an empty graph)")):
        path = RES / f"level1_{seed}.jsonl"
        test = rows(path)
        if not test:
            continue
        ver = rows(path, subset="verified")
        md += [f"## Level 1, {title}", "", f"Test split: SWE-bench Django tasks from 2019-07-01 on (n={len(test)}). "
               f"Retrieval only, no model calls.", "", l1_table(test), "", diffs(test), "",
               f"SWE-bench Verified subset (n={len(ver)}):", "", l1_table(ver), ""]
        w, lo = where_differ(test, "bearings", "dict")
        w2, l2 = where_differ(test, "bearings", "bearings-1")
        lat = sorted(r["latency_full_ms"] for r in test)
        lat1 = sorted(r["latency_one_ms"] for r in test)
        agree = [r["db_matches_reference"] for r in test if "db_matches_reference" in r]
        tc = [r["test_cmd_hit"] for r in test]
        pc = sorted(r["pack_chars"] for r in test)
        md += [f"- Where Bearings and the dictionary differ at hit@5: Bearings better on {w} tasks, worse on {lo}.",
               f"- Where the second hop changes hit@5: better on {w2} tasks, worse on {l2}.",
               f"- Query latency (HydraDB path query + scoring): full p50 {lat[len(lat)//2]:.0f} ms, p95 {lat[int(len(lat)*.95)]:.0f} ms; "
               f"one hop p50 {lat1[len(lat1)//2]:.0f} ms.",
               f"- Suggested test command names the module the real fix's tests live in: {sum(tc)/len(tc):.3f} of tasks.",
               f"- Context pack size: median {pc[len(pc)//2]} characters (≈{pc[len(pc)//2]//4} tokens).",
               (f"- HydraDB's ranking equals the in-memory reference implementation on {sum(agree)}/{len(agree)} tasks."
                if agree else ""), ""]
        body_html.append(f"<h2>Level 1: {html.escape(title)}</h2>")
        body_html.append(f"<p class='note'>hit@5 = the real fix touched at least one of the 5 suggested files. "
                         f"Rolling mean over 100 tasks; each task is answered before it is learned.</p>")
        body_html.append(svg_lines(curve(path), f"hit@5 vs tasks learned ({seed})", "hit@5", f"curve-{seed}"))
        groups = []
        for m in ("hit@1", "hit@5"):
            items = []
            for c in CONDS:
                sub = [r for r in test if c in r["metrics"]]
                if sub:
                    items.append((c, *ci([r["metrics"][c][m] for r in sub])))
            groups.append((f"{m}, test split n={len(test)}", items))
        body_html.append(svg_bars(groups, f"bars-{seed}"))
    rs = reach_section()
    if rs:
        md += ["## Does the second hop reach files the first hop cannot?", "",
               "Measured on the dev split: for each gold source file, is it linked in one hop from any of the task's "
               "entities, only through a CO_CHANGED hop, or not at all?", "", rs, ""]
    l2md, l2rows, l2stats = level2()
    md += ["## Level 2, live agent runs: tokens to locate the right files", "",
           "Measured with DeepSeek through OpenCode. The agent names the files it would edit and stops; success is "
           "checked in code against the real fix. Token counts include the context pack.", "", l2md, ""]
    demo = sorted((RES / "claude_demo").glob("*.json")) if (RES / "claude_demo").exists() else []
    if demo:
        md += ["## Claude Code demo (one task, not a statistic)", "",
               "| Side | total input | uncached input | cache write | cache read | output | turns | tool calls | right files | list-price arithmetic |",
               "|---|---|---|---|---|---|---|---|---|---|"]
        for p in demo:
            d = json.loads(p.read_text())
            if "side" not in d:
                continue
            md.append(f"| {d['side']} Bearings ({d['task']}, {d['model']}) | {d['total_input']:,} | {d['input_tokens']:,} | "
                      f"{d['cache_creation_input_tokens']:,} | {d['cache_read_input_tokens']:,} | {d['output_tokens']:,} | "
                      f"{d['num_turns']} | {d['tool_calls']} | {d['correct_files']} | ${d['list_price_usd']:.2f} |")
        md.append("")
    (RES / "RESULTS.md").write_text("\n".join(md))
    md_html = "\n".join(md)
    page = TEMPLATE.replace("{{BODY}}", "\n".join(body_html)).replace("{{RESULTS_MD}}", html.escape(md_html))
    (RES / "report.html").write_text(page)
    print("\n".join(md))


TEMPLATE = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Bearings results</title>
<style>
.viz-root{color-scheme:light;--surface-1:#fcfcfb;--text-primary:#0b0b0b;--text-secondary:#52514e;--grid:#e4e3df;
--series-1:#2a78d6;--series-2:#eb6834;--series-3:#1baf7a;--series-4:#eda100;--series-5:#e87ba4}
@media (prefers-color-scheme: dark){:root:where(:not([data-theme="light"])) .viz-root{color-scheme:dark;--surface-1:#1a1a19;
--text-primary:#f0efec;--text-secondary:#c3c2b7;--grid:#34332f;--series-1:#3987e5;--series-2:#d95926;--series-3:#199e70;--series-4:#c98500;--series-5:#d55181}}
body{margin:0;font:15px/1.5 system-ui,sans-serif}
.viz-root{background:var(--surface-1);color:var(--text-primary);min-height:100vh;padding:24px 32px;max-width:980px;margin:auto}
h1{font-size:26px;margin:0 0 4px} h2{font-size:19px;margin:32px 0 6px} .note{color:var(--text-secondary);margin:0 0 8px}
.chart{width:100%;height:auto;display:block;margin:8px 0 12px}
.grid{stroke:var(--grid);stroke-width:1} .tick{fill:var(--text-secondary);font-size:11px} .axis{fill:var(--text-secondary);font-size:12px}
.dlabel{fill:var(--text-primary);font-size:12px} .glabel{fill:var(--text-primary);font-size:13px;font-weight:600}
.whisker{stroke:var(--text-secondary);stroke-width:1.5} .xhair{stroke:var(--text-secondary);stroke-width:1;stroke-dasharray:3 3}
#tip{position:fixed;pointer-events:none;background:var(--surface-1);border:1px solid var(--grid);border-radius:6px;padding:6px 8px;font-size:12px;display:none;box-shadow:0 2px 8px #0002}
textarea{width:100%;min-height:140px;font:13px ui-monospace,monospace;background:transparent;color:inherit;border:1px solid var(--grid);border-radius:6px;padding:8px}
button,select{font:inherit;padding:6px 12px;border-radius:6px;border:1px solid var(--grid);background:transparent;color:inherit;cursor:pointer}
.file{margin:10px 0;padding:10px 12px;border:1px solid var(--grid);border-radius:8px} .file code{font-weight:600}
.why{color:var(--text-secondary);font:12px ui-monospace,monospace;margin-top:4px}
details pre{white-space:pre-wrap;font-size:12px}
</style></head>
<body><div class="viz-root">
<h1>Bearings</h1>
<p class="note">A learned context layer for coding agents, stored as a graph in self-hosted HydraDB. Every number below is generated from the result files in this repository.</p>
<h2>Try a task</h2>
<p class="note">Paste an issue, or pick a SWE-bench task from after the graph's cutoff. The suggestions come from one weighted path query against HydraDB; each line under a file is the graph path that justifies it.</p>
<select id="ex"><option value="">Pick an example task...</option></select>
<textarea id="task" placeholder="Describe the bug or task"></textarea>
<p><button id="go">Get context pack</button> <span id="meta" class="note"></span></p>
<div id="out"></div>
{{BODY}}
<details><summary>All result tables (RESULTS.md)</summary><pre>{{RESULTS_MD}}</pre></details>
<div id="tip"></div>
</div>
<script>
const tip=document.getElementById('tip');
document.querySelectorAll('svg[data-chart]').forEach(svg=>{
  const d=JSON.parse(document.getElementById('data-'+svg.dataset.chart).textContent);
  const hit=svg.querySelector('.hit'), xh=svg.querySelector('.xhair');
  hit.addEventListener('mousemove',ev=>{
    const pt=svg.createSVGPoint(); pt.x=ev.clientX; pt.y=ev.clientY;
    const p=pt.matrixTransform(svg.getScreenCTM().inverse());
    const x=d.x0+(p.x-d.L)/(d.W-d.L-d.R)*(d.x1-d.x0);
    let rows=[], nx=null;
    for(const [c,s] of Object.entries(d.series)){let best=s[0];for(const q of s){if(Math.abs(q[0]-x)<Math.abs(best[0]-x))best=q;}nx=best[0];rows.push([best[1],d.labels[c]]);}
    rows.sort((a,b)=>b[0]-a[0]);
    tip.innerHTML='<b>after '+nx+' tasks</b><br>'+rows.map(r=>r[1]+': '+r[0].toFixed(3)).join('<br>');
    tip.style.display='block'; tip.style.left=(ev.clientX+14)+'px'; tip.style.top=(ev.clientY+10)+'px';
    const sx=d.L+(nx-d.x0)/(d.x1-d.x0)*(d.W-d.L-d.R); xh.setAttribute('x1',sx); xh.setAttribute('x2',sx); xh.setAttribute('visibility','visible');
  });
  hit.addEventListener('mouseleave',()=>{tip.style.display='none'; xh.setAttribute('visibility','hidden');});
});
const esc=s=>s.replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
fetch('/api/examples').then(r=>r.json()).then(ex=>{const sel=document.getElementById('ex');
  ex.forEach((t,i)=>{const o=document.createElement('option');o.value=i;o.textContent=t.id;sel.appendChild(o);});
  sel.onchange=()=>{const t=ex[sel.value]; if(t){document.getElementById('task').value=t.text; window._gold=t.gold;}};
}).catch(()=>{document.getElementById('meta').textContent='(start the server with: uv run bearings-web)';});
document.getElementById('go').onclick=async()=>{
  const task=document.getElementById('task').value; if(!task.trim())return;
  document.getElementById('meta').textContent='querying HydraDB...';
  const r=await (await fetch('/api/pack?task='+encodeURIComponent(task))).json();
  const gold=window._gold||[];
  document.getElementById('meta').textContent=`${r.ms} ms, scope ${r.scope}, ${r.graph_tasks} tasks in graph`+(gold.length?`; real fix touched: ${gold.join(', ')}`:'');
  document.getElementById('out').innerHTML=r.files.map((f,i)=>`<div class="file"><code>${i+1}. ${esc(f.path)}</code> ${gold.includes(f.path)?' <b>(in the real fix)</b>':''}<span class="note"> score ${f.score}</span>${f.why.map(w=>'<div class="why">'+esc(w)+'</div>').join('')}</div>`).join('')+(r.test_command?`<p>Verify with <code>${esc(r.test_command)}</code></p>`:'');
};
</script></body></html>"""


if __name__ == "__main__":
    main()
