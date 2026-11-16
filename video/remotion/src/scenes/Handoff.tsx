import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { C, MONO, Scene, SceneData, Swap, Kinetic, Eyebrow, Window, Chip, clamp, data, fmt, out, useSpring } from "../ui";
import { Bars } from "./Honest";

const H = () => data.handoff;
const short = (p: string) => p.split("/").slice(-2).join("/");

/** What we measured first: where the tokens of a live run go. */
export const Pivot: React.FC<{ sc: SceneData }> = ({ sc }) => {
  const frame = useCurrentFrame();
  const a2 = sc.lines.length > 1 ? sc.lines[1].from : Math.round(sc.frames * 0.45);
  const p = interpolate(frame, [20, 70], [0, 1], { ...clamp, easing: out });
  const share = H().pivot.after_pct; // e.g. 94
  const W = 1500;
  return (
    <Scene sc={sc}>
      <div style={{ position: "absolute", left: 120, top: 96, width: 1600 }}>
        <Eyebrow color={C.warn}>Where the tokens go</Eyebrow>
        <div style={{ height: 18 }} />
        <Kinetic text="Finding the right file is the cheap part." size={68} delay={4} accent={["cheap"]} />
      </div>
      <div style={{ position: "absolute", left: 210, top: 470, width: W }}>
        <div style={{ display: "flex", height: 120, borderRadius: 18, overflow: "hidden", border: `1px solid ${C.line}` }}>
          <div style={{ width: `${(100 - share) * p}%`, background: C.accent, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 28, fontWeight: 700, color: "#ffffff", whiteSpace: "nowrap" }}>
            {p > 0.6 ? `${100 - share}%` : ""}
          </div>
          <div style={{ flex: 1, background: `repeating-linear-gradient(135deg, ${C.warnSoft}, ${C.warnSoft} 14px, rgba(242,166,90,0.08) 14px, rgba(242,166,90,0.08) 28px)`, display: "flex", alignItems: "center", paddingLeft: 40, fontSize: 34, fontWeight: 700, color: C.warn, opacity: p }}>
            {share}% after the right file is open
          </div>
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", marginTop: 22, fontSize: 26, color: C.dim }}>
          <span>finding the file</span>
          <span>neighbouring code · hunting tests and docs · re-reading the fix file</span>
        </div>
        <div style={{ display: "flex", gap: 18, marginTop: 60, opacity: interpolate(frame, [a2, a2 + 20], [0, 1], clamp) }}>
          {H().pivot.parts.map((x: { label: string; pct: number }, i: number) => (
            <Chip key={i} color={C.warn} bg={C.warnSoft} delay={a2 + 6 + i * 6} style={{ fontSize: 30, padding: "12px 22px" }}>
              {x.pct}% {x.label}
            </Chip>
          ))}
        </div>
      </div>
      <div style={{ position: "absolute", left: 120, top: 974, fontSize: 22, color: C.faint }}>
        {H().pivot.source}
      </div>
    </Scene>
  );
};

