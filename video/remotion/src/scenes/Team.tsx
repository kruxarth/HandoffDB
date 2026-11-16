import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { C, MONO, Scene, SceneData, Kinetic, Eyebrow, Compass, clamp, out } from "../ui";

const AGENTS = [
  { x: 420, y: 470, label: "agent 1" },
  { x: 420, y: 790, label: "agent 2" },
  { x: 1500, y: 470, label: "agent 3" },
  { x: 1500, y: 790, label: "agent 4" },
];
const HUB = { x: 960, y: 630 };

export const Team: React.FC<{ sc: SceneData }> = ({ sc }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const inP = interpolate(frame, [40, 70], [0, 1], { ...clamp, easing: out }); // agent 1 → graph
  const outP = interpolate(frame, [80, 115], [0, 1], { ...clamp, easing: out }); // graph → everyone
  const hub = spring({ frame: frame - 10, fps, config: { damping: 14 } });
  return (
    <Scene sc={sc}>
      <div style={{ position: "absolute", left: 120, top: 96 }}>
        <Eyebrow>Built for teams</Eyebrow>
        <div style={{ height: 18 }} />
        <Kinetic text="One agent learns. Every agent starts there." size={72} delay={4} accent={["Every", "agent"]} />
      </div>
      <svg style={{ position: "absolute", inset: 0 }} width={1920} height={1080}>
        {AGENTS.map((a, i) => {
          const p = i === 0 ? inP : outP;
          const [x1, y1, x2, y2] = i === 0 ? [a.x, a.y, HUB.x, HUB.y] : [HUB.x, HUB.y, a.x, a.y];
          return (
            <g key={i}>
              <line x1={a.x} y1={a.y} x2={HUB.x} y2={HUB.y} stroke="rgba(255,255,255,0.1)" strokeWidth={2} />
              <line x1={x1} y1={y1} x2={x1 + (x2 - x1) * p} y2={y1 + (y2 - y1) * p} stroke={C.accent} strokeWidth={4} strokeLinecap="round" />
              {p > 0 && p < 1 ? <circle cx={x1 + (x2 - x1) * p} cy={y1 + (y2 - y1) * p} r={10} fill={C.accent} /> : null}
            </g>
          );
        })}
      </svg>
      <div style={{ position: "absolute", left: HUB.x, top: HUB.y, translate: "-50% -50%", scale: String(0.6 + 0.4 * hub), opacity: Math.min(1, hub * 1.5), textAlign: "center" }}>
        <div
          style={{
            width: 300,
            height: 300,
            borderRadius: 150,
            background: `radial-gradient(circle, ${C.panel2} 0%, ${C.panel} 70%)`,
            border: `1.5px solid ${C.accent}66`,
            boxShadow: `0 0 ${40 + 50 * outP}px ${C.accent}${outP > 0 ? "55" : "22"}`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexDirection: "column",
          }}
        >
          <Compass size={110} needle={interpolate(frame, [0, 120], [-30, 40], { ...clamp, easing: out })} />
          <div style={{ fontSize: 28, fontWeight: 650, marginTop: 10 }}>team graph</div>
          <div style={{ fontFamily: MONO, fontSize: 18, color: C.dim, marginTop: 4 }}>in HydraDB</div>
        </div>
      </div>
      {AGENTS.map((a, i) => {
        const lit = i === 0 ? inP > 0 : outP > 0.98;
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: a.x,
              top: a.y,
              translate: "-50% -50%",
              padding: "22px 34px",
              borderRadius: 20,
              background: C.panel2,
              border: `1.5px solid ${lit ? C.accent : C.line}`,
              boxShadow: "0 30px 60px rgba(0,0,0,0.5)",
              textAlign: "center",
              minWidth: 260,
            }}
          >
            <div style={{ fontFamily: MONO, fontSize: 28, color: lit ? C.accent : C.text }}>{a.label}</div>
            <div style={{ fontSize: 22, color: C.dim, marginTop: 6 }}>{i === 0 ? "finishes a task" : lit ? "starts from it" : "same repo"}</div>
          </div>
        );
      })}
      <div style={{ position: "absolute", left: 120, bottom: 56, fontSize: 24, color: C.faint }}>
        HydraDB scopes map to team and repo: tenant = team, subtenant = repo.
      </div>
    </Scene>
  );
};

export const End: React.FC<{ sc: SceneData }> = ({ sc }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const needle = spring({ frame: frame - 6, fps, config: { damping: 6, mass: 1.2, stiffness: 60 } });
  const t = spring({ frame: frame - 24, fps, config: { damping: 200 } });
  const t2 = spring({ frame: frame - 70, fps, config: { damping: 200 } });
  return (
    <Scene sc={sc}>
      <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
        <Compass size={220} needle={-120 + 165 * needle} ring={interpolate(frame, [0, sc.frames], [0, 12])} />
        <div style={{ fontSize: 150, fontWeight: 800, letterSpacing: "-0.05em", marginTop: 30, opacity: t, translate: `0px ${(1 - t) * 30}px` }}>Bearings</div>
        <div style={{ fontSize: 46, color: C.dim, marginTop: 6, opacity: t, translate: `0px ${(1 - t) * 30}px` }}>
          Your agents start where your team left off.
        </div>
        <div style={{ fontFamily: MONO, fontSize: 24, color: C.faint, marginTop: 70, opacity: t2, letterSpacing: "0.06em" }}>
          Built on <span style={{ color: C.accent }}>HydraDB</span> · HydraDB Hackathon, Track 2 · MIT licensed
        </div>
      </div>
    </Scene>
  );
};
