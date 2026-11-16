import React from "react";
import { Easing, interpolate, useCurrentFrame } from "remotion";
import { C, MONO, Scene, SceneData, Kinetic, Eyebrow, Stat, at, clamp, data, out } from "../ui";

const pct = (x: number) => Math.round(x * 100);

/** 850 real issues in date order; a tick lights when Bearings ranked the real fix first. */
const Strip: React.FC<{ start: number; dur: number; top: number }> = ({ start, dur, top }) => {
  const frame = useCurrentFrame();
  const r = data.replay;
  const n: number = r.date.length;
  const L = 120, W = 1680;
  const cursor = interpolate(frame, [start, start + dur], [0, n], { ...clamp, easing: Easing.bezier(0.4, 0, 0.6, 1) });
  const nDev = r.split.filter((s: string) => s === "dev").length;
  const xs = (i: number) => L + (i / n) * W;
  const years = ["2016", "2017", "2018", "2019", "2020", "2021", "2022", "2023"]
    .map((y) => ({ y, i: r.date.findIndex((d: string) => d >= `${y}-01`) }))
    .filter(({ i }, k, arr) => i >= 0 && (k === 0 || xs(i) - xs(arr[k - 1].i) > 90));
  const hits = r.bearings.slice(0, Math.floor(cursor)).filter((v: number, i: number) => v && r.split[i] === "test").length;
  const seen = r.split.slice(0, Math.floor(cursor)).filter((s: string) => s === "test").length;
  return (
    <div style={{ position: "absolute", left: 0, top, width: 1920, height: 300 }}>
      <svg width={1920} height={230}>
        <rect x={L} y={40} width={xs(nDev) - L} height={120} fill="rgba(255,255,255,0.03)" rx={10} />
        {r.bearings.map((v: number, i: number) => {
          const on = i < cursor;
          const age = cursor - i;
          return (
            <rect
              key={i}
              x={xs(i)}
              y={v ? 52 : 92}
              width={Math.max(1.2, W / n - 0.6)}
              height={v ? 96 : 40}
              rx={0.8}
              fill={v ? C.accent : "rgba(255,255,255,0.25)"}
              opacity={on ? Math.min(1, 0.35 + age / 20) : 0.06}
            />
          );
        })}
        <line x1={xs(cursor)} x2={xs(cursor)} y1={24} y2={176} stroke={C.text} strokeWidth={2.5} />
        <line x1={xs(nDev)} x2={xs(nDev)} y1={30} y2={200} stroke={C.faint} strokeWidth={1.5} strokeDasharray="6 6" />
        <text x={(L + xs(nDev)) / 2} y={204} textAnchor="middle" fill={C.faint} fontFamily={MONO} fontSize={20}>
          tuning only (126)
        </text>
        <text x={(xs(nDev) + L + W) / 2} y={204} textAnchor="middle" fill={C.dim} fontFamily={MONO} fontSize={20}>
          scored: 724 issues from July 2019
        </text>
        {years.map(({ y, i }) => (
          <text key={y} x={xs(i)} y={18} fill={C.faint} fontFamily={MONO} fontSize={19} textAnchor="middle">
            {y}
          </text>
        ))}
      </svg>
      <div style={{ position: "absolute", left: 120, top: 236, fontSize: 26, color: C.dim, display: "flex", gap: 40, alignItems: "center" }}>
        <span>
          <span style={{ display: "inline-block", width: 14, height: 30, background: C.accent, borderRadius: 3, marginRight: 12, verticalAlign: "middle" }} />
          real fix ranked first
        </span>
        <span style={{ fontFamily: MONO, color: C.text, fontVariantNumeric: "tabular-nums" }}>
          {seen ? `${hits} / ${seen} scored` : " "}
        </span>
      </div>
    </div>
  );
};

export const Replay: React.FC<{ sc: SceneData }> = ({ sc }) => {
  const frame = useCurrentFrame();
  const b = at(sc, "07b");
  const H = data.learn.m.history;
  const up = interpolate(frame, [b - 6, b + 20], [0, 1], { ...clamp, easing: out });
  return (
    <Scene sc={sc}>
      <div style={{ position: "absolute", left: 120, top: 96 }}>
        <Eyebrow>Results · retrieval, no model calls</Eyebrow>
        <div style={{ height: 18 }} />
        <Kinetic text="Every Django issue, replayed in date order." size={72} delay={4} accent={["date", "order."]} />
      </div>
      <div style={{ translate: `0px ${-up * 40}px` }}>
        <Strip start={30} dur={b - 40} top={330} />
      </div>
      <div style={{ position: "absolute", left: 120, top: 660, fontSize: 30, color: C.dim, opacity: 1 - up }}>
        Each issue is answered from what came before it. Then its real fix is learned.
      </div>
      <div style={{ position: "absolute", left: 120, top: 640, display: "flex", gap: 40, width: 1680 }}>
        <Stat
          value={pct(H.bearings["hit@1"])}
          delay={b + 6}
          label={
            <>
              real fix ranked <b style={{ color: C.text }}>first</b>
              <br />
              keyword search: {pct(H.bm25["hit@1"])}%
            </>
          }
          style={{ flex: 1 }}
        />
        <Stat
          value={pct(H.bearings["hit@5"])}
          delay={b + 60}
          color={C.text}
          label={
            <>
              in the <b style={{ color: C.text }}>top five</b>: tied
              <br />
              keyword search: {pct(H.bm25["hit@5"])}%
            </>
          }
          style={{ flex: 1 }}
        />
      </div>
      <div style={{ position: "absolute", left: 120, bottom: 50, fontSize: 22, color: C.faint, opacity: up }}>
        Graph seeded from Django's own past fixes, never from the future. SWE-bench, 724 scored issues. Full intervals in results/RESULTS.md.
      </div>
    </Scene>
  );
};
