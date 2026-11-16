import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { C, MONO, Scene, SceneData, Window, Kinetic, Eyebrow, at, clamp, data, out, useSpring } from "../ui";

type F = { path: string; why: string[]; lines?: [number, string][] };

const parseWhy = (w: string) => {
  const m = w.match(/^(symbol|word) '([^']+)' -> (\S+) \(together in (\d+) past changes?\)/);
  return m ? { kind: m[1], term: m[2], path: m[3], n: Number(m[4]) } : null;
};

/** The pack as text segments; `anchor` segments are the line numbers from code anchors. */
const packLines = (files: F[], test: string) => {
  const rows: { seg: { t: string; anchor?: boolean; dim?: boolean; file?: boolean }[] }[] = [{ seg: [{ t: "Start in:" }] }];
  files.slice(0, 3).forEach((f, i) => {
    const seg: { t: string; anchor?: boolean; dim?: boolean; file?: boolean }[] = [{ t: `${i + 1}. ` }, { t: f.path, file: true }];
    rows.push({ seg });
    if (f.lines && f.lines.length) {
      const ls = f.lines.slice(0, 2);
      const s2: { t: string; anchor?: boolean; dim?: boolean }[] = [{ t: "   defines ", dim: true }];
      ls.forEach(([n, name], j) => {
        s2.push({ t: `${name} ` });
        s2.push({ t: `line ${n}`, anchor: true });
        if (j < ls.length - 1) s2.push({ t: ", ", dim: true });
      });
      if (f.lines.length > 2) s2.push({ t: ", …", dim: true });
      rows.push({ seg: s2 });
    }
    const why = f.why.find((w) => !w.startsWith("defines"));
    const p = why ? parseWhy(why) : null;
    if (p) rows.push({ seg: [{ t: `   because ${p.kind} '${p.term}' → here, in ${p.n} past changes`, dim: true }] });
  });
  rows.push({ seg: [{ t: "" }] });
  rows.push({ seg: [{ t: "Verify with: " }, { t: test, file: true }] });
  return rows;
};

const Pack: React.FC<{ start: number; anchorAt: number }> = ({ start, anchorAt }) => {
  const frame = useCurrentFrame();
  const rows = packLines(data.query.files, data.query.test);
  const total = rows.reduce((a, r) => a + r.seg.reduce((b, s) => b + s.t.length, 0) + 1, 0);
  const typed = interpolate(frame, [start, start + 150], [0, total], clamp);
  const glow = interpolate(frame, [anchorAt, anchorAt + 16], [0, 1], { ...clamp, easing: out });
  let used = 0;
  return (
    <Window
      title="context pack · django__django-15916"
      delay={start - 10}
      glow={glow * 0.6}
      style={{ left: 840, top: 360, width: 960, height: 600 }}
      bodyStyle={{ padding: "26px 32px" }}
      right={<div style={{ fontFamily: MONO, fontSize: 20, color: C.accent }}>≈350 tokens</div>}
    >
      {rows.map((r, i) => {
        const row = r.seg.map((s, j) => {
          const vis = Math.max(0, Math.min(s.t.length, typed - used));
          used += s.t.length;
          const txt = s.t.slice(0, Math.floor(vis));
          if (!txt) return null;
          return (
            <span
              key={j}
              style={{
                color: s.anchor ? "#ffffff" : s.file ? C.accent : s.dim ? C.dim : C.text,
                background: s.anchor ? `rgba(2,132,199,${0.25 + 0.75 * glow})` : undefined,
                borderRadius: 6,
                padding: s.anchor ? "1px 6px" : undefined,
                fontWeight: s.anchor ? 700 : 400,
              }}
            >
              {txt}
            </span>
          );
        });
        used += 1;
        return (
          <div key={i} style={{ fontFamily: MONO, fontSize: 23, lineHeight: "40px", minHeight: 40, whiteSpace: "pre", overflow: "hidden" }}>
            {row}
          </div>
        );
      })}
    </Window>
  );
};

