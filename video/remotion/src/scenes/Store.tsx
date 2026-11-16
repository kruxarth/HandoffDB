import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { C, MONO, Scene, SceneData, Swap, Kinetic, Eyebrow, Chip, clamp, data, fmt, out } from "../ui";

const S = () => data.handoff.store;

// deterministic pseudo-random
const rnd = (i: number) => {
  const x = Math.sin(i * 127.1 + 311.7) * 43758.5453;
  return x - Math.floor(x);
};

type Nd = { x: number; y: number; col: number; order: number };
const COLS = [
  { name: "words", color: C.accent, n: 6 },
  { name: "runs", color: C.teal, n: 9 },
  { name: "files", color: C.warn, n: 8 },
  { name: "tests", color: C.green, n: 5 },
];

const buildNet = (L: number, T: number, W: number, H: number) => {
  const nodes: Nd[] = [];
  COLS.forEach((c, ci) => {
    for (let i = 0; i < c.n; i++) {
      const y = T + ((i + 0.5) / c.n) * H + (rnd(ci * 31 + i) - 0.5) * 28;
      const x = L + (ci / (COLS.length - 1)) * W + (rnd(ci * 17 + i * 3) - 0.5) * 60;
      nodes.push({ x, y, col: ci, order: rnd(ci * 7 + i * 13) });
    }
  });
  const edges: [number, number][] = [];
  const byCol = (ci: number) => nodes.map((n, i) => [n, i] as const).filter(([n]) => n.col === ci).map(([, i]) => i);
  for (let ci = 0; ci < COLS.length - 1; ci++) {
    const a = byCol(ci), b = byCol(ci + 1);
    a.forEach((ai, k) => {
      const m = 2 + Math.floor(rnd(ai * 5 + k) * 2);
      for (let j = 0; j < m; j++) edges.push([ai, b[Math.floor(rnd(ai * 11 + j * 7 + ci) * b.length)]]);
    });
    b.forEach((bi) => {
      if (!edges.some(([, t]) => t === bi)) edges.push([a[Math.floor(rnd(bi * 3) * a.length)], bi]);
    });
  }
  return { nodes, edges };
};

/** A living graph: `grow` (0..1) reveals nodes; pulses run along edges. */
const Network: React.FC<{ L: number; T: number; W: number; H: number; grow: number; pulse: number; hot?: boolean }> = ({ L, T, W, H, grow, pulse, hot }) => {
  const frame = useCurrentFrame();
  const { nodes, edges } = React.useMemo(() => buildNet(L, T, W, H), [L, T, W, H]);
  const vis = (i: number) => nodes[i].col === 0 || nodes[i].order <= grow;
  return (
    <svg style={{ position: "absolute", inset: 0 }} width={1920} height={1080}>
      {COLS.map((c, ci) => (
        <text key={ci} x={L + (ci / (COLS.length - 1)) * W} y={T - 34} textAnchor="middle" fill={c.color} fontSize={24} fontWeight={700} fontFamily={MONO}>
          {c.name}
        </text>
      ))}
      {edges.map(([a, b], k) => {
        if (!vis(a) || !vis(b)) return null;
        const A = nodes[a], B = nodes[b];
        const t = ((frame * 0.018 + rnd(k * 9)) % 1);
        const px = A.x + (B.x - A.x) * t, py = A.y + (B.y - A.y) * t;
        return (
          <g key={k}>
            <line x1={A.x} y1={A.y} x2={B.x} y2={B.y} stroke={COLS[A.col].color} strokeOpacity={0.28} strokeWidth={2.5} />
            {pulse > 0 && rnd(k * 2 + 1) < pulse ? <circle cx={px} cy={py} r={5} fill={COLS[A.col + 1].color} opacity={0.9} /> : null}
          </g>
        );
      })}
      {nodes.map((n, i) => {
        if (!vis(i)) return null;
        const r = 13 + (hot ? 3 * Math.sin(frame / 8 + i) : 0);
        return (
          <g key={i}>
            <circle cx={n.x} cy={n.y} r={r + 9} fill={COLS[n.col].color} opacity={0.14} />
            <circle cx={n.x} cy={n.y} r={r} fill="#ffffff" stroke={COLS[n.col].color} strokeWidth={5} />
          </g>
        );
      })}
    </svg>
  );
};

