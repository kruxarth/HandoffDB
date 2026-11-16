"""Handoff-graph section of results/RESULTS.md and the dashboard, from committed files:
runs/handoff/results.jsonl (Experiment A), runs/handoff/same/results.jsonl (B),
runs/handoff/prior/results.jsonl (memory runs), runs/handoff/notes/usage.jsonl,
results/handoff_retrieval.{txt,jsonl}, results/handoff_load.json."""
from __future__ import annotations

import json
import statistics
from pathlib import Path

from summarize import ci, paired_diff

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "runs" / "handoff"
RES = ROOT / "results"
LAB = {"cold": "Cold start (nothing)", "notes": "Handoff notes (Markdown files)", "graph": "Bearings handoff pack (graph)"}
ORDER = ("cold", "notes", "graph")


def _rows(p: Path) -> list[dict]:
    return [json.loads(line) for line in open(p)] if p.exists() else []


def fmt(t, pct=False) -> str:
    if pct:
        return f"{t[0]:.0%} [{t[1]:.0%}, {t[2]:.0%}]"
    return f"{t[0]:.3f} [{t[1]:.3f}, {t[2]:.3f}]"


def experiment(path: Path, rep: int | None = None) -> dict:
    """Paired stats per condition. A run counts unless rate-limited or never started; issues
    missing a counted run in any condition are dropped from the paired set."""
    rs = _rows(path)
    latest = {}
    for r in rs:
        if rep is None or r.get("rep", 0) == rep:
            latest[(r["id"], r["condition"], r.get("rep", 0))] = r
    superseded = len(_rows(path)) - len(latest)
    rs = list(latest.values())
    valid = [r for r in rs if not r["rate_limited"] and r["steps"] > 0]
    conds = [c for c in ORDER if any(r["condition"] == c for r in valid)]
    by = {c: {} for c in conds}
    for r in valid:
        by[r["condition"]].setdefault(r["id"], []).append(r)
    ids = sorted(set.intersection(*[set(by[c]) for c in conds])) if conds else []
    out = {"superseded": superseded,
           "bad_note_rows": sum(1 for r in rs if r["condition"] == "notes" and r.get("note_tokens_on_disk", 0) > 300000),
           "n": len(ids), "total_runs": len(rs), "excluded": len(rs) - len(valid), "conds": {}, "ids": ids,
           "timeouts": sum(1 for r in valid if r["exit"] == "timeout" and r["id"] in ids),
           "escapes": sum(1 for r in valid if r.get("outside_access") and r["id"] in ids),
           "model": valid[0]["model"] if valid else "?"}

    def per_issue(c, key):
        return [statistics.mean(x[key] for x in by[c][i]) for i in ids]
    for c in conds:
        tin = per_issue(c, "total_input")
        q = statistics.quantiles(tin, n=4) if len(tin) >= 4 else [min(tin), statistics.median(tin), max(tin)]
        st = {"q1": q[0], "q3": q[2], "succ": ci(per_issue(c, "success")), "src": ci(per_issue(c, "src_ok")), "test": ci(per_issue(c, "test_ok")),
              "median_in": statistics.median(tin), "mean_in": statistics.mean(tin), "steps": statistics.median(per_issue(c, "steps")),
              "wall": statistics.median(per_issue(c, "wall_s")), "tin": tin,
              "pack_tokens": statistics.median(per_issue(c, "pack_tokens")) if c == "graph" else 0,
              "note_tokens_on_disk": statistics.median(per_issue(c, "note_tokens_on_disk")) if c == "notes" else 0,
              "n_notes": statistics.median(per_issue(c, "n_notes")) if c == "notes" else 0}
        out["conds"][c] = st
    for a, b in (("graph", "cold"), ("graph", "notes"), ("notes", "cold")):
        if a in out["conds"] and b in out["conds"]:
            A, B = out["conds"][a], out["conds"][b]
            out[f"{a}-{b}"] = {"dtok": paired_diff(A["tin"], B["tin"]),
                               "ratio": statistics.median([x / max(1, y) for x, y in zip(A["tin"], B["tin"])]),
                               "dsucc": paired_diff(per_issue(a, "success"), per_issue(b, "success"))}
            d = out[f"{a}-{b}"]
            saves = d["dtok"][2] < 0 and A["succ"][0] >= B["succ"][0]
            costs = d["dtok"][1] > 0
            d["verdict"] = "saves tokens" if saves else ("cheaper but less successful: no saving claimed"
                                                         if d["dtok"][2] < 0 else "costs more tokens" if costs else "tie")
    return out


