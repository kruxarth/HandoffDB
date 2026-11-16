import React from "react";
import {
  AbsoluteFill,
  Easing,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { loadFont as loadInter } from "@remotion/google-fonts/Inter";
import { loadFont as loadMono } from "@remotion/google-fonts/JetBrainsMono";
import timelineJson from "../public/timeline.json";
import dataJson from "../public/data.json";

const inter = loadInter("normal", { weights: ["400", "500", "600", "700", "800"], subsets: ["latin"] });
const mono = loadMono("normal", { weights: ["400", "500", "700"], subsets: ["latin"] });

export const SANS = inter.fontFamily;
export const MONO = mono.fontFamily;

export const C = {
  bg: "#fbf8f2",
  panel: "#ffffff",
  panel2: "#ffffff",
  line: "rgba(15,23,42,0.10)",
  text: "#111827",
  dim: "#475569",
  faint: "#8b95a7",
  accent: "#0284c7",
  accentSoft: "rgba(2,132,199,0.12)",
  warn: "#f97316",
  warnSoft: "rgba(249,115,22,0.13)",
  gray: "#94a3b8",
  teal: "#14b8a6",
  green: "#16a34a",
  yellow: "#eab308",
  pink: "#ec4899",
};

export type Line = { id: string; text: string; from: number; frames: number; src: string };
export type SceneData = { name: string; lines: Line[]; frames: number; start: number };
export const timeline = timelineJson as { fps: number; frames: number; scenes: SceneData[] };
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const data = dataJson as any;

export const at = (sc: SceneData, id: string) => {
  const l = sc.lines.find((x) => x.id === id);
  if (!l) throw new Error(`line ${id} not in scene ${sc.name}`);
  return l.from;
};
export const lineEnd = (sc: SceneData, id: string) => {
  const l = sc.lines.find((x) => x.id === id)!;
  return l.from + l.frames;
};

export const out = Easing.bezier(0.16, 1, 0.3, 1);
export const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

/** 0 → 1 spring starting at `delay` frames. */
export const useSpring = (delay = 0, damping = 200, durationInFrames?: number) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return spring({ frame: frame - delay, fps, config: { damping }, durationInFrames });
};

/** Fades and lifts the whole scene in and out. */
export const Scene: React.FC<{ sc: SceneData; children: React.ReactNode }> = ({ sc, children }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const inn = spring({ frame, fps, config: { damping: 200 }, durationInFrames: 22 });
  const outp = interpolate(frame, [sc.frames - 14, sc.frames], [1, 0], { ...clamp, easing: Easing.bezier(0.7, 0, 0.84, 0) });
  return (
    <AbsoluteFill
      style={{
        opacity: Math.min(inn, outp),
        translate: `0px ${(1 - inn) * 26 - (1 - outp) * 18}px`,
        scale: String(0.985 + 0.015 * inn),
        fontFamily: SANS,
        color: C.text,
      }}
    >
      {children}
    </AbsoluteFill>
  );
};

