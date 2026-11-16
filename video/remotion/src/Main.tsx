import React from "react";
import { AbsoluteFill, Sequence, interpolate, staticFile, useCurrentFrame } from "remotion";
import { Audio } from "@remotion/media";
import { C, Compass, SANS, SceneData, timeline } from "./ui";
import { Problem } from "./scenes/Problem";
import { Idea } from "./scenes/Idea";
import { Query } from "./scenes/Query";
import { Learn } from "./scenes/Learn";
import { Plug } from "./scenes/Plug";
import { Replay } from "./scenes/Replay";
import { Curve } from "./scenes/Curve";
import { Side } from "./scenes/Side";
import { Live, Claude, Limits } from "./scenes/Honest";
import { Team, End } from "./scenes/Team";
import { Pivot, Record, Traverse, Results, Pile } from "./scenes/Handoff";
import { Store } from "./scenes/Store";

export const SCENES: Record<string, React.FC<{ sc: SceneData }>> = {
  problem: Problem,
  pivot: Pivot,
  record: Record,
  traverse: Traverse,
  results: Results,
  pile: Pile,
  store: Store,
  idea: Idea,
  query: Query,
  learn: Learn,
  plug: Plug,
  replay: Replay,
  curve: Curve,
  side: Side,
  live: Live,
  claude: Claude,
  limits: Limits,
  team: Team,
  end: End,
};

const Background: React.FC = () => {
  const frame = useCurrentFrame();
  const endStart = timeline.scenes[timeline.scenes.length - 1].start;
  const fadeMark = interpolate(frame, [endStart - 10, endStart + 10], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <AbsoluteFill
        style={{
          background: `radial-gradient(1200px 800px at ${70 + 8 * Math.sin(frame / 240)}% ${10 + 6 * Math.cos(frame / 300)}%, rgba(20,184,166,0.16), transparent 60%), radial-gradient(900px 700px at 0% 100%, rgba(249,115,22,0.12), transparent 60%), radial-gradient(700px 600px at 50% 50%, rgba(2,132,199,0.06), transparent 70%)`,
        }}
      />
      <AbsoluteFill
        style={{
          backgroundImage: "radial-gradient(rgba(15,23,42,0.05) 1.2px, transparent 1.2px)",
          backgroundSize: "36px 36px",
          maskImage: "linear-gradient(180deg, rgba(0,0,0,0.9), rgba(0,0,0,0.2))",
        }}
      />
      <div style={{ position: "absolute", right: -260, bottom: -300, opacity: 0.08 }}>
        <Compass size={1000} ring={frame / 12} noNeedle color="#0f172a" />
      </div>
      <div style={{ position: "absolute", right: 80, top: 70, display: "flex", alignItems: "center", gap: 14, opacity: 0.75 * fadeMark, fontFamily: SANS }}>
        <Compass size={40} needle={40} />
        <span style={{ fontWeight: 700, fontSize: 26, letterSpacing: "-0.02em", color: C.text }}>Bearings</span>
      </div>
    </AbsoluteFill>
  );
};

export const Main: React.FC = () => {
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <Background />
      {timeline.scenes.map((sc) => {
        const Comp = SCENES[sc.name];
        return (
          <Sequence key={sc.name} name={sc.name} from={sc.start} durationInFrames={sc.frames}>
            <Comp sc={sc} />
          </Sequence>
        );
      })}
      {timeline.scenes.flatMap((sc) =>
        sc.lines.map((l) => (
          <Sequence key={l.id} name={`voice ${l.id}`} from={sc.start + l.from} durationInFrames={l.frames + 6}>
            <Audio src={staticFile(l.src)} />
          </Sequence>
        )),
      )}
      <Audio src={staticFile("music.wav")} volume={0.16} />
    </AbsoluteFill>
  );
};