def table(ex: dict) -> str:
    if not ex["n"]:
        return "(not run yet)"
    out = [f"Model: `{ex['model']}` through OpenCode, sandboxed. Paired issues: {ex['n']}. Runs excluded (rate-limited or "
           f"never started): {ex['excluded']} of {ex['total_runs']}. Timeouts counted as failures: {ex['timeouts']}. "
           f"Runs with a tool call flagged by the escape check: {ex['escapes']}.", "",
           "| Condition | success (fix files and a real test file) | fix files named | test file named | total input tokens, median | mean | steps, median | what it was given |",
           "|---|---|---|---|---|---|---|---|"]
    for c in ORDER:
        if c not in ex["conds"]:
            continue
        s = ex["conds"][c]
        given = {"cold": "nothing", "notes": f"{s['n_notes']:.0f} notes on disk (median), {s['note_tokens_on_disk']:,.0f} tokens if all read",
                 "graph": f"a pack of {s['pack_tokens']:,.0f} tokens (median)"}[c]
        out.append(f"| {LAB[c]} | {fmt(s['succ'], True)} | {fmt(s['src'], True)} | {fmt(s['test'], True)} | "
                   f"{s['median_in']:,.0f} | {s['mean_in']:,.0f} | {s['steps']:.0f} | {given} |")
    out += ["", "| Paired comparison | Δ total input tokens per run (mean, 95% CI) | median per-issue ratio | Δ success (95% CI) | verdict (pre-registered rule) |",
            "|---|---|---|---|---|"]
    for k in ("graph-cold", "graph-notes", "notes-cold"):
        if k in ex:
            d = ex[k]
            a, b = k.split("-")
            out.append(f"| {LAB[a].split(' (')[0]} − {LAB[b].split(' (')[0]} | {d['dtok'][0]:+,.0f} [{d['dtok'][1]:+,.0f}, {d['dtok'][2]:+,.0f}] | "
                       f"{d['ratio']:.2f} | {d['dsucc'][0]:+.2f} [{d['dsucc'][1]:+.2f}, {d['dsucc'][2]:+.2f}] | {d['verdict']} |")
    return "\n".join(out)


