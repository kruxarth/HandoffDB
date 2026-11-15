"""Build the submission video from real artifacts.

  uv run --with playwright python video/build.py [--only scene] [--no-record]

1. reads narration.json + audio/*.wav (durations)
2. writes scenes/<name>.html with data from results/ and runs/ embedded
3. records each scene in headless Chrome (Playwright record_video, 1920x1080)
4. assembles video/out/bearings.mp4 with ffmpeg (scene clips + narration)
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import subprocess
import wave
from pathlib import Path

V = Path(__file__).resolve().parent
ROOT = V.parent
SC = V / "scenes"
OUT = V / "out"
GAP = 0.35  # silence between narration lines


def lines() -> list[dict]:
    out = []
    for ln in json.load(open(V / "narration.json")):
        h = hashlib.sha1(ln["text"].encode()).hexdigest()[:8]
        wav = V / "audio" / f"{ln['id']}_{h}.wav"
        dur = None
        if wav.exists():
            w = wave.open(str(wav))
            dur = w.getnframes() / w.getframerate()
        out.append({**ln, "wav": wav, "dur": dur})
    return out


CSS = """
*{box-sizing:border-box} html,body{margin:0;width:1920px;height:1080px;overflow:hidden;background:#0e1014;color:#eeede8;
font-family:'Noto Sans','DejaVu Sans',system-ui,sans-serif}
.mono{font-family:'JetBrainsMono Nerd Font Mono','JetBrains Mono','DejaVu Sans Mono',monospace}
.wrap{position:absolute;inset:0;padding:90px 120px}
h1{font-size:76px;line-height:1.08;margin:0 0 28px;font-weight:700;letter-spacing:-1px}
h2{font-size:44px;margin:0 0 20px;font-weight:600;color:#c3c2b7}
.dim{color:#8f8e86} .blue{color:#5c9bea} .orange{color:#e0743f} .green{color:#3dbb8a}
.fade{opacity:0;transform:translateY(14px);transition:opacity .7s ease,transform .7s ease}
.fade.on{opacity:1;transform:none}
.panel{background:#161a21;border:1px solid #262b35;border-radius:18px;padding:28px 34px}
.tag{display:inline-block;font-size:22px;padding:6px 14px;border-radius:999px;background:#1d2a3d;color:#8fbaf0;margin-right:10px}
"""

RUNNER = """
<script>
const D = %DUR%*1000; const t0 = performance.now();
function at(frac, fn){ setTimeout(fn, frac*D); }
function show(sel, frac){ at(frac, ()=>document.querySelectorAll(sel).forEach(e=>e.classList.add('on'))); }
</script>
"""


def page(body: str, dur: float, extra_js: str = "") -> str:
    return (f"<!DOCTYPE html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{body}"
            f"{RUNNER.replace('%DUR%', f'{dur:.2f}')}<script>{extra_js}</script></body></html>")


# ------------------------------------------------------------------ scenes
def scene_problem(dur: float, data: dict) -> str:
    calls = data["calls"]
    items = "".join(f"<div class='c fade'><span class='dim'>$</span> {html.escape(c['cmd'])}</div>" for c in calls)
    body = f"""
<div class='wrap'>
  <h1 class='fade' id='h'>Every task starts from zero.</h1>
  <h2 class='fade' id='s'>A coding agent explores the repo, and pays for every step in tokens.</h2>
  <div style='display:flex;gap:40px;margin-top:40px'>
    <div class='panel mono' style='flex:1;height:560px;overflow:hidden;font-size:22px;line-height:1.7' id='term'>{items}</div>
    <div class='panel' style='width:520px;display:flex;flex-direction:column;justify-content:center;align-items:center'>
      <div class='dim' style='font-size:26px'>tokens read so far</div>
      <div class='mono' id='tok' style='font-size:110px;font-weight:700;color:#e0743f'>0</div>
      <div class='dim' style='font-size:26px'><span id='nc'>0</span> tool calls</div>
      <div class='dim' style='font-size:20px;margin-top:30px;text-align:center'>a real run: {html.escape(data['label'])}</div>
    </div>
  </div>
</div>"""
    js = f"""
show('#h',0.02); show('#s',0.12);
const C=document.querySelectorAll('.c'); const toks={json.dumps([c['cum'] for c in calls])};
C.forEach((c,i)=>at(0.18+0.74*i/C.length, ()=>{{c.classList.add('on'); document.getElementById('tok').textContent=toks[i].toLocaleString('en-US');
document.getElementById('nc').textContent=i+1; const T=document.getElementById('term'); T.scrollTop=T.scrollHeight;}}));
"""
    return page(body, dur, js)


def scene_idea(dur: float, data: dict) -> str:
    # a small real neighbourhood from the graph: one task, its entities, its file, a co-changed file, its test
    nodes = data["nodes"]
    svg = ["<svg width='1680' height='640' viewBox='0 0 1680 640'>"]
    for i, e in enumerate(data["edges"]):
        a, b = nodes[e[0]], nodes[e[1]]
        svg.append(f"<line class='fade e' style='transition-delay:0s' x1='{a['x']}' y1='{a['y']}' x2='{b['x']}' y2='{b['y']}' stroke='#3a4252' stroke-width='3'/>"
                   f"<text class='fade e' x='{(a['x']+b['x'])/2}' y='{(a['y']+b['y'])/2 - 10}' fill='#8f8e86' font-size='20' text-anchor='middle'>{e[2]}</text>")
    for k, n in nodes.items():
        col = {"task": "#e0743f", "term": "#5c9bea", "file": "#3dbb8a", "test": "#d9a536"}[n["kind"]]
        w = max(170, 14 * len(n["label"]) + 40)
        svg.append(f"<g class='fade n {n['kind']}'><rect x='{n['x'] - w / 2}' y='{n['y'] - 32}' width='{w}' height='64' rx='14' fill='#161a21' stroke='{col}' stroke-width='3'/>"
                   f"<text x='{n['x']}' y='{n['y'] + 8}' fill='#eeede8' font-size='24' text-anchor='middle' class='mono'>{html.escape(n['label'])}</text></g>")
    svg.append("</svg>")
    body = f"""<div class='wrap'><h1 class='fade' id='h'>Bearings remembers where past work landed.</h1>
<div class='dim fade' id='s' style='font-size:30px;margin-bottom:30px'>Each finished task is written into HydraDB as structure.</div>
{''.join(svg)}</div>"""
    js = """show('#h',0.02); show('#s',0.1); show('.task',0.2); show('.term',0.35); show('.file',0.55); show('.test',0.7); show('.e',0.6);"""
    return page(body, dur, js)


def scene_query(dur: float, data: dict) -> str:
    def why(w: str) -> str:
        import re
        m = re.match(r"^(\w+) '(.+?)' -> .+? \(together in (\d+) past changes?\)", w)
        return f"'{m.group(2)}' was in {m.group(3)} past fixes here" if m else w
    files = "".join(
        f"<div class='fade f' style='margin:16px 0'><div class='mono' style='font-size:29px'><span class='green'>{i + 1}.</span> {html.escape(f['path'])}"
        + (" <span class='tag' style='background:#1b3326;color:#7fd8ae;font-size:18px'>real fix</span>" if f["path"] in data.get("gold", []) else "")
        + "</div>"
        + ("<div class='mono' style='font-size:22px;margin-left:44px;color:#5c9bea'>"
           + "   ".join(f"def {html.escape(n)}  line {ln}" for ln, n in f.get("lines", [])[:2]) + "</div>" if f.get("lines") else "")
        + "".join(f"<div class='mono dim' style='font-size:20px;margin-left:44px'>{html.escape(why(w))}</div>"
                  for w in [x for x in f["why"] if not x.startswith("defines ")][:1])
        + "</div>" for i, f in enumerate(data["files"][:3]))
    body = f"""<div class='wrap'><h1 class='fade' id='h'>One weighted path query.</h1>
<div style='display:flex;gap:40px'>
 <div class='panel mono fade' id='q' style='width:760px;font-size:22px;line-height:1.6;white-space:pre;color:#c3c2b7'>{html.escape(data['cypher'])}</div>
 <div class='panel' style='flex:1'>
   <div class='dim fade' id='t' style='font-size:24px;margin-bottom:6px'>task: {html.escape(data['task'][:70])}…</div>
   {files}
   <div class='mono fade' id='v' style='font-size:26px;margin-top:22px'>Verify with: <span class='blue'>{html.escape(data['test'] or '')}</span></div>
 </div></div>
<div class='fade' id='w' style='position:absolute;bottom:80px;left:120px;font-size:30px'>
 <span class='tag'>cheaper when it led to the fix</span><span class='tag' style='background:#3a2418;color:#f0a37c'>dearer when it led nowhere</span>
 <span class='tag' style='background:#1b3326;color:#7fd8ae'>no model calls</span></div></div>"""
    js = """show('#h',0.02); show('#q',0.08); show('#t',0.22); document.querySelectorAll('.f').forEach((e,i)=>at(0.3+0.1*i,()=>e.classList.add('on'))); show('#v',0.55); show('#w',0.7);"""
    return page(body, dur, js)


def scene_side(dur: float, d: dict) -> str:
    def col(side: dict, cid: str, title: str, color: str) -> str:
        items = "".join(
            f"<div class='c{cid} fade' style='{'color:#7fd8ae;font-weight:700' if c['gold'] else ''}'><span class='dim'>$</span> {html.escape(c['cmd'])}</div>"
            for c in side["calls"])
        return f"""<div style='flex:1;display:flex;flex-direction:column;gap:14px'>
  <div style='display:flex;justify-content:space-between;align-items:baseline'>
    <div style='font-size:34px;font-weight:700;color:{color}'>{title}</div>
    <div class='mono' style='font-size:54px;font-weight:700' id='tok{cid}'>0</div></div>
  <div class='panel mono' id='term{cid}' style='height:600px;overflow:hidden;font-size:19px;line-height:1.65'>{items}</div>
  <div class='dim' style='font-size:22px'><span id='nc{cid}'>0</span> tool calls · <span id='st{cid}'></span></div></div>"""
    body = f"""<div class='wrap' style='padding-top:60px'>
  <h1 class='fade' id='h' style='font-size:58px'>Same issue, two agents.</h1>
  <div class='dim fade' id='s' style='font-size:26px;margin-bottom:26px'>{html.escape(d['label'])}</div>
  <div style='display:flex;gap:40px'>{col(d['none'], 'a', 'No memory', '#c3c2b7')}{col(d['bearings'], 'b', 'With Bearings', '#5c9bea')}</div></div>"""
    js = f"""show('#h',0.02); show('#s',0.06);
const S={json.dumps({k: {"toks": [c["cum"] for c in d[k]["calls"]], "gold": [c["gold"] for c in d[k]["calls"]], "found": d[k]["found"], "total": d[k]["total"], "answer": d[k]["answer"]} for k in ("none", "bearings")})};
function run(k, id){{ const C=document.querySelectorAll('.c'+id); const n=C.length; const span=0.78;
  C.forEach((c,i)=>at(0.1+span*i/Math.max(n,1), ()=>{{ c.classList.add('on'); document.getElementById('tok'+id).textContent=S[k].toks[i].toLocaleString('en-US');
    document.getElementById('nc'+id).textContent=i+1; const T=document.getElementById('term'+id); T.scrollTop=T.scrollHeight;
    if(S[k].gold[i] && !document.getElementById('st'+id).textContent) document.getElementById('st'+id).textContent='opened the real fix at '+S[k].toks[i].toLocaleString('en-US')+' tokens'; }}));
  at(0.9, ()=>{{ document.getElementById('tok'+id).textContent=S[k].total.toLocaleString('en-US');
    document.getElementById('st'+id).textContent=(S[k].found?'opened the real fix at '+S[k].found.toLocaleString('en-US')+' tokens · ':'')+S[k].answer; }}); }}
run('none','a'); run('bearings','b');"""
    return page(body, dur, js)


def scene_learn(dur: float, d: dict) -> str:
    W, H, L, R, T, B = 1240, 680, 80, 290, 30, 70
    xs = [x for s in d["series"].values() for x, _ in s]
    x0, x1, lo, hi = min(xs), max(xs), d["lo"], d["hi"]
    sx = lambda x: L + (x - x0) / max(1, x1 - x0) * (W - L - R)  # noqa: E731
    sy = lambda y: T + (hi - y) / (hi - lo) * (H - T - B)  # noqa: E731
    col = {"bearings": "#5c9bea", "frozen": "#d9a536", "bm25": "#e87ba4", "dict": "#e0743f"}
    svg = [f"<svg width='{W}' height='{H}' viewBox='0 0 {W} {H}'>"]
    y = lo
    while y <= hi + 1e-9:
        svg.append(f"<line x1='{L}' x2='{W - R}' y1='{sy(y):.0f}' y2='{sy(y):.0f}' stroke='#262b35'/>"
                   f"<text x='{L - 12}' y='{sy(y) + 7:.0f}' fill='#8f8e86' font-size='20' text-anchor='end'>{y:.0%}</text>")
        y += 0.1
    for xv in range(0, x1 + 1, 200):
        if xv >= x0:
            svg.append(f"<text x='{sx(xv):.0f}' y='{H - B + 30}' fill='#8f8e86' font-size='20' text-anchor='middle'>{xv}</text>")
    svg.append(f"<text x='{(L + W - R) / 2}' y='{H - 4}' fill='#8f8e86' font-size='22' text-anchor='middle'>tasks learned</text>")
    ends = []
    for c, ser in d["series"].items():
        pts = " ".join(f"{sx(x):.0f},{sy(v):.0f}" for x, v in ser)
        svg.append(f"<polyline class='ln' points='{pts}' fill='none' stroke='{col[c]}' stroke-width='{5 if c == 'bearings' else 3}' "
                   f"stroke-linejoin='round' pathLength='1' stroke-dasharray='1' stroke-dashoffset='1'/>")
        ends.append([sy(ser[-1][1]), c])
    ends.sort()
    for i in range(1, len(ends)):
        ends[i][0] = max(ends[i][0], ends[i - 1][0] + 30)
    for yv, c in ends:
        svg.append(f"<text class='fade lab' x='{W - R + 14}' y='{yv + 8:.0f}' fill='{col[c]}' font-size='24' font-weight='600'>{d['labels'][c]}</text>")
    svg.append("</svg>")
    stats = "".join(f"<div class='fade st' style='margin:0 0 34px'><div class='mono' style='font-size:64px;font-weight:700;color:{s[2]}'>{s[0]}</div>"
                    f"<div class='dim' style='font-size:24px'>{s[1]}</div></div>" for s in d["stats"])
    body = f"""<div class='wrap'><h1 class='fade' id='h'>{d['title']}</h1>
<div class='dim fade' id='s' style='font-size:28px;margin-bottom:24px'>{d['sub']}</div>
<div style='display:flex;gap:30px'><div>{''.join(svg)}</div><div style='padding-top:30px'>{stats}</div></div></div>"""
    css = "<style>.ln{transition:stroke-dashoffset 3.2s ease-in-out}.ln.on{stroke-dashoffset:0}</style>"
    js = """show('#h',0.02); show('#s',0.08); show('.ln',0.14); show('.lab',0.45);
document.querySelectorAll('.st').forEach((e,i)=>at(0.5+0.12*i,()=>e.classList.add('on')));"""
    return page(css + body, dur, js)


def scene_bars(dur: float, d: dict) -> str:
    mx = max(r["value"] for r in d["rows"])
    cm = len(d["rows"]) > 4
    m, bh, fs = ("10px", 40, 26) if cm else ("26px", 54, 30)
    rows = "".join(
        f"<div class='fade br' style='margin:{m} 0'><div style='font-size:{fs}px;margin-bottom:6px'>{html.escape(r['label'])}"
        f"<span class='dim' style='font-size:24px'>  {html.escape(r['note'])}</span></div>"
        f"<div style='display:flex;align-items:center;gap:20px'><div class='bar' style='height:{bh}px;border-radius:0 8px 8px 0;"
        f"background:{r['color']};width:0' data-w='{900 * r['value'] / mx:.0f}'></div>"
        f"<span class='mono' style='font-size:{fs + 4}px'>{html.escape(r['text'])}</span></div></div>" for r in d["rows"])
    body = f"""<div class='wrap'><h1 class='fade' id='h'>{d['title']}</h1>
<div class='dim fade' id='s' style='font-size:28px;margin-bottom:20px'>{d['sub']}</div>{rows}
<div class='dim fade' id='f' style='position:absolute;bottom:50px;left:120px;font-size:24px;max-width:1680px'>{d['foot']}</div></div>"""
    css = "<style>.bar{transition:width 1.2s ease}</style>"
    js = """show('#h',0.02); show('#s',0.08);
document.querySelectorAll('.br').forEach((e,i)=>at(0.15+0.12*i,()=>{e.classList.add('on'); const b=e.querySelector('.bar'); b.style.width=b.dataset.w+'px';}));
show('#f',0.6);"""
    return page(css + body, dur, js)


def scene_list(dur: float, d: dict) -> str:
    items = "".join(f"<div class='fade it' style='font-size:38px;margin:0 0 36px;max-width:1650px'><span class='{c}'>●</span> {t}</div>"
                    for c, t in d["items"])
    body = f"<div class='wrap'><h1 class='fade' id='h'>{d['title']}</h1><div style='margin-top:50px'>{items}</div></div>"
    js = "show('#h',0.02); document.querySelectorAll('.it').forEach((e,i)=>at(0.1+0.8*i/document.querySelectorAll('.it').length,()=>e.classList.add('on')));"
    return page(body, dur, js)


def scene_card(dur: float, title: str, sub: str) -> str:
    body = f"""<div class='wrap' style='display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center'>
<h1 class='fade' id='h' style='font-size:120px'>{html.escape(title)}</h1><h2 class='fade' id='s'>{sub}</h2></div>"""
    return page(body, dur, "show('#h',0.03); show('#s',0.2);")


def scene_html(name: str, dur: float, data: dict) -> str:
    if name == "problem":
        return scene_problem(dur, data["problem"])
    if name == "idea":
        return scene_idea(dur, data["idea"])
    if name == "query":
        return scene_query(dur, data["query"])
    if name == "team":
        return scene_card(dur, "Built for teams", "What one person's agent learns, every agent on the team starts from.<br>"
                          "<span class='dim'>One graph per repo, scoped per team, self-hosted on HydraDB.</span>")
    if name == "end":
        return scene_card(dur, "Bearings", "Your agents start where your team left off.")
    if name == "learn":
        return scene_learn(dur, data["learn"])
    if name == "side":
        return scene_side(dur, data["side"])
    if name in ("live", "claude"):
        return scene_bars(dur, data[name])
    if name == "limits":
        return scene_list(dur, data["limits"])
    raise KeyError(name)


# -------------------------------------------------------------------- data
def build_data() -> dict:
    import sys
    sys.path.insert(0, str(ROOT / "src"))
    data: dict = {}
    # problem: the sandboxed no-memory Level 2 run with the most tool calls
    res = [json.loads(x) for x in open(ROOT / "runs/level2/results.jsonl")]
    cand = [r for r in res if r["condition"] == "none" and r["exit"] == 0 and r.get("sandboxed")
            and not r.get("outside_access")]
    r = max(cand, key=lambda r: r["tool_calls"])
    calls, cum = [], 0
    for line in open(ROOT / f"runs/level2/none/{r['id']}.r0.jsonl"):
        e = json.loads(line)
        p = e.get("part", {})
        if e["type"] == "step_finish":
            t = p["tokens"]
            cum += t["input"] + t["cache"]["read"] + t["cache"].get("write", 0)
            for c in calls:
                c.setdefault("cum", cum)
        if e["type"] == "tool_use":
            i = p.get("state", {}).get("input", {})
            cmd = i.get("command") or (f"{p.get('tool')} {i.get('pattern') or i.get('filePath') or ''}")
            calls.append({"cmd": cmd.replace("/work/repo/", "").split("\n")[0][:80]})
    for c in calls:
        c.setdefault("cum", cum)
    data["problem"] = {"calls": calls[:40], "label": f"SWE-bench {r['id'].split('__')[1]}, DeepSeek via OpenCode, no memory"}
    # query: the real v2 pack for the illustration task, chosen by a fixed rule: the
    # earliest post-cutoff Verified issue whose real fix the pack ranks first with a line anchor
    from bearings.core import Bearings, Params
    from bearings.db import Hydra, cypher_strings
    tid = "django__django-15916"
    task = next(json.loads(x) for x in open(ROOT / "data/derived/tasks.jsonl") if json.loads(x)["id"] == tid)
    eng = Bearings(Hydra(tenant="bench", subtenant="django-l2"), Params())
    eng.load(full=False)
    pk = eng.context_pack(task["text"], repo=ROOT / "data/repos/django", commit=task["base_commit"])
    data["query"] = {"task": task["text"].split("\n")[0], "files": pk.files, "test": pk.test_command, "gold": task["files"],
                     "cypher": "CALL algo.MSpaths({\n  sourceLabel: 'Term',\n  sourceProperty: 'key',\n"
                               f"  sourceValues: {cypher_strings(pk.entities[:2])[:-1]},\n    ...],\n"
                               "  relTypes: ['POINTS_TO', 'CO_CHANGED'],\n  maxLen: 2, weightProp: 'w',\n"
                               "  pathCount: 20 })\nYIELD path, pathWeight"}
    # idea: a real neighbourhood from the graph: a past fix (before the cutoff) that
    # changed the top file and shares the entities that led the pack there
    from bearings.core import test_command
    from bearings.entities import extract
    top = pk.files[0]
    terms = [t for t in top["terms"] if ":" in t][:6]
    best = None
    for line in open(ROOT / "data/derived/history.jsonl"):
        h = json.loads(line)
        if h["date"] >= "2022-07-01" or top["path"] not in h["files"]:
            continue
        shared = [t for t in terms if t in extract(h["text"])]
        has_other = any(f != top["path"] and f.endswith(".py") and not f.startswith("tests/") for f in h["files"])
        key = (len(shared), has_other)
        if best is None or key > best[2]:
            best = (h, shared, key)
    h, shared, _ = best
    shared = (shared + [t for t in terms if t not in shared])[:3]
    other = next((f for f in h["files"] if f != top["path"] and f.endswith(".py") and not f.startswith("tests/")), None)
    tests = next((f for f in h["files"] if f.startswith("tests/")), None)
    short = lambda p: "/".join(p.split("/")[-2:])  # noqa: E731
    nodes = {"T": {"kind": "task", "label": f"past fix {h['id'].split(':')[-1][:7]}", "x": 170, "y": 320},
             "F": {"kind": "file", "label": short(top["path"]), "x": 1040, "y": 320}}
    edges = [("T", "a", "mentions")]
    for i, t in enumerate(shared):
        k = "abc"[i]
        nodes[k] = {"kind": "term", "label": t.split(":", 1)[1], "x": 580, "y": [140, 320, 500][i]}
        if i:
            edges.append(("T", k, ""))
        edges.append((k, "F", "points to" if i == 0 else ""))
    if other:
        nodes["G"] = {"kind": "file", "label": short(other), "x": 1460, "y": 150}
        edges.append(("F", "G", "co-changed"))
    tc = test_command(tests) if tests else None
    if tc:
        nodes["X"] = {"kind": "test", "label": tc.replace("./tests/runtests.py", "runtests.py"), "x": 1400, "y": 520}
        edges.append(("F", "X", "tested by"))
    data["idea"] = {"nodes": nodes, "edges": edges}
    data["side"] = side_data("django__django-15916")
    data.update(results_data())
    return data


def side_data(tid: str) -> dict | None:
    """The same issue, no memory vs Bearings, from the committed Level 2 run logs."""
    rows = {json.loads(x)["condition"]: json.loads(x) for x in open(ROOT / "runs/level2/results.jsonl")
            if json.loads(x)["id"] == tid}
    if "none" not in rows or "bearings" not in rows:
        return None
    out = {"label": f"SWE-bench {tid.split('__')[1]}: {rows['none'].get('gold')[0]} is the file to find. "
                    f"DeepSeek V4.1 Flash through OpenCode, real runs, tokens = input read so far."}
    for cond in ("none", "bearings"):
        r = rows[cond]
        calls, cum = [], 0
        for line in open(ROOT / f"runs/level2/{cond}/{tid}.r0.jsonl"):
            e = json.loads(line)
            p = e.get("part", {})
            if e["type"] == "step_finish":
                t = p["tokens"]
                cum += t["input"] + t["cache"]["read"]
                for c in calls:
                    c.setdefault("cum", cum)
            if e["type"] == "tool_use":
                i = p.get("state", {}).get("input", {})
                cmd = i.get("command") or f"{p.get('tool')} {i.get('pattern') or i.get('filePath') or ''}"
                gold = any(g in json.dumps(i) for g in r["gold"])
                calls.append({"cmd": cmd.replace("/work/repo/", "").split("\n")[0][:62], "gold": gold})
        for c in calls:
            c.setdefault("cum", cum)
        ok = "named the right file" if r["all"] else "missed the file"
        out[cond] = {"calls": calls, "total": r["total_input"], "found": r.get("tokens_to_first_gold"),
                     "answer": f"{r['total_input']:,} tokens in total, {ok}"}
    return out


def results_data() -> dict:
    """Numbers for the result scenes, computed the same way as bench/report.py."""
    import sys
    sys.path.insert(0, str(ROOT / "bench"))
    import report as rep
    from summarize import ci
    out: dict = {}
    m = {}
    for seed in ("history", "tasks"):
        test = rep.rows(rep.RES / f"level1_{seed}.jsonl")
        m[seed] = {c: {k: ci([r["metrics"][c][k] for r in test if c in r["metrics"]])[0] for k in ("hit@1", "hit@5")}
                   for c in ("bearings", "bearings-1", "bm25", "frozen", "graph", "anchors")}
        m[seed]["n"] = len(test)
    cv = rep.curve(rep.RES / "level1_tasks.jsonl")  # empty start: where learning shows
    keep = {c: cv[c] for c in ("frozen", "bm25", "bearings") if c in cv}
    ys = [v for s_ in keep.values() for _, v in s_]
    H, T = m["history"], m["tasks"]
    out["learn"] = {
        "series": keep, "lo": max(0, int(min(ys) * 10) / 10), "hi": min(1, (int(max(ys) * 10) + 1) / 10),
        "labels": {"bearings": "Bearings", "frozen": "Same graph, frozen", "bm25": "Keyword search"},
        "title": "The right file, more often.",
        "sub": f"{H['n']} real Django issues, in date order. Chart: starting from an empty graph, top-5 hit rate.",
        "stats": [(f"{H['bearings']['hit@1']:.0%}", f"real fix ranked first (keyword search {H['bm25']['hit@1']:.0%})", "#5c9bea"),
                  (f"{H['bearings']['hit@5']:.0%}", f"real fix in the top 5 (keyword search {H['bm25']['hit@5']:.0%})", "#5c9bea"),
                  (f"{T['bearings']['hit@5']:.0%}", f"from an empty graph (keyword search {T['bm25']['hit@5']:.0%})", "#3dbb8a")],
        "m": m}
    md, st = rep.level2()
    c = st.get("conds", {})
    if c:
        lab = {"none": "No memory", "dict": "Dictionary pack", "anchors": "Code anchors only", "bearings": "Bearings"}
        colr = {"none": "#6b6a64", "dict": "#e87ba4", "anchors": "#9085e9", "bearings": "#5c9bea"}
        out["live"] = {
            "title": "Across forty new issues: no token saving.",
            "sub": f"Live agents (DeepSeek through OpenCode), {st['n']} real issues the graph never saw. Median input tokens per run.",
            "rows": [{"label": lab[k], "value": v["median_in"], "text": f"{v['median_in']:,.0f}", "color": colr[k],
                      "note": f"found every file in {v['succ'][0]:.0%}"} for k, v in c.items() if k in lab],
            "foot": "Includes the pack's own tokens. Same issues in every condition. In every condition the agent opened a real-fix file after about 7k tokens.",
            "stats": st}
    dd = [json.loads(p.read_text()) for p in sorted((rep.RES / "claude_demo").glob("*.json"))]
    dd = [x for x in dd if "side" in x]
    if dd:
        lab = {"without": "without Bearings", "without-2": "without, second run", "hook": "with Bearings"}
        colr = {"without": "#6b6a64", "without-2": "#4a4945", "hook": "#5c9bea"}
        rows = []
        for t in sorted({x["task"] for x in dd}):
            for side in ("without", "without-2", "hook"):
                x = next((y for y in dd if y["task"] == t and y["side"] == side), None)
                if x:
                    rows.append({"label": f"{t.split('__')[1]}, {lab[side]}", "value": x["total_input"],
                                 "text": f"{x['total_input']:,}", "color": colr[side],
                                 "note": f"{x['num_turns']} turns"})
        out["claude"] = {"title": "And in Claude Code?", "rows": rows,
                         "sub": "Two real issues fixed end to end in headless Claude Code. Total input tokens, as Claude Code reports them.",
                         "foot": "Two examples, not a statistic. The model already knew where to look; each extra turn re-reads the whole context.",
                         "demo": dd}
    d2 = (H["bearings"]["hit@5"] - H["bearings-1"]["hit@5"]) * 100
    out["limits"] = {"title": "What did not help, measured.", "items": [
        ("orange", f"The second hop through files that change together: {d2:+.1f} points top-5."),
        ("orange", "Live agents on 40 new issues: no token saving. The issues already point at the code."),
        ("orange", "In Claude Code on two demo tasks: no saving either."),
        ("blue", "Seeded from the dataset's own real fixes, in date order, never from the future. Tuned only on earlier issues."),
        ("blue", "Every number is reproducible from committed result files."),
    ]}
    return out


# ----------------------------------------------------------------- record
def record(name: str, html_text: str, dur: float) -> Path:
    from playwright.sync_api import sync_playwright
    SC.mkdir(exist_ok=True)
    (SC / f"{name}.html").write_text(html_text)
    vid_dir = OUT / "raw" / name
    subprocess.run(["rm", "-rf", str(vid_dir)])
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/usr/bin/google-chrome-stable")
        ctx = b.new_context(viewport={"width": 1920, "height": 1080}, record_video_dir=str(vid_dir),
                            record_video_size={"width": 1920, "height": 1080})
        pg = ctx.new_page()
        pg.goto((SC / f"{name}.html").as_uri())
        pg.wait_for_timeout(int((dur + 0.6) * 1000))
        ctx.close()
        b.close()
    webm = next(vid_dir.glob("*.webm"))
    mp4 = OUT / f"{name}.mp4"
    # drop the first 0.3 s (page load), fix length, constant 30 fps
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "0.3", "-i", str(webm), "-t", f"{dur:.2f}",
                    "-r", "30", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", str(mp4)], check=True)
    return mp4


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None)
    ap.add_argument("--no-record", action="store_true")
    args = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    ls = lines()
    scenes: list[tuple[str, list[dict]]] = []
    for ln in ls:
        if scenes and scenes[-1][0] == ln["scene"]:
            scenes[-1][1].append(ln)
        else:
            scenes.append((ln["scene"], [ln]))
    data = build_data()
    clips, audio_parts = [], []
    for name, group in scenes:
        if any(g["dur"] is None for g in group):
            print("missing audio for", name)
            continue
        dur = sum(g["dur"] for g in group) + GAP * len(group) + 0.6
        if not args.no_record and (args.only in (None, name)):
            record(name, scene_html(name, dur, data), dur)
            print("recorded", name, f"{dur:.1f}s")
        clips.append((OUT / f"{name}.mp4", dur))
        audio_parts.append(group)
    # narration track: each line followed by GAP, each scene padded to its clip length
    concat = OUT / "audio_list.txt"
    with open(concat, "w") as f:
        for (clip, dur), group in zip(clips, audio_parts):
            used = 0.0
            for g in group:
                f.write(f"file '{g['wav']}'\n")
                sil = OUT / f"sil_{GAP}.wav"
                if not sil.exists():
                    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"anullsrc=r=24000:cl=mono",
                                    "-t", str(GAP), str(sil)], check=True)
                f.write(f"file '{sil}'\n")
                used += g["dur"] + GAP
            pad = OUT / f"pad_{name_safe(clip)}.wav"
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
                            "-t", f"{max(0.01, dur - used):.3f}", str(pad)], check=True)
            f.write(f"file '{pad}'\n")
    with open(OUT / "video_list.txt", "w") as f:
        for clip, _ in clips:
            f.write(f"file '{clip}'\n")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(OUT / "video_list.txt"),
                    "-f", "concat", "-safe", "0", "-i", str(concat), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
                    "-c:a", "aac", "-b:a", "192k", "-shortest", str(OUT / "bearings.mp4")], check=True)
    total = sum(d for _, d in clips)
    print(f"video/out/bearings.mp4  {total:.1f}s")


def name_safe(p: Path) -> str:
    return p.stem


if __name__ == "__main__":
    main()