const Route: React.FC<{ start: number }> = ({ start }) => {
  const frame = useCurrentFrame();
  const files: F[] = data.query.files.slice(0, 3);
  const edges = files.flatMap((f) => f.why.map(parseWhy).filter(Boolean).slice(0, 2)) as { kind: string; term: string; path: string; n: number }[];
  const terms = Array.from(new Set(edges.map((e) => e.term))).filter((t) => t.length <= 18).slice(0, 5);
  const ed = edges.filter((e) => terms.includes(e.term));
  const TX = 40, FX = 420;
  const ty = (i: number) => 60 + i * 96;
  const fy = (i: number) => 110 + i * 150;
  const short = (p: string) => p.split("/").slice(-2).join("/");
  return (
    <Window title="one weighted path query · HydraDB" delay={start - 14} style={{ left: 120, top: 360, width: 680, height: 600 }} bodyStyle={{ padding: 0 }}>
      <svg width={680} height={540}>
        {ed.map((e, k) => {
          const i = terms.indexOf(e.term);
          const j = files.findIndex((f) => f.path === e.path);
          const st = start + 10 + k * 9;
          const p = interpolate(frame, [st, st + 22], [0, 1], { ...clamp, easing: out });
          const x1 = TX + 200, y1 = ty(i), x2 = FX, y2 = fy(j);
          const d = `M${x1},${y1} C${x1 + 90},${y1} ${x2 - 90},${y2} ${x2},${y2}`;
          const best = j === 0;
          return (
            <path
              key={k}
              d={d}
              fill="none"
              stroke={best ? C.accent : "rgba(15,23,42,0.35)"}
              strokeWidth={best ? 2 + Math.log(e.n + 1) * 1.6 : 1.5 + Math.log(e.n + 1) * 0.7}
              pathLength={1}
              strokeDasharray={1}
              strokeDashoffset={1 - p}
              opacity={best ? 1 : 0.7}
            />
          );
        })}
        {terms.map((t, i) => (
          <g key={t} opacity={interpolate(frame, [start + i * 4, start + 10 + i * 4], [0, 1], clamp)}>
            <rect x={TX - 10} y={ty(i) - 24} width={220} height={48} rx={12} fill={C.accentSoft} stroke={`${C.accent}55`} />
            <text x={TX + 100} y={ty(i) + 8} textAnchor="middle" fill={C.accent} fontFamily={MONO} fontSize={t.length > 14 ? 18 : 22}>
              {t}
            </text>
          </g>
        ))}
        {files.map((f, j) => {
          const o = interpolate(frame, [start + 30 + j * 8, start + 44 + j * 8], [0, 1], clamp);
          return (
            <g key={f.path} opacity={o}>
              <rect x={FX} y={fy(j) - 30} width={230} height={60} rx={14} fill={j === 0 ? C.accent : C.panel2} stroke={j === 0 ? C.accent : C.line} />
              <text x={FX + 115} y={fy(j) + 8} textAnchor="middle" fill={j === 0 ? "#ffffff" : C.text} fontFamily={MONO} fontSize={19} fontWeight={j === 0 ? 700 : 400}>
                {short(f.path)}
              </text>
            </g>
          );
        })}
      </svg>
    </Window>
  );
};

export const Query: React.FC<{ sc: SceneData }> = ({ sc }) => {
  const a6 = at(sc, "05b");
  const s = useSpring(4);
  const task: string = data.query.task;
  const hi = ["ModelForm", "formfield_callback"];
  return (
    <Scene sc={sc}>
      <div style={{ position: "absolute", left: 120, top: 80 }}>
        <Eyebrow>A new task arrives</Eyebrow>
      </div>
      <div
        style={{
          position: "absolute",
          left: 120,
          top: 140,
          width: 1680,
          padding: "30px 40px",
          borderRadius: 22,
          background: C.panel,
          border: `1px solid ${C.line}`,
          opacity: s,
          translate: `0px ${(1 - s) * 30}px`,
          boxShadow: "0 30px 70px rgba(15,23,42,0.12)",
        }}
      >
        <div style={{ fontFamily: MONO, fontSize: 21, color: C.faint, marginBottom: 10 }}>SWE-bench django__django-15916 · the graph never saw it</div>
        <div style={{ fontSize: 50, fontWeight: 650, letterSpacing: "-0.02em" }}>
          {task.split(/(\s+)/).map((w, i) => {
            const k = w.replace(/[.,]/g, "");
            return (
              <span key={i} style={hi.includes(k) ? { color: C.accent, background: C.accentSoft, borderRadius: 8, padding: "0 6px" } : undefined}>
                {w}
              </span>
            );
          })}
        </div>
      </div>
      <Route start={36} />
      <Pack start={90} anchorAt={a6} />
      <div style={{ position: "absolute", left: 120, top: 990, fontSize: 24, color: C.dim }}>
        The real pack. The real fix changed <span style={{ color: C.accent, fontFamily: MONO }}>{data.query.gold[0]}</span>: ranked first.
      </div>
      <div style={{ position: "absolute", right: 120, top: 990, opacity: interpolate(useCurrentFrame(), [a6, a6 + 14], [0, 1], clamp) }}>
        <Kinetic text="Exact lines, from today's code." size={30} weight={600} color={C.accent} delay={a6} />
      </div>
    </Scene>
  );
};