def note_cost() -> dict:
    u = _rows(RUNS / "notes" / "usage.jsonl")
    if not u:
        return {}
    p = [x["prompt_tokens"] for x in u]
    c = [x["completion_tokens"] for x in u]
    sizes = [((RUNS / "notes" / f"{x['issue']}.md").stat().st_size + 3) // 4 for x in u if (RUNS / "notes" / f"{x['issue']}.md").exists()]
    return {"n": len(u), "prompt_total": sum(p), "completion_total": sum(c), "prompt_median": statistics.median(p),
            "completion_median": statistics.median(c), "note_tokens_median": statistics.median(sizes) if sizes else 0,
            "model": u[0]["model"],
            # list price of deepseek-v4.1-flash-fast on the provider's /v1/models: $0.01 / M input, $0.08 / M output
            "usd_list": round(sum(p) * 0.01e-6 + sum(c) * 0.08e-6, 4)}


def accumulation(ex: dict) -> list[dict]:
    """Per Experiment A target: how many earlier runs, the size of all their notes, the pack size."""
    out = []
    for r in _rows(RUNS / "results.jsonl"):
        if r["condition"] == "notes":
            out.append({"id": r["id"], "n_prior": r["n_prior"], "notes_tokens": r["note_tokens_on_disk"]})
    packs = {r["id"]: r["pack_tokens"] for r in _rows(RUNS / "results.jsonl") if r["condition"] == "graph"}
    for o in out:
        o["pack_tokens"] = packs.get(o["id"])
    return sorted(out, key=lambda o: o["n_prior"])


def memory_stats() -> dict:
    rs = [r for r in _rows(RUNS / "prior" / "results.jsonl") if not r["rate_limited"] and r["steps"] > 0]
    if not rs:
        return {}
    return {"n": len(rs), "succ": ci([r["success"] for r in rs]), "median_in": statistics.median(r["total_input"] for r in rs),
            "model": rs[0]["model"]}


def section() -> tuple[list[str], dict]:
    A = experiment(RUNS / "results.jsonl", rep=0)
    B = experiment(RUNS / "same" / "results.jsonl")
    nc = note_cost()
    mem = memory_stats()
    load = json.loads((RES / "handoff_load.json").read_text()) if (RES / "handoff_load.json").exists() else {}
    retr = (RES / "handoff_retrieval.txt").read_text() if (RES / "handoff_retrieval.txt").exists() else ""
    md = ["## Handoff graph (current product)", "",
          "Pre-registration: `bench/handoff_prereg.md` (committed before any live run on the targets). Code: "
          "`src/bearings/handoff.py`, `bench/handoff.py`.", ""]
    if mem:
        md += [f"Memory: {mem['n']} cold runs, one per SWE-bench Django issue dated 2021-01-01 to 2022-06-30 "
               f"(`{mem['model']}`), plus the 40 Level 2 runs as recorded knowledge only. Their own success: {fmt(mem['succ'], True)}; "
               f"median total input {mem['median_in']:,.0f} tokens.", ""]
    md += ["### Experiment A: the next agent, on a different issue (primary)", "", table(A), "",
           "### Experiment B: the next agent, on the same issue", "", table(B), ""]
    if nc:
        md += ["### What the handoff notes cost to write", "",
               f"{nc['n']} model calls (`{nc['model']}`), one per note, plus any retries (one first attempt looped and was regenerated; both count): {nc['prompt_total']:,} input and "
               f"{nc['completion_total']:,} output tokens in total (median {nc['prompt_median']:,.0f} in, "
               f"{nc['completion_median']:,.0f} out per note; a note is {nc['note_tokens_median']:,.0f} tokens). "
               f"List-price arithmetic: ${nc['usd_list']:.3f}. The graph's recorder makes no model call.", ""]
    accf = RES / "handoff_accumulation.json"
    acc = json.loads(accf.read_text()) if accf.exists() else []
    if acc:
        md += ["### Accumulation", "", "| recorded runs | handoff notes (files) | notes, total tokens | pack, median tokens (102 targets) |",
               "|---|---|---|---|"] + [f"| {a['runs']} | {a['notes_files']} | {a['notes_tokens']:,} | {a['pack_tokens_median']} |" for a in acc] + \
              ["", "File: `results/handoff_accumulation.json`.", ""]
    if retr:
        md += ["### Retrieval without model calls", "", "```", retr.strip(), "```", ""]
    if load:
        md += ["### Under load", "",
               f"{load['clients']} concurrent clients for {load['seconds']} s while a writer recorded "
               f"{load['runs_recorded_during_test']} runs into the same scope: {load['requests']:,} pack requests, "
               f"{load['errors']} errors, p50 {load['p50_ms']} ms, p95 {load['p95_ms']} ms ({load['rps']} packs/s). "
               f"Each pack is {load['calls_per_pack']}. File: `results/handoff_load.json`.", ""]
    data = {"A": _strip(A), "B": _strip(B), "notes_cost": nc, "memory": mem, "load": load,
            "accumulation": acc, "curve": curve()}
    return md, data


def _strip(ex: dict) -> dict:
    out = {k: v for k, v in ex.items() if k not in ("conds", "ids")}
    out["conds"] = {c: {k: v for k, v in s.items() if k != "tin"} for c, s in ex["conds"].items()}
    return out


def curve() -> list[dict]:
    rs = _rows(RES / "handoff_retrieval.jsonl")
    if not rs:
        return []
    out = []
    for k in sorted({int(k[5:]) for k in rs[0] if k.startswith("first")}):
        xs = [r[f"first{k}"]["both"] for r in rs]
        s = [r[f"first{k}"]["src"] for r in rs]
        t = [r[f"first{k}"]["test"] for r in rs]
        out.append({"runs": k, "both": ci(xs), "src": ci(s), "test": ci(t)})
    d = [r["dictionary"] for r in rs]
    out.append({"runs": "table", "both": ci([x["both"] for x in d]), "src": ci([x["src"] for x in d]),
                "test": ci([x["test"] for x in d])})
    return out
