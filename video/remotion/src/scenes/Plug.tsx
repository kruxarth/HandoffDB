import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { C, MONO, Scene, SceneData, Window, Kinetic, Eyebrow, clamp, out, useSpring } from "../ui";

const Step: React.FC<{ n: string; title: string; sub: string; delay: number; hook?: boolean }> = ({ n, title, sub, delay, hook }) => {
  const s = useSpring(delay, 200, 24);
  return (
    <div style={{ display: "flex", gap: 22, alignItems: "flex-start", opacity: s, translate: `${(1 - s) * -30}px 0px`, marginBottom: 44 }}>
      <div
        style={{
          width: 52,
          height: 52,
          borderRadius: 14,
          flex: "0 0 auto",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: hook ? C.accent : C.panel2,
          color: hook ? C.bg : C.dim,
          fontFamily: MONO,
          fontSize: 24,
          fontWeight: 700,
          border: `1px solid ${C.line}`,
        }}
      >
        {n}
      </div>
      <div>
        <div style={{ fontSize: 38, fontWeight: 600, color: hook ? C.accent : C.text, fontFamily: hook ? MONO : undefined }}>{title}</div>
        <div style={{ fontSize: 28, color: C.dim, marginTop: 6 }}>{sub}</div>
      </div>
    </div>
  );
};

export const Plug: React.FC<{ sc: SceneData }> = ({ sc }) => {
  const frame = useCurrentFrame();
  const mcp = Math.round(sc.frames * 0.62);
  const pulse = interpolate(frame % 40, [0, 20, 40], [0.2, 1, 0.2]);
  return (
    <Scene sc={sc}>
      <div style={{ position: "absolute", left: 120, top: 96 }}>
        <Eyebrow>Delivery</Eyebrow>
        <div style={{ height: 18 }} />
        <Kinetic text="No extra turn for the agent." size={80} delay={4} />
      </div>
      <Window title="Claude Code · .claude/settings.json hooks" delay={10} style={{ left: 120, top: 320, width: 1000, height: 640 }} bodyStyle={{ padding: "48px 50px" }}>
        <Step n="1" title="You type a task" sub="as usual" delay={22} />
        <Step n="⤷" title="UserPromptSubmit" sub="the context pack is added to your prompt" delay={36} hook />
        <Step n="2" title="The agent works" sub="starting in the right files" delay={56} />
        <Step n="⤷" title="Stop" sub="git status → what changed is learned" delay={74} hook />
      </Window>
      <Window
        title="any other agent · MCP"
        delay={mcp - 8}
        style={{ left: 1180, top: 320, width: 620, height: 640 }}
        bodyStyle={{ padding: "48px 44px" }}
      >
        {["get_context_pack", "report_task"].map((t, i) => {
          const s = interpolate(frame, [mcp + i * 8, mcp + 14 + i * 8], [0, 1], { ...clamp, easing: out });
          return (
            <div
              key={t}
              style={{
                fontFamily: MONO,
                fontSize: 34,
                padding: "26px 28px",
                borderRadius: 16,
                marginBottom: 22,
                background: C.accentSoft,
                border: `1px solid ${C.accent}55`,
                color: C.accent,
                opacity: s,
                translate: `0px ${(1 - s) * 20}px`,
              }}
            >
              {t}()
            </div>
          );
        })}
        <div style={{ fontSize: 30, color: C.dim, marginTop: 26, lineHeight: 1.45, opacity: interpolate(frame, [mcp + 20, mcp + 34], [0, 1], clamp) }}>
          OpenCode and other MCP clients.
          <br />
          Same graph, same packs.
        </div>
        <div style={{ position: "absolute", right: 40, bottom: 34, width: 14, height: 14, borderRadius: 7, background: C.accent, opacity: pulse * interpolate(frame, [mcp, mcp + 10], [0, 1], clamp) }} />
      </Window>
    </Scene>
  );
};
