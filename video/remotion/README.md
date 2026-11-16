# Bearings launch video (Remotion)

    bash ../gen_audio.sh            # narration lines via a local TTS server (audio is not committed)
    python3 gen_music.py            # background music into public/music.wav
    python3 export_data.py          # numbers from ../../results into public/data.json
    python3 prep.py                 # timeline from narration + audio (--draft estimates missing audio)
    npx remotion render src/index.ts BearingsLaunch ../out/bearings_launch.mp4