/** A run becomes structure: tool calls on the left, the run's node and edges on the right. */
export const Record: React.FC<{ sc: SceneData }> = ({ sc }) => {
  const frame = useCurrentFrame();
  const R = H().record;
  const per = 9;
  const calls: string[] = R.calls;
  const shown = Math.max(0, Math.min(calls.length, Math.floor((frame - 20) / per) + 1));
  const reads: { f: string; lines: string; concluded?: boolean }[] = R.reads;
  const RX = 1150, RY = 560;
  const fy = (i: number) => 250 + i * (560 / Math.max(1, reads.length - 1));
  const a2 = sc.lines.length > 1 ? sc.lines[1].from : Math.round(sc.frames * 0.5);
  const noModel = interpolate(frame, [a2, a2 + 18], [0, 1], { ...clamp, easing: out });
  return (
    <Scene sc={sc}>
      <div style={{ position: "absolute", left: 120, top: 80 }}>
        <Eyebrow>HandoffDB records every run</Eyebrow>
        <div style={{ height: 14 }} />
        <Kinetic text="From its tool calls, as structure." size={64} delay={4} accent={["structure."]} />
      </div>
      <Window title={`agent run · ${R.issue}`} delay={8} style={{ left: 120, top: 250, width: 820, height: 690 }} bodyStyle={{ padding: "18px 24px" }}>
        {calls.slice(Math.max(0, shown - 11), shown).map((c, i, arr) => (
          <div key={i} style={{ fontFamily: MONO, fontSize: 20, lineHeight: "52px", height: 52, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", color: i === arr.length - 1 ? C.text : C.dim }}>
            <span style={{ color: C.accent }}>$ </span>
            {c}
          </div>
        ))}
      </Window>
      <svg style={{ position: "absolute", inset: 0 }} width={1920} height={1080}>
        {reads.map((r, i) => {
          const st = 30 + i * 10;
          const p = interpolate(frame, [st, st + 24], [0, 1], { ...clamp, easing: out });
          const x2 = 1380, y2 = fy(i);
          return (
            <g key={i} opacity={p}>
              <line x1={RX} y1={RY} x2={RX + (x2 - RX) * p} y2={RY + (y2 - RY) * p} stroke={r.concluded ? C.accent : "rgba(15,23,42,0.35)"} strokeWidth={r.concluded ? 4 : 2} />
              <circle cx={x2} cy={y2} r={9} fill={r.concluded ? C.accent : C.gray} />
            </g>
          );
        })}
        <circle cx={RX} cy={RY} r={56} fill={C.panel2} stroke={C.accent} strokeWidth={3} opacity={useSpring(14)} />
      </svg>
      <div style={{ position: "absolute", left: RX, top: RY, translate: "-50% -50%", fontFamily: MONO, fontSize: 24, color: C.accent, fontWeight: 700 }}>run</div>
      {reads.map((r, i) => {
        const p = interpolate(frame, [40 + i * 10, 60 + i * 10], [0, 1], clamp);
        return (
          <div key={i} style={{ position: "absolute", left: 1404, top: fy(i) - 22, maxWidth: 480, overflow: "hidden", opacity: p, fontFamily: MONO, fontSize: 21, whiteSpace: "nowrap", lineHeight: 1.15 }}>
            <div style={{ color: r.concluded ? C.accent : C.text }}>{short(r.f)}</div>
            <div style={{ color: C.faint, fontSize: 17 }}>{r.concluded ? "concluded: fix here" : r.lines ? `lines ${r.lines}` : r.f.startsWith("tests/") ? "test file" : "opened"}</div>
          </div>
        );
      })}
      <div style={{ position: "absolute", left: 1010, top: 900, opacity: noModel }}>
        <Chip delay={a2} style={{ fontSize: 30, padding: "12px 24px" }}>no model call · {H().record_ms} ms to record</Chip>
      </div>
    </Scene>
  );
};

/** The next task traverses: entities → earlier runs → files → their tests; the pack types out. */
export const Traverse: React.FC<{ sc: SceneData }> = ({ sc }) => {
  const frame = useCurrentFrame();
  const P = H().pack;
  const cols = [
    { x: 160, title: "the new task", items: P.terms.slice(0, 5) },
    { x: 560, title: "earlier runs", items: P.runs.slice(0, 4) },
    { x: 960, title: "files they opened", items: P.source.slice(0, 4).map(short) },
    { x: 1360, title: "tests they found", items: P.test.slice(0, 3).map(short) },
  ];
  const a2 = sc.lines.length > 1 ? sc.lines[1].from : Math.round(sc.frames * 0.55);
  const typed = interpolate(frame, [a2, a2 + 120], [0, P.text.length], clamp);
  const show = interpolate(frame, [a2 - 10, a2 + 10], [0, 1], clamp);
  return (
    <Scene sc={sc}>
      <div style={{ position: "absolute", left: 120, top: 80 }}>
        <Eyebrow>The next agent's task</Eyebrow>
        <div style={{ height: 14 }} />
        <Kinetic text="A few graph traversals. One small pack." size={64} delay={4} accent={["small", "pack."]} />
      </div>
      <div style={{ opacity: 1 - show * 0.85 }}>
        {cols.map((c, ci) => (
          <div key={ci} style={{ position: "absolute", left: c.x, top: 300, width: 360 }}>
            <div style={{ fontSize: 24, color: C.dim, marginBottom: 18, opacity: interpolate(frame, [10 + ci * 14, 24 + ci * 14], [0, 1], clamp) }}>{c.title}</div>
            {c.items.map((t: string, i: number) => {
              const st = 16 + ci * 16 + i * 4;
              const p = interpolate(frame, [st, st + 16], [0, 1], { ...clamp, easing: out });
              return (
                <div key={i} style={{ opacity: p, translate: `${(1 - p) * -20}px 0px`, fontFamily: MONO, fontSize: 21, padding: "12px 16px", marginBottom: 12, borderRadius: 12, background: ci === 3 || ci === 2 && i === 0 ? C.accentSoft : C.panel2, border: `1px solid ${ci === 3 || (ci === 2 && i === 0) ? C.accent + "88" : C.line}`, color: ci === 0 ? C.dim : C.text, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                  {t}
                </div>
              );
            })}
          </div>
        ))}
        <svg style={{ position: "absolute", inset: 0 }} width={1920} height={1080}>
          {[0, 1, 2].map((k) => {
            const p = interpolate(frame, [30 + k * 16, 50 + k * 16], [0, 1], { ...clamp, easing: out });
            const x1 = cols[k].x + 330, x2 = cols[k + 1].x - 10;
            return <line key={k} x1={x1} y1={420} x2={x1 + (x2 - x1) * p} y2={420} stroke={C.accent} strokeWidth={4} strokeLinecap="round" />;
          })}
        </svg>
      </div>
      <Window title={`handoff pack · ${P.id}`} delay={a2 - 10} style={{ left: 260, top: 280, width: 1400, height: 660, opacity: show }} bodyStyle={{ padding: "22px 30px" }}
        right={<div style={{ fontFamily: MONO, fontSize: 20, color: C.accent }}>{fmt(P.tokens)} tokens</div>}>
        <div style={{ fontFamily: MONO, fontSize: 20, lineHeight: "34px", whiteSpace: "pre-wrap", color: C.text }}>{P.text.slice(0, Math.floor(typed))}</div>
      </Window>
    </Scene>
  );
};

/** Live agents: same issue (success) first, then brand-new issues (tokens). */
export const Results: React.FC<{ sc: SceneData }> = ({ sc }) => {
  const frame = useCurrentFrame();
  const R = H().results;
  const a2 = sc.lines.length > 1 ? sc.lines[1].from : Math.round(sc.frames / 2);
  const color = (k: string) => (k === "graph" ? C.accent : k === "notes" ? C.warn : C.gray);
  const rowsA = R.A.map((r: any) => ({ label: r.label, value: r.median_in, text: "", color: color(r.key), note: undefined }));
  const max = Math.max(...rowsA.map((r: any) => r.value)) * 1.25;
  return (
    <Scene sc={sc}>
      <div style={{ position: "absolute", left: 120, top: 96, width: 1650 }}>
        <Swap at={0} until={a2}>
          <Eyebrow>{R.titleB}</Eyebrow>
          <div style={{ height: 18 }} />
          <Kinetic text={R.headB} size={64} delay={4} accent={R.accentB} />
        </Swap>
        <Swap at={a2}>
          <Eyebrow>{R.titleA}</Eyebrow>
          <div style={{ height: 18 }} />
          <Kinetic text={R.headA} size={64} accent={R.accentA} />
        </Swap>
      </div>
      <Swap at={0} until={a2}>
        {R.B.map((r: any, i: number) => {
          const p = interpolate(frame, [20 + i * 8, 56 + i * 8], [0, 1], { ...clamp, easing: out });
          const g = r.key === "graph";
          return (
            <div key={i} style={{ position: "absolute", left: 120, top: 400 + i * 110, width: 1680, height: 80, display: "flex", alignItems: "center", gap: 24 }}>
              <div style={{ width: 380, textAlign: "right", fontSize: 30, color: g ? C.accent : C.text, fontWeight: g ? 700 : 500 }}>{r.label}</div>
              <div style={{ flex: 1, height: 64, position: "relative", background: "rgba(15,23,42,0.05)", borderRadius: 14 }}>
                <div style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: `${r.succ * 100 * p}%`, background: g ? C.accent : r.key === "notes" ? "#fdba74" : C.gray, borderRadius: 14, boxShadow: g ? `0 0 30px ${C.accent}44` : undefined }} />
                <div style={{ position: "absolute", left: `calc(${r.succ * 100 * p}% + 18px)`, top: 10, fontFamily: MONO, fontSize: 36, fontWeight: 800, color: g ? C.accent : C.dim }}>{String(Math.round(r.succ * 1000 * p) / 10)}%</div>
              </div>
            </div>
          );
        })}
        <div style={{ position: "absolute", left: 120, top: 760, fontSize: 26, color: C.dim, width: 1680 }}>{R.subB}</div>
      </Swap>
      <Swap at={a2}>
        <Bars rows={rowsA} max={max} start={a2 + 10} left={120} top={420} width={1680} labelW={380} />
        <div style={{ position: "absolute", left: 120, top: 760, fontSize: 26, color: C.dim, width: 1680 }}>{R.subA}</div>
      </Swap>
      <div style={{ position: "absolute", left: 120, top: 974, fontSize: 22, color: C.faint }}>{R.foot}</div>
    </Scene>
  );
};

/** Notes pile up; the pack stays small. */
export const Pile: React.FC<{ sc: SceneData }> = ({ sc }) => {
  const frame = useCurrentFrame();
  const acc: { n_prior: number; notes_tokens: number; pack_tokens: number }[] = H().acc.map((a: any) => ({ n_prior: a.runs, notes_tokens: a.notes_tokens, pack_tokens: a.pack_tokens_median }));
  const L = 200, T = 330, W = 1400, Ht = 520;
  const x1 = Math.max(...acc.map((a) => a.n_prior));
  const y1 = Math.max(...acc.map((a) => a.notes_tokens)) * 1.08;
  const sx = (x: number) => L + (x / x1) * W, sy = (y: number) => T + (1 - y / y1) * Ht;
  const p = interpolate(frame, [20, 110], [0, 1], { ...clamp, easing: out });
  const vis = acc.filter((a) => a.n_prior <= x1 * p);
  const last = vis[vis.length - 1] || acc[0];
  const path = (k: "notes_tokens" | "pack_tokens") => vis.map((a) => `${sx(a.n_prior)},${sy(a[k])}`).join(" ");
  return (
    <Scene sc={sc}>
      <div style={{ position: "absolute", left: 120, top: 96 }}>
        <Eyebrow color={C.warn}>As runs pile up</Eyebrow>
        <div style={{ height: 18 }} />
        <Kinetic text="Notes grow without limit. The pack does not." size={64} delay={4} accent={["pack", "does", "not."]} />
      </div>
      <svg style={{ position: "absolute", inset: 0 }} width={1920} height={1080}>
        {[0, 0.25, 0.5, 0.75, 1].map((f, i) => (
          <g key={i}>
            <line x1={L} x2={L + W} y1={sy(y1 * f)} y2={sy(y1 * f)} stroke="rgba(15,23,42,0.07)" />
            <text x={L - 16} y={sy(y1 * f) + 8} fill={C.faint} fontSize={22} textAnchor="end" fontFamily={MONO}>{Math.round((y1 * f) / 1000)}k</text>
          </g>
        ))}
        <polyline points={path("notes_tokens")} fill="none" stroke={C.warn} strokeWidth={5} strokeLinejoin="round" />
        <polyline points={path("pack_tokens")} fill="none" stroke={C.accent} strokeWidth={5} strokeLinejoin="round" />
        <text x={L + W / 2} y={T + Ht + 60} fill={C.dim} fontSize={24} textAnchor="middle">earlier agent runs on the repository</text>
      </svg>
      <div style={{ position: "absolute", left: sx(last.n_prior) - 520, top: sy(last.notes_tokens) - 70, width: 500, textAlign: "right", fontSize: 30, fontWeight: 700, color: C.warn }}>
        {fmt(last.notes_tokens)} tokens of notes · {last.n_prior} files
      </div>
      <div style={{ position: "absolute", left: sx(last.n_prior) - 520, top: sy(last.pack_tokens) - 64, width: 500, textAlign: "right", fontSize: 30, fontWeight: 700, color: C.accent }}>
        a {fmt(last.pack_tokens)}-token pack
      </div>
      <div style={{ position: "absolute", left: 120, top: 974, fontSize: 22, color: C.faint }}>{H().acc_foot}</div>
    </Scene>
  );
};
