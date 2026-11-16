import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { C, MONO, Scene, SceneData, Kinetic, Eyebrow, Chip, at, clamp, data, fmt, out, useSpring } from "../ui";

type Row = { label: string; value: number; text: string; color: string; note?: string };

export const Bars: React.FC<{ rows: Row[]; max: number; start: number; left: number; top: number; width: number; rowH?: number; labelW?: number; gapAfter?: number[] }> = ({
  rows,
  max,
  start,
  left,
  top,
  width,
  rowH = 92,
  labelW = 330,
  gapAfter = [],
}) => {
  const frame = useCurrentFrame();
  let y = 0;
  return (
    <div style={{ position: "absolute", left, top, width }}>
      {rows.map((r, i) => {
        const p = interpolate(frame, [start + i * 6, start + i * 6 + 30], [0, 1], { ...clamp, easing: out });
        const el = (
          <div key={i} style={{ position: "absolute", top: y, left: 0, width, height: rowH - 18, display: "flex", alignItems: "center", gap: 24, opacity: Math.min(1, p * 2) }}>
            <div style={{ width: labelW, fontSize: 28, color: r.color === C.accent ? C.accent : C.text, textAlign: "right", flex: "0 0 auto" }}>{r.label}</div>
            <div style={{ flex: 1, height: "100%", position: "relative" }}>
              <div
                style={{
                  position: "absolute",
                  left: 0,
                  top: 6,
                  bottom: 6,
                  width: `${(r.value / max) * 100 * p}%`,
                  background: r.color,
                  borderRadius: 10,
                  boxShadow: r.color === C.accent ? `0 0 30px ${C.accent}44` : undefined,
                }}
              />
              <div
                style={{
                  position: "absolute",
                  left: `calc(${(r.value / max) * 100 * p}% + 18px)`,
                  top: 0,
                  bottom: 0,
                  display: "flex",
                  alignItems: "center",
                  fontFamily: MONO,
                  fontSize: 26,
                  color: C.text,
                  whiteSpace: "nowrap",
                  fontVariantNumeric: "tabular-nums",
                }}
              >
                {fmt(r.value * p)}
                {r.note ? <span style={{ color: C.dim, marginLeft: 16, fontFamily: "inherit", fontSize: 22 }}>{r.note}</span> : null}
              </div>
            </div>
          </div>
        );
        y += rowH + (gapAfter.includes(i) ? 26 : 0);
        return el;
      })}
    </div>
  );
};

export const Live: React.FC<{ sc: SceneData }> = ({ sc }) => {
  const frame = useCurrentFrame();
  const L = data.live;
  const conds = L.stats.conds;
  const why = Math.round(sc.frames * 0.42);
  const rows: Row[] = L.rows.map((r: Row) => ({ ...r, color: r.label === "Bearings" ? C.accent : r.label === "No memory" ? C.gray : "#4b5260", note: undefined }));
  const fg = ["none", "dict", "bearings"].map((k) => conds[k].first_gold);
  const w = interpolate(frame, [why, why + 20], [0, 1], { ...clamp, easing: out });
  return (
    <Scene sc={sc}>
      <div style={{ position: "absolute", left: 120, top: 96 }}>
        <Eyebrow color={C.warn}>Live agents · {L.stats.n} new issues</Eyebrow>
        <div style={{ height: 18 }} />
        <Kinetic text="No token saving." size={96} delay={4} />
      </div>
      <div style={{ position: "absolute", left: 120, top: 340, fontSize: 28, color: C.dim }}>Median input tokens per run, pack included</div>
      <Bars rows={rows} max={130000} start={18} left={120} top={410} width={1000} labelW={260} rowH={150} />
      <div
        style={{
          position: "absolute",
          left: 1200,
          top: 340,
          width: 600,
          padding: "40px 42px",
          borderRadius: 24,
          background: C.panel,
          border: `1px solid ${C.warn}44`,
          opacity: w,
          translate: `0px ${(1 - w) * 30}px`,
          boxShadow: "0 30px 70px rgba(0,0,0,0.45)",
        }}
      >
        <div style={{ fontFamily: MONO, fontSize: 22, color: C.warn, letterSpacing: "0.12em" }}>WHY</div>
        <div style={{ fontSize: 42, fontWeight: 700, marginTop: 16, lineHeight: 1.2, letterSpacing: "-0.02em" }}>These issues already name the code.</div>
        <div style={{ fontSize: 28, color: C.dim, marginTop: 22, lineHeight: 1.4 }}>
          In every condition the agent opened a real-fix file in its first step or two:
        </div>
        <div style={{ display: "flex", gap: 14, marginTop: 20 }}>
          {["no memory", "dictionary", "Bearings"].map((n, i) => (
            <div key={n} style={{ flex: 1, padding: "20px 10px", borderRadius: 14, background: C.panel2, textAlign: "center" }}>
              <div style={{ fontFamily: MONO, fontSize: 38, color: i === 2 ? C.accent : C.text }}>{(fg[i] / 1000).toFixed(1)}k</div>
              <div style={{ fontSize: 20, color: C.dim, marginTop: 4 }}>{n}</div>
            </div>
          ))}
        </div>
        <div style={{ fontSize: 24, color: C.faint, marginTop: 16 }}>median tokens until a real-fix file is opened</div>
      </div>
      <div style={{ position: "absolute", left: 120, bottom: 56, fontSize: 22, color: C.faint, width: 1680 }}>
        DeepSeek V4.1 Flash through OpenCode, sandboxed. SWE-bench Verified issues from after the graph's cutoff. Whole runs: flat within noise.
      </div>
    </Scene>
  );
};

