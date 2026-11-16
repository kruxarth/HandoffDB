// Render stills at fractions of every scene for a visual check: node check_frames.mjs [scene ...]
import { bundle } from "@remotion/bundler";
import { renderStill, selectComposition } from "@remotion/renderer";
import fs from "node:fs";
import path from "node:path";
const tl = JSON.parse(fs.readFileSync("public/timeline.json", "utf8"));
const only = process.argv.slice(2);
const fracs = (process.env.FRACS || "0.35,0.8").split(",").map(Number);
const serveUrl = await bundle({ entryPoint: path.resolve("src/index.ts") });
const comp = await selectComposition({ serveUrl, id: "BearingsLaunch" });
fs.mkdirSync("out/frames", { recursive: true });
for (const sc of tl.scenes) {
  if (only.length && !only.includes(sc.name)) continue;
  for (const f of fracs) {
    const frame = sc.start + Math.round(sc.frames * f);
    const output = `out/frames/${sc.name}_${Math.round(f * 100)}.jpg`;
    await renderStill({ serveUrl, composition: comp, frame, output, imageFormat: "jpeg", jpegQuality: 80, scale: 0.5 });
    console.log(output);
  }
}
