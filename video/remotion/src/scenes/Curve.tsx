import React from "react";
import { Easing, interpolate, useCurrentFrame } from "remotion";
import { C, MONO, Scene, SceneData, Kinetic, Eyebrow, Stat, at, clamp, data } from "../ui";

const pct = (x: number) => Math.round(x * 100);
const AMBER = "#eab308";

/** Rolling top-5 hit rate over the task stream, empty start (bench/report.py rep.curve). */
const Chart: React.FC<{ start: number; frozenAt: number }> = ({ start, frozenAt }) => {
  const frame = useCurrentFrame();
  const series: Record<string, [number, number][]> = data.learn.series;
  const lo = 0.2, hi = 0.8;
  const W = 1120, H = 600, L = 90, R = 30, T = 30, B = 70;
  const xmax = 850;
  const sx = (x: number) => L + (x / xmax) * (W - L - R);
  const sy = (y: number) => T + ((hi - y) / (hi - lo)) * (H - T - B);
  const draw = (k: string, s0: number, len: number) => {
    const p = interpolate(frame, [s0, s0 + len], [0, 1], { ...clamp, easing: Easing.bezier(0.45, 0, 0.25, 1) });
    const pts = series[k];
    const d = pts.map(([x, y], i) => `${i ? "L" : "M"}${sx(x).toFixed(1)},${sy(y).toFixed(1)}`).join(" ");
    const last = pts[Math.max(0, Math.min(pts.length - 1, Math.floor(p * (pts.length - 1))))];
    return { d, p, last };
  };
  const lines = [
    { k: "bm25", color: C.gray, label: "Keyword search", s0: start, dash: undefined as string | undefined, w: 4 },
    { k: "bearings", color: C.accent, label: "Bearings", s0: start, dash: undefined, w: 6 },
    { k: "frozen", color: AMBER, label: "Same graph, frozen", s0: frozenAt, dash: "12 10", w: 4 },
  ];
  return (
    <svg width={W} height={H} style={{ position: "absolute", left: 80, top: 400, overflow: "visible" }}>
      {[0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8].map((y) => (
        <g key={y}>
          <line x1={L} x2={W - R} y1={sy(y)} y2={sy(y)} stroke="rgba(15,23,42,0.07)" />
          <text x={L - 16} y={sy(y) + 7} textAnchor="end" fill={C.faint} fontFamily={MONO} fontSize={20}>
            {Math.round(y * 100)}%
          </text>
        </g>
      ))}
      {[0, 200, 400, 600, 800].map((x) => (
        <text key={x} x={sx(x)} y={H - B + 36} textAnchor="middle" fill={C.faint} fontFamily={MONO} fontSize={20}>
          {x}
        </text>
      ))}
      <text x={(L + W - R) / 2} y={H - 4} textAnchor="middle" fill={C.dim} fontSize={22}>
        issues learned so far · top-5 hit rate, rolling 100
      </text>
      {lines.map((l, i) => {
        const o = interpolate(frame, [l.s0, l.s0 + 15], [0, 1], clamp);
        return (
          <g key={`lg-${l.k}`} opacity={o} transform={`translate(${L + 10 + i * 300}, ${-40})`}>
            <line x1={0} x2={44} y1={0} y2={0} stroke={l.color} strokeWidth={l.w} strokeDasharray={l.dash} strokeLinecap="round" />
            <text x={58} y={9} fill={l.color} fontSize={26} fontWeight={600}>
              {l.label}
            </text>
          </g>
        );
      })}
      {lines.map((l) => {
        const { d, p, last } = draw(l.k, l.s0, 75);
        if (p <= 0) return null;
        return (
          <g key={l.k}>
            <clipPath id={`clip-${l.k}`}>
              <rect x={0} y={0} width={sx(last[0]) + 2} height={H} />
            </clipPath>
            <path d={d} fill="none" stroke={l.color} strokeWidth={l.w} strokeLinejoin="round" strokeLinecap="round" strokeDasharray={l.dash} clipPath={`url(#clip-${l.k})`} />
            <circle cx={sx(last[0])} cy={sy(last[1])} r={9} fill={l.color} />
          </g>
        );
      })}
    </svg>
  );
};

export const Curve: React.FC<{ sc: SceneData }> = ({ sc }) => {
  const fz = at(sc, "08b");
  const T = data.learn.m.tasks;
  const gain = ((T.bearings["hit@5"] - T.frozen["hit@5"]) * 100).toFixed(1);
  return (
    <Scene sc={sc}>
      <div style={{ position: "absolute", left: 120, top: 96 }}>
        <Eyebrow>Starting from an empty graph</Eyebrow>
        <div style={{ height: 18 }} />
        <Kinetic text="It learns as issues arrive." size={80} delay={4} accent={["learns"]} />
      </div>
      <Chart start={24} frozenAt={fz + 4} />
      <div style={{ position: "absolute", left: 1330, top: 360, width: 470, display: "flex", flexDirection: "column", gap: 30 }}>
        <Stat
          value={pct(T.bearings["hit@5"])}
          delay={70}
          label={
            <>
              real fix in the top five
              <br />
              keyword search: {pct(T.bm25["hit@5"])}%
            </>
          }
        />
        <Stat
          value={Number(gain)}
          suffix=" pts"
          decimals={1}
          size={96}
          delay={fz + 40}
          color={AMBER}
          label={<>over the same graph, frozen: the gain from learning</>}
        />
      </div>
      <div style={{ position: "absolute", left: 120, bottom: 50, fontSize: 22, color: C.faint }}>
        724 scored issues, each answered before its own fix is learned. Paired difference vs keyword search: +15.6 points [+11.3, +19.8].
      </div>
    </Scene>
  );
};