export const Claude: React.FC<{ sc: SceneData }> = ({ sc }) => {
  const frame = useCurrentFrame();
  const win = Math.round(sc.frames * 0.5);
  const rows: Row[] = data.claude.rows.map((r: Row) => ({
    ...r,
    label: r.label.split(", ").slice(1).join(", ").replace("without Bearings", "without").replace("without, second run", "without, rerun"),
    color: r.label.includes("with Bearings") ? C.accent : r.label.includes("second") ? "#4b5260" : C.gray,
  }));
  const tasks = Array.from(new Set(data.claude.rows.map((r: Row) => r.label.split(", ")[0]))) as string[];
  const w = interpolate(frame, [win, win + 22], [0, 1], { ...clamp, easing: out });
  return (
    <Scene sc={sc}>
      <div style={{ position: "absolute", left: 120, top: 96 }}>
        <Eyebrow>Claude Code · two demo tasks</Eyebrow>
        <div style={{ height: 18 }} />
        <Kinetic text="The same story." size={88} delay={4} />
      </div>
      {tasks.map((t, i) => (
        <div key={t} style={{ position: "absolute", left: 120, top: 345 + i * 300, fontFamily: MONO, fontSize: 24, color: C.faint }}>
          {t}
        </div>
      ))}
      <Bars rows={rows.slice(0, 3)} max={460000} start={14} left={120} top={385} width={1050} rowH={84} labelW={250} />
      <Bars rows={rows.slice(3)} max={460000} start={30} left={120} top={685} width={1050} rowH={84} labelW={250} />
      <div style={{ position: "absolute", left: 120, top: 985, fontSize: 24, color: C.dim }}>Total input tokens as Claude Code reports them (sonnet). Two examples, not a statistic.</div>
      <div
        style={{
          position: "absolute",
          left: 1280,
          top: 360,
          width: 520,
          opacity: w,
          translate: `0px ${(1 - w) * 30}px`,
        }}
      >
        <div style={{ fontFamily: MONO, fontSize: 22, color: C.accent, letterSpacing: "0.12em" }}>WHERE BEARINGS WINS</div>
        <div style={{ fontSize: 64, fontWeight: 750, marginTop: 16, lineHeight: 1.2, letterSpacing: "-0.03em" }}>Ranking.</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 16, marginTop: 26, alignItems: "flex-start" }}>
          <Chip delay={win + 10}>which file to open first</Chip>
          <Chip delay={win + 22}>learning from an empty start</Chip>
        </div>
      </div>
    </Scene>
  );
};

const Item: React.FC<{ text: string; good: boolean; delay: number }> = ({ text, good, delay }) => {
  const s = useSpring(delay, 200, 24);
  return (
    <div style={{ display: "flex", gap: 26, alignItems: "flex-start", opacity: s, translate: `${(1 - s) * -40}px 0px`, marginBottom: 40 }}>
      <div
        style={{
          width: 44,
          height: 44,
          borderRadius: 12,
          flex: "0 0 auto",
          marginTop: 2,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: 26,
          fontWeight: 700,
          background: good ? C.accentSoft : C.warnSoft,
          color: good ? C.accent : C.warn,
        }}
      >
        {good ? "✓" : "–"}
      </div>
      <div style={{ fontSize: 40, lineHeight: 1.3, color: C.text }}>{text}</div>
    </div>
  );
};

export const Limits: React.FC<{ sc: SceneData }> = ({ sc }) => {
  const b = at(sc, "12b");
  const items: [string, string][] = data.limits.items;
  const bad = items.filter((x) => x[0] === "orange");
  const good = items.filter((x) => x[0] === "blue");
  return (
    <Scene sc={sc}>
      <div style={{ position: "absolute", left: 120, top: 96 }}>
        <Eyebrow color={C.warn}>Reported, not hidden</Eyebrow>
        <div style={{ height: 18 }} />
        <Kinetic text="What did not help, measured." size={80} delay={4} />
      </div>
      <div style={{ position: "absolute", left: 120, top: 350, width: 1640 }}>
        {bad.map((x, i) => (
          <Item key={i} text={x[1]} good={false} delay={20 + i * 22} />
        ))}
        <div style={{ height: 36 }} />
        {good.map((x, i) => (
          <Item key={i} text={x[1]} good delay={b + 6 + i * 22} />
        ))}
      </div>
    </Scene>
  );
};
