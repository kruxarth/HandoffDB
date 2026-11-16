"""Timeline for the Remotion launch video.

  python3 video/remotion/prep.py

Reads video/narration.json and the matching video/audio/<id>_<hash>.wav clips,
copies the clips into public/audio/ (gitignored: the voice stays local), and
writes public/timeline.json: every scene's length and every line's start frame,
so each scene is timed to its own narration.
"""

from __future__ import annotations

import hashlib
import sys
import json
import shutil
import wave
from pathlib import Path

HERE = Path(__file__).resolve().parent
V = HERE.parent
FPS = 30
DRAFT = "--draft" in sys.argv
LEAD = 0.5  # seconds before a scene's first line
GAP = 0.55  # between lines inside a scene
TAIL = {"default": 0.9, "end": 3.2, "curve": 1.6, "problem": 0.9}


def main() -> None:
    lines = json.load(open(V / "narration.json"))
    pub = HERE / "public" / "audio"
    pub.mkdir(parents=True, exist_ok=True)
    scenes: list[dict] = []
    t = 0
    for ln in lines:
        h = hashlib.sha1(ln["text"].encode()).hexdigest()[:8]
        src = V / "audio" / f"{ln['id']}_{h}.wav"
        if src.exists():
            with wave.open(str(src)) as w:
                dur = w.getnframes() / w.getframerate()
            shutil.copy(src, pub / f"{ln['id']}.wav")
        elif DRAFT:  # estimate, so layout work can start before the voice is ready
            dur = len(ln["text"].split()) / 2.7
            print(f"  (draft) no audio yet for {ln['id']}, estimating {dur:.1f} s")
        else:
            raise SystemExit(f"missing audio for line {ln['id']}: run video/gen_audio.sh (or pass --draft)")
        if not scenes or scenes[-1]["name"] != ln["scene"]:
            scenes.append({"name": ln["scene"], "lines": [], "cursor": round(LEAD * FPS)})
        sc = scenes[-1]
        sc["lines"].append({"id": ln["id"], "text": ln["text"], "from": sc["cursor"],
                            "frames": round(dur * FPS), "src": f"audio/{ln['id']}.wav"})
        sc["cursor"] += round((dur + GAP) * FPS)
    for sc in scenes:
        last = sc["lines"][-1]
        tail = TAIL.get(sc["name"], TAIL["default"])
        sc["frames"] = last["from"] + last["frames"] + round(tail * FPS)
        sc["start"] = t
        t += sc["frames"]
        del sc["cursor"]
    out = {"fps": FPS, "frames": t, "scenes": scenes}
    (HERE / "public" / "timeline.json").write_text(json.dumps(out, indent=1))
    print(f"{len(scenes)} scenes, {t / FPS:.1f} s")
    for sc in scenes:
        print(f"  {sc['name']:8s} {sc['frames'] / FPS:5.1f} s  ({len(sc['lines'])} lines)")


if __name__ == "__main__":
    main()
