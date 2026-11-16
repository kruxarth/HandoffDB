import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { C, MONO, Scene, SceneData, Mark, clamp, out } from "../ui";

/** Product name: the mark draws itself, then run → graph → next agent. */
export const Name: React.FC<{ sc: SceneData }> = ({ sc }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const m = spring({ frame: frame - 4, fps, config: { damping: 200 }, durationInFrames: 40 });
  const t = spring({ frame: frame - 18, fps, config: { damping: 200 } });
  const steps = [
    { label: "agent run ends", sub: "files, lines, tests, fix", color: C.accent },
    { label: "graph on HydraDB", sub: "recorded, no model call", color: C.teal },
    { label: "next agent", sub: "starts from it", color: C.green },
  ];
  const s0 = Math.round(sc.frames * 0.35);
  return (
    <Scene sc={sc}>
      <div style={{ position: "absolute", left: 0, right: 0, top: 150, display: "flex", flexDirection: "column", alignItems: "center" }}>
        <Mark size={200} t={m} pulse={frame / 40} />
        <div style={{ fontSize: 140, fontWeight: 800, letterSpacing: "-0.05em", marginTop: 20, opacity: t, translate: `0px ${(1 - t) * 30}px`, color: C.text }}>
          Handoff<span style={{ color: C.accent }}>DB</span>
        </div>
        <div style={{ fontSize: 40, color: C.dim, marginTop: 4, opacity: t }}>The next agent starts where the last one left off.</div>
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 760, display: "flex", justifyContent: "center", alignItems: "center", gap: 0 }}>
        {steps.map((s, i) => {
          const p = interpolate(frame, [s0 + i * 22, s0 + i * 22 + 18], [0, 1], { ...clamp, easing: out });
          const a = interpolate(frame, [s0 + i * 22 + 10, s0 + i * 22 + 28], [0, 1], { ...clamp, easing: out });
          return (
            <React.Fragment key={i}>
              <div style={{ opacity: p, translate: `0px ${(1 - p) * 24}px`, background: "#ffffff", border: `2px solid ${s.color}66`, borderRadius: 22, padding: "20px 30px", minWidth: 330, textAlign: "center", boxShadow: "0 14px 34px rgba(15,23,42,0.08)" }}>
                <div style={{ fontFamily: MONO, fontSize: 28, fontWeight: 700, color: s.color }}>{s.label}</div>
                <div style={{ fontSize: 22, color: C.dim, marginTop: 6 }}>{s.sub}</div>
              </div>
              {i < steps.length - 1 ? (
                <svg width={110} height={40} style={{ overflow: "visible" }}>
                  <line x1={14} y1={20} x2={14 + 74 * a} y2={20} stroke={C.faint} strokeWidth={4} strokeLinecap="round" />
                  <path d="M80,10 L96,20 L80,30" fill="none" stroke={C.faint} strokeWidth={4} strokeLinecap="round" opacity={a} />
                </svg>
              ) : null}
            </React.Fragment>
          );
        })}
      </div>
    </Scene>
  );
};
