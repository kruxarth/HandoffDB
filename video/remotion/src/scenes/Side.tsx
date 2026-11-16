import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { C, MONO, Scene, SceneData, Window, Kinetic, Eyebrow, clamp, data } from "../ui";

type Call = { cmd: string; gold: boolean };
const PER = 7;

const Col: React.FC<{ title: string; calls: Call[]; left: number; accent: boolean; start: number }> = ({ title, calls, left, accent, start }) => {
  const frame = useCurrentFrame();
  const shown = Math.max(0, Math.min(calls.length, Math.floor((frame - start) / PER) + 1));
  const done = shown === calls.length;
  return (
    <Window
      title={title}
      delay={start - 14}
      glow={accent && done ? 0.5 : 0}
      style={{ left, top: 300, width: 820, height: 690 }}
      bodyStyle={{ padding: "16px 26px" }}
      right={
        <div style={{ fontFamily: MONO, fontSize: 24, color: accent ? C.accent : C.text, fontVariantNumeric: "tabular-nums" }}>
          {shown} tool calls
        </div>
      }
    >
      {calls.slice(0, shown).map((c, i) => {
        const s = interpolate(frame - start - i * PER, [0, 6], [0, 1], clamp);
        return (
          <div
            key={i}
            style={{
              fontFamily: MONO,
              fontSize: 19,
              lineHeight: "31px",
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
              color: c.gold ? C.accent : C.dim,
              opacity: s,
              translate: `${(1 - s) * 14}px 0px`,
            }}
          >
            <span style={{ color: C.faint }}>{String(i + 1).padStart(2, "0")} </span>
            {c.cmd}
            {c.gold ? "  ◆" : ""}
          </div>
        );
      })}
    </Window>
  );
};

export const Side: React.FC<{ sc: SceneData }> = ({ sc }) => {
  const s = data.side;
  return (
    <Scene sc={sc}>
      <div style={{ position: "absolute", left: 120, top: 96 }}>
        <Eyebrow>One new issue · django-15916</Eyebrow>
        <div style={{ height: 18 }} />
        <Kinetic text="Straight to the right lines." size={76} delay={4} />
      </div>
      <Col title="no memory" calls={s.none.calls} left={120} accent={false} start={30} />
      <Col title="with the Bearings pack" calls={s.bearings.calls} left={980} accent start={30} />
      <div style={{ position: "absolute", left: 120, top: 1010, fontSize: 22, color: C.faint, width: 1680 }}>
        Real runs, DeepSeek V4.1 Flash through OpenCode. ◆ = touches the file the real fix changed. One issue, not an average.
      </div>
    </Scene>
  );
};
