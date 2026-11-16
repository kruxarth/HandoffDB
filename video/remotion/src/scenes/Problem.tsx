import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { C, MONO, Scene, SceneData, Swap, Kinetic, Window, at, clamp, data, fmt, out, useSpring, Eyebrow } from "../ui";

type Call = { cmd: string; cum: number };

const Log: React.FC<{ dim: number }> = ({ dim }) => {
  const frame = useCurrentFrame();
  const calls: Call[] = data.problem.calls;
  const per = 7;
  const shown = Math.max(0, Math.min(calls.length, Math.floor((frame - 18) / per) + 1));
  const vis = calls.slice(Math.max(0, shown - 13), shown);
  const tokens = shown ? calls[shown - 1].cum : 0;
  const prev = shown > 1 ? calls[shown - 2].cum : 0;
  const t = interpolate(frame - 18 - (shown - 1) * per, [0, per], [prev, tokens], { ...clamp, easing: out });
  return (
    <Window
      title={`agent · no memory · ${data.problem.label.split(",")[0].replace("SWE-bench ", "")}`}
      delay={6}
      style={{ left: 110, top: 150, width: 930, height: 800, filter: `saturate(${1 - dim * 0.8})`, opacity: 1 - dim * 0.55 }}
      bodyStyle={{ padding: "22px 28px" }}
      right={
        <div style={{ fontFamily: MONO, fontSize: 22, color: C.warn, fontVariantNumeric: "tabular-nums" }}>
          {fmt(t)} tokens read
        </div>
      }
    >
      {vis.map((c, i) => {
        const idx = shown - vis.length + i;
        const age = frame - 18 - idx * per;
        const s = interpolate(age, [0, 6], [0, 1], clamp);
        return (
          <div
            key={idx}
            style={{
              fontFamily: MONO,
              fontSize: 22,
              lineHeight: "50px",
              height: 50,
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
              color: i === vis.length - 1 ? C.text : C.dim,
              opacity: s,
              translate: `${(1 - s) * 16}px 0px`,
            }}
          >
            <span style={{ color: C.faint }}>{String(idx + 1).padStart(2, "0")} </span>
            <span style={{ color: C.accent }}>$ </span>
            {c.cmd}
          </div>
        );
      })}
    </Window>
  );
};

const SameFile: React.FC = () => {
  const s1 = useSpring(8);
  const s2 = useSpring(22);
  const box = (who: string, when: string, s: number) => (
    <div
      style={{
        opacity: s,
        translate: `0px ${(1 - s) * 30}px`,
        background: C.panel,
        border: `1px solid ${C.line}`,
        borderRadius: 18,
        padding: "20px 24px",
        width: 300,
      }}
    >
      <div style={{ fontSize: 28, fontWeight: 650 }}>{who}</div>
      <div style={{ fontSize: 22, color: C.dim, marginTop: 4 }}>{when}</div>
    </div>
  );
  return (
    <div style={{ marginTop: 50 }}>
      <div style={{ display: "flex", gap: 30 }}>
        {box("Teammate's agent", "last week", s1)}
        {box("Your agent", "today", s2)}
      </div>
      <div
        style={{
          marginTop: 26,
          fontFamily: MONO,
          fontSize: 26,
          padding: "18px 24px",
          borderRadius: 16,
          border: `1px dashed ${C.warn}88`,
          color: C.warn,
          opacity: s2,
          width: 630,
        }}
      >
        → the same files, found twice
      </div>
    </div>
  );
};

export const Problem: React.FC<{ sc: SceneData }> = ({ sc }) => {
  const frame = useCurrentFrame();
  const a2 = at(sc, "02");
  const a3 = at(sc, "02b");
  const dim = interpolate(frame, [a3, a3 + 20], [0, 1], { ...clamp, easing: out });
  return (
    <Scene sc={sc}>
      <Log dim={dim} />
      <div style={{ position: "absolute", left: 1110, top: 200, width: 700 }}>
        <Swap at={0} until={a2}>
          <Eyebrow>Every coding agent, every task</Eyebrow>
          <div style={{ height: 24 }} />
          <Kinetic text="Starts from zero." delay={6} size={96} />
          <div style={{ fontSize: 36, color: C.dim, marginTop: 30, lineHeight: 1.35, width: 660 }}>
            Every search and every file it opens is paid for in tokens.
          </div>
        </Swap>
        <Swap at={a2} until={a3}>
          <Kinetic text="And most of it is a repeat." size={80} accent={["repeat"]} />
          <SameFile />
        </Swap>
        <Swap at={a3}>
          <Kinetic text="When the session ends, it is thrown away." size={80} accent={["thrown", "away"]} />
        </Swap>
      </div>
      <div style={{ position: "absolute", left: 110, top: 974, fontSize: 22, color: C.faint }}>
        A real run: {data.problem.label}
      </div>
    </Scene>
  );
};
