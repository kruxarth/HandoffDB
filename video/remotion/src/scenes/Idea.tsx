import React from "react";
import { interpolate, random, useCurrentFrame } from "remotion";
import { C, MONO, Scene, SceneData, Kinetic, Eyebrow, at, clamp, data, out, useSpring } from "../ui";

type N = { kind: string; label: string; x: number; y: number };

const KIND: Record<string, { tag: string; color: string }> = {
  task: { tag: "past fix", color: C.text },
  term: { tag: "word / symbol", color: C.accent },
  file: { tag: "file", color: "#9fd0ff" },
  test: { tag: "test", color: "#b9f0c8" },
};

// graph coordinates come from video/build.py (x 170–1460, y 140–520); map onto the stage
const X = (x: number) => 200 + x * 1.0;
const Y = (y: number) => 330 + y * 0.95;

const Node: React.FC<{ n: N; delay: number }> = ({ n, delay }) => {
  const s = useSpring(delay, 13);
  const k = KIND[n.kind];
  const label = n.kind === "task" ? "a past fix" : n.label;
  return (
    <div
      style={{
        position: "absolute",
        left: X(n.x),
        top: Y(n.y),
        translate: "-50% -50%",
        scale: String(0.6 + 0.4 * Math.min(1.06, s)),
        opacity: Math.min(1, s * 1.6),
        textAlign: "center",
      }}
    >
      <div style={{ fontFamily: MONO, fontSize: 18, letterSpacing: "0.14em", textTransform: "uppercase", color: C.faint, marginBottom: 8 }}>{k.tag}</div>
      <div
        style={{
          fontFamily: MONO,
          fontSize: 28,
          padding: "14px 22px",
          borderRadius: 16,
          background: C.panel2,
          border: `1.5px solid ${k.color}66`,
          color: k.color,
          whiteSpace: "nowrap",
          boxShadow: `0 20px 50px rgba(0,0,0,0.5), 0 0 30px ${k.color}22`,
        }}
      >
        {label}
      </div>
    </div>
  );
};

export const Idea: React.FC<{ sc: SceneData }> = ({ sc }) => {
  const frame = useCurrentFrame();
  const g = data.idea;
  const nodes: Record<string, N> = g.nodes;
  const edges: [string, string, string][] = g.edges;
  const a4 = at(sc, "04");
  const a5 = at(sc, "04b");
  // reveal order: task, terms, file, test
  const order: Record<string, number> = {};
  Object.entries(nodes).forEach(([id, n]) => {
    order[id] = n.kind === "task" ? 0 : n.kind === "term" ? 1 : n.kind === "file" ? 2 : 3;
  });
  const stepAt = (k: number) => Math.min(a4, 40) + 10 + k * 40;
  const cloud = interpolate(frame, [a5, a5 + 40], [0, 1], { ...clamp, easing: out });
  return (
    <Scene sc={sc}>
      <div style={{ position: "absolute", left: 120, top: 96 }}>
        <Eyebrow>The idea</Eyebrow>
        <div style={{ height: 18 }} />
        <Kinetic text="Remember where past work landed." delay={4} size={80} accent={["landed."]} />
      </div>
      {/* seeded history: many faint nodes */}
      <svg style={{ position: "absolute", inset: 0 }} width={1920} height={1080}>
        {Array.from({ length: 140 }).map((_, i) => {
          const x = 120 + random(`x${i}`) * 1680;
          const y = 300 + random(`y${i}`) * 680;
          const j = Math.floor(random(`j${i}`) * 140);
          const x2 = 120 + random(`x${j}`) * 1680;
          const y2 = 300 + random(`y${j}`) * 680;
          const o = cloud * (0.25 + 0.5 * random(`o${i}`)) * interpolate(frame, [a5 + i * 0.6, a5 + 20 + i * 0.6], [0, 1], clamp);
          return (
            <g key={i} opacity={o}>
              <line x1={x} y1={y} x2={x2} y2={y2} stroke="rgba(111,177,255,0.18)" strokeWidth={1} />
              <circle cx={x} cy={y} r={3 + random(`r${i}`) * 3} fill={C.accent} opacity={0.6} />
            </g>
          );
        })}
      </svg>
      <div style={{ position: "absolute", inset: 0, opacity: 1 - cloud * 0.55 }}>
        <svg style={{ position: "absolute", inset: 0 }} width={1920} height={1080}>
          {edges.map(([a, b, label], i) => {
            const A = nodes[a];
            const B = nodes[b];
            const st = stepAt(Math.max(order[a], order[b]) - 0.5);
            const p = interpolate(frame, [st, st + 26], [0, 1], { ...clamp, easing: out });
            const x1 = X(A.x), y1 = Y(A.y), x2 = X(B.x), y2 = Y(B.y);
            const len = Math.hypot(x2 - x1, y2 - y1);
            return (
              <g key={i}>
                <line x1={x1} y1={y1} x2={x2} y2={y2} stroke={C.accent} strokeOpacity={0.55} strokeWidth={2.5} strokeDasharray={len} strokeDashoffset={len * (1 - p)} />
                {label ? (
                  <text
                    x={(x1 + x2) / 2}
                    y={(y1 + y2) / 2 - 16}
                    textAnchor="middle"
                    fill={C.dim}
                    fontFamily={MONO}
                    fontSize={21}
                    opacity={interpolate(p, [0.6, 1], [0, 1], clamp)}
                  >
                    {label}
                  </text>
                ) : null}
              </g>
            );
          })}
        </svg>
        {Object.entries(nodes).map(([id, n]) => (
          <Node key={id} n={n} delay={stepAt(order[id])} />
        ))}
      </div>
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          top: 560,
          textAlign: "center",
          opacity: cloud,
          translate: `0px ${(1 - cloud) * 30}px`,
        }}
      >
        <div
          style={{
            display: "inline-block",
            padding: "34px 54px",
            borderRadius: 28,
            background: "rgba(9,11,16,0.82)",
            border: `1px solid ${C.line}`,
            boxShadow: "0 40px 90px rgba(0,0,0,0.6)",
          }}
        >
          <div style={{ fontSize: 60, fontWeight: 750, letterSpacing: "-0.03em" }}>
            Useful on <span style={{ color: C.accent }}>day one.</span>
          </div>
          <div style={{ fontSize: 30, color: C.dim, marginTop: 12 }}>
            A repo's merged history seeds the graph. Django: 21,217 issue-fixing commits.
          </div>
        </div>
      </div>
      <div style={{ position: "absolute", left: 120, bottom: 60, fontSize: 22, color: C.faint, opacity: 1 - cloud }}>
        A real neighbourhood from the graph, stored in HydraDB.
      </div>
    </Scene>
  );
};
