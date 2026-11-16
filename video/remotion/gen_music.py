"""Synthesize a soft ambient pad for the video (no samples, no downloads).

  uv run --with numpy python video/remotion/gen_music.py

Length comes from public/timeline.json; writes public/music.wav.
"""

import json
import wave
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
SR = 44100
tl = json.load(open(HERE / "public" / "timeline.json"))
dur = tl["frames"] / tl["fps"]
t = np.arange(int(dur * SR)) / SR

# Am – F – C – G, 8 s per chord
CHORDS = [[57, 60, 64, 69], [53, 57, 60, 65], [48, 55, 60, 64], [55, 59, 62, 67]]
BAR = 8.0
f = lambda m: 440 * 2 ** ((m - 69) / 12)  # noqa: E731
out = np.zeros_like(t)
for k in range(int(dur / BAR) + 2):
    notes = CHORDS[k % 4]
    t0 = k * BAR - 1.5
    env = np.clip((t - t0) / 2.5, 0, 1) * np.clip((t0 + BAR + 3.0 - t) / 2.5, 0, 1)
    env = env ** 2 * (3 - 2 * env)  # smoothstep
    seg = np.zeros_like(t)
    for i, m in enumerate(notes):
        for det in (-0.12, 0.12):
            ph = 2 * np.pi * f(m + det / 10) * t
            seg += np.sin(ph) * (0.6 if i else 0.9) + 0.12 * np.sin(2 * ph)
    seg += 0.5 * np.sin(2 * np.pi * f(notes[0] - 12) * t)  # sub
    out += seg * env
# slow breathing + master fades
out *= 0.85 + 0.15 * np.sin(2 * np.pi * t / 11)
out *= np.clip(t / 3, 0, 1) * np.clip((dur - t) / 4, 0, 1)
out = out / np.max(np.abs(out)) * 0.5
pcm = (out * 32767).astype(np.int16)
stereo = np.stack([pcm, pcm], 1).tobytes()
with wave.open(str(HERE / "public" / "music.wav"), "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(stereo)
print(f"music.wav {dur:.1f} s")