/** Swaps content when a later line starts: shows the child whose `from` is the latest passed. */
export const Swap: React.FC<{ at: number; until?: number; children: React.ReactNode; style?: React.CSSProperties }> = ({
  at: a,
  until,
  children,
  style,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const inn = spring({ frame: frame - a, fps, config: { damping: 200 }, durationInFrames: 20 });
  const outp = until === undefined ? 1 : 1 - spring({ frame: frame - until, fps, config: { damping: 200 }, durationInFrames: 14 });
  if (frame < a - 1 || outp <= 0.001) return null;
  return (
    <div style={{ position: "absolute", opacity: Math.min(inn, outp), translate: `0px ${(1 - inn) * 30 - (1 - outp) * 20}px`, ...style }}>
      {children}
    </div>
  );
};

/** Kinetic headline: words rise in one after another. */
export const Kinetic: React.FC<{ text: string; delay?: number; size?: number; weight?: number; color?: string; accent?: string[]; style?: React.CSSProperties }> = ({
  text,
  delay = 0,
  size = 84,
  weight = 750,
  color = C.text,
  accent = [],
  style,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const words = text.split(" ");
  return (
    <div style={{ fontSize: size, fontWeight: weight, letterSpacing: "-0.03em", lineHeight: 1.08, color, ...style }}>
      {words.map((w, i) => {
        const s = spring({ frame: frame - delay - i * 3, fps, config: { damping: 18, mass: 0.6, stiffness: 140 } });
        const clean = w.replace(/[.,:]/g, "");
        return (
          <span key={i} style={{ display: "inline-block", overflow: "hidden", verticalAlign: "top", paddingBottom: "0.08em" }}>
            <span
              style={{
                display: "inline-block",
                translate: `0px ${(1 - Math.min(1, s)) * 1.05 * size}px`,
                opacity: Math.min(1, s * 1.4),
                color: accent.includes(clean) ? C.accent : undefined,
              }}
            >
              {w}
              {i < words.length - 1 ? " " : ""}
            </span>
          </span>
        );
      })}
    </div>
  );
};

export const Eyebrow: React.FC<{ children: React.ReactNode; color?: string; style?: React.CSSProperties }> = ({ children, color = C.accent, style }) => (
  <div style={{ fontFamily: MONO, fontSize: 24, letterSpacing: "0.18em", textTransform: "uppercase", color, fontWeight: 500, ...style }}>
    {children}
  </div>
);

export const Footnote: React.FC<{ children: React.ReactNode; delay?: number; style?: React.CSSProperties }> = ({ children, delay = 0, style }) => {
  const s = useSpring(delay);
  return (
    <div style={{ position: "absolute", left: 120, right: 120, bottom: 64, fontSize: 24, color: C.dim, opacity: s, lineHeight: 1.4, ...style }}>
      {children}
    </div>
  );
};

/** A floating framed window, product-UI style. */
export const Window: React.FC<{
  title: string;
  right?: React.ReactNode;
  delay?: number;
  style?: React.CSSProperties;
  bodyStyle?: React.CSSProperties;
  glow?: number;
  children: React.ReactNode;
}> = ({ title, right, delay = 0, style, bodyStyle, glow = 0, children }) => {
  const s = useSpring(delay, 200, 26);
  return (
    <div
      style={{
        position: "absolute",
        background: `linear-gradient(180deg, ${C.panel2}, ${C.panel})`,
        border: `1px solid ${C.line}`,
        borderRadius: 22,
        boxShadow: `0 40px 90px rgba(15,23,42,0.12), 0 0 0 1px rgba(15,23,42,0.02), 0 0 ${60 * glow}px rgba(2,132,199,${0.35 * glow})`,
        overflow: "hidden",
        opacity: s,
        translate: `0px ${(1 - s) * 50}px`,
        scale: String(0.96 + 0.04 * s),
        ...style,
      }}
    >
      <div
        style={{
          height: 58,
          display: "flex",
          alignItems: "center",
          gap: 10,
          padding: "0 22px",
          borderBottom: `1px solid ${C.line}`,
          background: "rgba(15,23,42,0.02)",
        }}
      >
        {[0, 1, 2].map((i) => (
          <div key={i} style={{ width: 13, height: 13, borderRadius: 7, background: "rgba(15,23,42,0.14)" }} />
        ))}
        <div style={{ marginLeft: 14, fontFamily: MONO, fontSize: 21, color: C.dim, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", flex: 1 }}>
          {title}
        </div>
        {right}
      </div>
      <div style={{ padding: 28, ...bodyStyle }}>{children}</div>
    </div>
  );
};

export const Chip: React.FC<{ children: React.ReactNode; color?: string; bg?: string; delay?: number; style?: React.CSSProperties }> = ({
  children,
  color = C.accent,
  bg = C.accentSoft,
  delay = 0,
  style,
}) => {
  const s = useSpring(delay, 14);
  return (
    <span
      style={{
        display: "inline-block",
        fontFamily: MONO,
        fontSize: 24,
        padding: "8px 16px",
        borderRadius: 999,
        color,
        background: bg,
        border: `1px solid ${color}44`,
        opacity: Math.min(1, s * 1.5),
        scale: String(0.7 + 0.3 * Math.min(1.08, s)),
        ...style,
      }}
    >
      {children}
    </span>
  );
};

/** Big number tile with count-up. */
export const Stat: React.FC<{ value: number; decimals?: number; suffix?: string; label: React.ReactNode; delay?: number; color?: string; style?: React.CSSProperties; size?: number }> = ({
  value,
  decimals = 0,
  suffix = "%",
  label,
  delay = 0,
  color = C.accent,
  style,
  size = 120,
}) => {
  const s = useSpring(delay, 200, 40);
  const frame = useCurrentFrame();
  const count = interpolate(frame, [delay, delay + 34], [0, value], { ...clamp, easing: out });
  return (
    <div
      style={{
        background: `linear-gradient(180deg, ${C.panel2}, ${C.panel})`,
        border: `1px solid ${C.line}`,
        borderRadius: 24,
        padding: "30px 36px",
        boxShadow: "0 30px 70px rgba(15,23,42,0.12)",
        opacity: s,
        translate: `0px ${(1 - s) * 40}px`,
        ...style,
      }}
    >
      <div style={{ fontSize: size, fontWeight: 800, letterSpacing: "-0.04em", color, lineHeight: 1, fontVariantNumeric: "tabular-nums" }}>
        {decimals ? (value >= 0 ? "+" : "") + count.toFixed(decimals) : Math.round(count)}
        <span style={{ fontSize: size * 0.55 }}>{suffix}</span>
      </div>
      <div style={{ fontSize: 30, color: C.dim, marginTop: 14, lineHeight: 1.3 }}>{label}</div>
    </div>
  );
};

/** HandoffDB mark: three linked nodes, drawn in with t (0..1), pulse travelling along edges. */
export const Mark: React.FC<{ size: number; t?: number; pulse?: number; color?: string; opacity?: number }> = ({ size, t = 1, pulse, color = C.accent, opacity = 1 }) => {
  const P = [[-58, -40], [58, -40], [0, 56]];
  const cols = [C.accent, C.teal, C.warn];
  const E = [[0, 1], [0, 2], [1, 2]];
  return (
    <svg width={size} height={size} viewBox="-100 -100 200 200" style={{ opacity, overflow: "visible" }}>
      {E.map(([a, b], i) => {
        const q = Math.max(0, Math.min(1, t * 3 - i));
        const [x1, y1] = P[a], [x2, y2] = P[b];
        const u = pulse === undefined ? -1 : (pulse + i / 3) % 1;
        return (
          <g key={i}>
            <line x1={x1} y1={y1} x2={x1 + (x2 - x1) * q} y2={y1 + (y2 - y1) * q} stroke={color} strokeWidth={9} strokeLinecap="round" strokeOpacity={0.55} />
            {u >= 0 && q >= 1 ? <circle cx={x1 + (x2 - x1) * u} cy={y1 + (y2 - y1) * u} r={8} fill={cols[b]} /> : null}
          </g>
        );
      })}
      {P.map(([x, y], i) => {
        const q = Math.max(0, Math.min(1, t * 3 - i * 0.6));
        return <circle key={i} cx={x} cy={y} r={24 * q} fill="#ffffff" stroke={cols[i]} strokeWidth={10} />;
      })}
    </svg>
  );
};

/** Old compass mark (unused in the HandoffDB cut). */
export const Compass: React.FC<{ size: number; needle?: number; ring?: number; opacity?: number; color?: string; noNeedle?: boolean }> = ({
  size,
  needle = 40,
  ring = 0,
  opacity = 1,
  color = C.accent,
  noNeedle = false,
}) => (
  <svg width={size} height={size} viewBox="-100 -100 200 200" style={{ opacity, overflow: "visible" }}>
    <g style={{ rotate: `${ring}deg` }}>
      <circle r={92} fill="none" stroke="rgba(15,23,42,0.22)" strokeWidth={2.5} />
      {Array.from({ length: 72 }).map((_, i) => {
        const major = i % 18 === 0;
        const r1 = major ? 76 : i % 6 === 0 ? 82 : 86;
        const a = (i / 72) * Math.PI * 2;
        return (
          <line
            key={i}
            x1={Math.sin(a) * r1}
            y1={-Math.cos(a) * r1}
            x2={Math.sin(a) * 92}
            y2={-Math.cos(a) * 92}
            stroke={major ? color : "rgba(15,23,42,0.3)"}
            strokeWidth={major ? 3.5 : 1.6}
          />
        );
      })}
    </g>
    <g style={{ rotate: `${needle}deg`, display: noNeedle ? "none" : undefined }}>
      <path d="M0,-66 L11,0 L0,8 L-11,0 Z" fill={color} />
      <path d="M0,66 L11,0 L0,-8 L-11,0 Z" fill="rgba(15,23,42,0.28)" />
      <circle r={7} fill={C.bg} stroke={color} strokeWidth={3} />
    </g>
  </svg>
);

export const fmt = (n: number) => Math.round(n).toLocaleString("en-US");
