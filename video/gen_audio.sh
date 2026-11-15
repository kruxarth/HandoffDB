#!/usr/bin/env bash
# Generate narration lines (skips lines whose wav exists and matches the text hash).
cd "$(dirname "$0")"
python3 - <<'PY'
import json, hashlib, os, subprocess
for line in json.load(open("narration.json")):
    h = hashlib.sha1(line["text"].encode()).hexdigest()[:8]
    out = f"audio/{line['id']}_{h}.wav"
    if os.path.exists(out):
        continue
    for old in [f for f in os.listdir("audio") if f.startswith(line["id"] + "_")]:
        os.remove("audio/" + old)
    body = json.dumps({"model": "omnivoice", "input": line["text"], "voice": "f6f18cfb", "language": "en", "response_format": "wav"})
    subprocess.run(["curl", "-s", "-f", "-o", out + ".part", "-X", "POST", "http://127.0.0.1:3900/v1/audio/speech",
                    "-H", "Content-Type: application/json", "-d", body], check=True)
    os.rename(out + ".part", out)
    print("done", out, flush=True)
PY