/** Plain store vs graph, the learning curve, and load. */
const StoreBase: React.FC<{ sc: SceneData; load?: boolean }> = ({ sc, load }) => {
  const frame = useCurrentFrame();
  const st = S();
  const a2 = load ? -10000 : sc.lines.length > 1 ? sc.lines[1].from : Math.round(sc.frames / 2);
  const a3 = load ? 0 : sc.frames + 10000;
  const curveP = interpolate(frame, [a2 + 10, a2 + 150], [0, 1], { ...clamp, easing: out });
  const grow = frame < a2 ? 1 : frame < a3 ? curveP : 1;
  const pulse = frame < a3 ? 0.35 : 1;

  const max = 0.4;
  const barColors = [C.gray, "#7dd3fc", C.accent];

  // curve geometry
  const L = 1040, T = 340, W = 740, Ht = 460;
  const xs = st.curve.map((c: number[]) => c[0]);
  const x1 = Math.max(...xs);
  const sx = (x: number) => L + (x / x1) * W, sy = (y: number) => T + (1 - y / max) * Ht;
  const vis = st.curve.filter((c: number[]) => c[0] <= x1 * curveP);
  const lastV = vis[vis.length - 1] || st.curve[0];
  const head = lastV;

  const ld = st.load;
  const cnt = (v: number) => Math.round(interpolate(frame, [a3 + 10, a3 + 90], [0, v], { ...clamp, easing: out }));

  return (
    <Scene sc={sc}>
      <div style={{ position: "absolute", left: 120, top: 80, width: 1700 }}>
        {!load && <Swap at={0} until={a2}>
          <Eyebrow color={C.warn}>Would a plain store do?</Eyebrow>
          <div style={{ height: 14 }} />
          <Kinetic text="A word → file table finds less." size={62} delay={4} accent={["less."]} />
        </Swap>}
        {!load && <Swap at={a2} until={a3}>
          <Eyebrow color={C.teal}>It keeps learning</Eyebrow>
          <div style={{ height: 14 }} />
          <Kinetic text="More recorded runs, better packs." size={62} accent={["better", "packs."]} />
        </Swap>}
        <Swap at={a3}>
          <Eyebrow color={C.green}>Under load</Eyebrow>
          <div style={{ height: 14 }} />
          <Kinetic text="Twenty agents at once. No errors." size={62} accent={["No", "errors."]} />
        </Swap>
      </div>

      <Network L={180} T={360} W={680} H={520} grow={grow} pulse={pulse} hot={frame >= a3} />

      {!load && <Swap at={0} until={a2}>
        {st.bars.map((b: { label: string; v: number }, i: number) => {
          const p = interpolate(frame, [24 + i * 10, 60 + i * 10], [0, 1], { ...clamp, easing: out });
          const top = 380 + i * 150;
          return (
            <div key={i} style={{ position: "absolute", left: 1040, top, width: 760 }}>
              <div style={{ fontSize: 28, color: i === 2 ? C.accent : C.text, fontWeight: i === 2 ? 700 : 500, marginBottom: 12 }}>{b.label}</div>
              <div style={{ height: 56, position: "relative", background: "rgba(15,23,42,0.05)", borderRadius: 12 }}>
                <div style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: `${(b.v / max) * 100 * p}%`, background: barColors[i], borderRadius: 12 }} />
                <div style={{ position: "absolute", left: `calc(${(b.v / max) * 100 * p}% + 16px)`, top: 8, fontFamily: MONO, fontSize: 30, fontWeight: 700, color: i === 2 ? C.accent : C.dim, opacity: p }}>
                  {Math.round(b.v * 100)}%
                </div>
              </div>
            </div>
          );
        })}
      </Swap>}

      {!load && <Swap at={a2} until={a3}>
        <svg style={{ position: "absolute", left: 0, top: 0 }} width={1920} height={1080}>
          {[0, 0.1, 0.2, 0.3, 0.4].map((f, i) => (
            <g key={i}>
              <line x1={L} x2={L + W} y1={sy(f)} y2={sy(f)} stroke="rgba(15,23,42,0.08)" />
              <text x={L - 14} y={sy(f) + 8} fill={C.faint} fontSize={22} textAnchor="end" fontFamily={MONO}>{Math.round(f * 100)}%</text>
            </g>
          ))}
          {xs.map((x: number, i: number) => (
            <text key={i} x={sx(x)} y={T + Ht + 40} fill={C.faint} fontSize={20} textAnchor="middle" fontFamily={MONO}>{x}</text>
          ))}
          <polygon points={`${sx(0)},${sy(0)} ${vis.map((c: number[]) => `${sx(c[0])},${sy(c[1])}`).join(" ")} ${sx(head[0])},${sy(0)}`} fill={C.teal} opacity={0.14} />
          <polyline points={vis.map((c: number[]) => `${sx(c[0])},${sy(c[1])}`).join(" ")} fill="none" stroke={C.teal} strokeWidth={6} strokeLinejoin="round" strokeLinecap="round" />
          {vis.map((c: number[], i: number) => (
            <circle key={i} cx={sx(c[0])} cy={sy(c[1])} r={9} fill="#ffffff" stroke={C.teal} strokeWidth={4} />
          ))}
          <text x={L + W / 2} y={T + Ht + 82} fill={C.dim} fontSize={24} textAnchor="middle">recorded runs</text>
        </svg>
        <div style={{ position: "absolute", left: sx(head[0]) - 180, top: sy(head[1]) - 70, width: 170, textAlign: "right", fontFamily: MONO, fontSize: 34, fontWeight: 700, color: C.teal }}>
          {Math.round(head[1] * 100)}%
        </div>
      </Swap>}

      <Swap at={a3}>
        <div style={{ position: "absolute", left: 1040, top: 370, width: 760, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 26 }}>
          {[
            { v: fmt(cnt(ld.requests)), l: "packs served in a minute", c: C.accent },
            { v: String(ld.errors), l: "errors", c: C.green },
            { v: `${(ld.p50_ms / 1000).toFixed(1)} s`, l: "median per pack", c: C.warn },
            { v: String(cnt(ld.runs_recorded_during_test)), l: "runs recorded meanwhile", c: C.teal },
          ].map((k, i) => (
            <div key={i} style={{ background: "#ffffff", border: `2px solid ${k.c}55`, borderRadius: 22, padding: "26px 28px", boxShadow: "0 12px 30px rgba(15,23,42,0.08)", opacity: interpolate(frame, [a3 + 6 + i * 6, a3 + 20 + i * 6], [0, 1], clamp) }}>
              <div style={{ fontFamily: MONO, fontSize: 62, fontWeight: 800, color: k.c }}>{k.v}</div>
              <div style={{ fontSize: 26, color: C.dim, marginTop: 6 }}>{k.l}</div>
            </div>
          ))}
        </div>
        <div style={{ position: "absolute", left: 1040, top: 790, width: 800 }}>
          <Chip delay={a3 + 40} color={C.dim} bg="rgba(15,23,42,0.05)" style={{ fontSize: 22, padding: "10px 18px", whiteSpace: "nowrap" }}>
            slowest 1 in 20: {(ld.p95_ms / 1000).toFixed(1)} s · one client alone: 0.2 s
          </Chip>
        </div>
      </Swap>

      <div style={{ position: "absolute", left: 120, top: 974, fontSize: 22, color: C.faint }}>{load ? "20 concurrent clients for 60 s while new runs were recorded (results/handoff_load.json)" : st.foot}</div>
    </Scene>
  );
};

export const Store: React.FC<{ sc: SceneData }> = ({ sc }) => <StoreBase sc={sc} />;
export const Load: React.FC<{ sc: SceneData }> = ({ sc }) => <StoreBase sc={sc} load />;
