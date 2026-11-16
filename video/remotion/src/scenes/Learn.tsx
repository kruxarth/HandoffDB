import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { C, MONO, Scene, SceneData, Kinetic, Eyebrow, Chip, clamp, out, useSpring } from "../ui";

// Edge cost from the README: w = ln(1000 / n) + ln(1 + miss). Lower = stronger.
const w = (n: number, miss: number) => Math.log(1000 / n) + Math.log(1 + miss);

const Box: React.FC<{ x: number; y: number; title: string; sub: string; color: string; delay: number }> = ({ x, y, title, sub, color, delay }) => {
  const s = useSpring(delay, 14);
  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y,
        translate: "-50% -50%",
        opacity: Math.min(1, s * 1.5),
        scale: String(0.7 + 0.3 * Math.min(1.05, s)),
        padding: "22px 30px",
        borderRadius: 20,
        background: C.panel2,
        border: `1.5px solid ${color}77`,
        boxShadow: `0 30px 60px rgba(0,0,0,0.5), 0 0 40px ${color}22`,
        textAlign: "center",
        minWidth: 320,
      }}
    >
      <div style={{ fontFamily: MONO, fontSize: 30, color }}>{title}</div>
      <div style={{ fontSize: 24, color: C.dim, marginTop: 6 }}>{sub}</div>
    </div>
  );
};

export const Learn: React.FC<{ sc: SceneData }> = ({ sc }) => {
  const frame = useCurrentFrame();
  const t1 = 58; // "cheaper"
  const t2 = 118; // "dearer"
  const p1 = interpolate(frame, [t1, t1 + 30], [0, 1], { ...clamp, easing: out });
  const p2 = interpolate(frame, [t2, t2 + 30], [0, 1], { ...clamp, easing: out });
  const wa = w(6, 0) + (w(7, 0) - w(6, 0)) * p1;
  const wb = w(6, 0) + (w(6, 1) - w(6, 0)) * p2;
  const free = Math.min(sc.frames - 60, 170);
  const S = { x: 560, y: 600 };
  const A = { x: 1380, y: 440 };
  const B = { x: 1380, y: 780 };
  return (
    <Scene sc={sc}>
      <div style={{ position: "absolute", left: 120, top: 96 }}>
        <Eyebrow>It learns</Eyebrow>
        <div style={{ height: 18 }} />
        <Kinetic text="Every result feeds back." size={80} delay={4} />
      </div>
      <svg style={{ position: "absolute", inset: 0 }} width={1920} height={1080}>
        <line x1={S.x} y1={S.y} x2={A.x} y2={A.y} stroke={C.accent} strokeWidth={3 + 9 * p1} strokeOpacity={0.5 + 0.5 * p1} />
        <line x1={S.x} y1={S.y} x2={B.x} y2={B.y} stroke={p2 > 0 ? C.warn : C.accent} strokeWidth={3 + 1 * (1 - p2)} strokeOpacity={0.6 - 0.25 * p2} strokeDasharray={p2 > 0.05 ? "10 10" : undefined} />
      </svg>
      {[
        { p: A, wv: wa, col: C.accent, label: "cheaper", show: p1, mid: { x: (S.x + A.x) / 2, y: (S.y + A.y) / 2 - 60 } },
        { p: B, wv: wb, col: p2 > 0 ? C.warn : C.text, label: "dearer", show: p2, mid: { x: (S.x + B.x) / 2, y: (S.y + B.y) / 2 + 60 } },
      ].map((e, i) => (
        <div
          key={i}
          style={{
            position: "absolute",
            left: e.mid.x,
            top: e.mid.y,
            translate: "-50% -50%",
            fontFamily: MONO,
            fontSize: 30,
            padding: "10px 18px",
            borderRadius: 14,
            background: "rgba(9,11,16,0.9)",
            border: `1px solid ${e.col}55`,
            color: e.col,
            fontVariantNumeric: "tabular-nums",
            opacity: interpolate(frame, [20, 34], [0, 1], clamp),
          }}
        >
          w = {e.wv.toFixed(2)}
          <span style={{ opacity: e.show, marginLeft: 14, fontFamily: "inherit", fontSize: 24 }}>{e.label}</span>
        </div>
      ))}
      <Box x={S.x} y={S.y} title="word / symbol" sub="from a finished task" color={C.accent} delay={8} />
      <Box x={A.x} y={A.y} title="file it changed" sub="led to the real fix" color={C.accent} delay={14} />
      <Box x={B.x} y={B.y} title="file it suggested" sub="led nowhere" color={p2 > 0 ? C.warn : C.text} delay={18} />
      <div style={{ position: "absolute", left: 120, top: 860, fontFamily: MONO, fontSize: 26, color: C.dim, opacity: interpolate(frame, [30, 44], [0, 1], clamp) }}>
        w = ln(1000 / n) + ln(1 + miss)
      </div>
      <div style={{ position: "absolute", left: 120, top: 920, display: "flex", gap: 16 }}>
        <Chip delay={free}>0 model calls</Chip>
        <Chip delay={free + 6}>plain code</Chip>
        <Chip delay={free + 12}>free to run</Chip>
      </div>
    </Scene>
  );
};
