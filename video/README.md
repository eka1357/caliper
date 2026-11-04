# Caliper demo video

The 3-minute demo and the 40-second X cut, built with [Remotion](https://www.remotion.dev).
No number is typed anywhere: `src/data/facts.ts` builds every value shown or spoken from
`web/public/results.json` and the run JSONs in `web/public/runs/`, through the site's own functions.

Footage is our own: the field clips (with the site's blur of faces, plates and the phone case's
drawing), screen recordings of the live site (recorded runs only), and a captured MCP session. No
QuantiPhy footage is used.

## Rebuild

Generated media lives in `public/` (gitignored). From `video/`:

```
node --no-warnings scripts/narration.mts resolve            # fill narration.md tokens ($0)
node --no-warnings scripts/narration.mts generate s1 ... x7 # ElevenLabs (ELEVENLABS_API_KEY in ../.env)
../backend/.venv/Scripts/python.exe scripts/export_footage.py C07 A14 A08   # $0, cache only
../backend/.venv/Scripts/python.exe scripts/mcp_capture.py  # $0, cache only -> data/mcp/session.json
node --no-warnings scripts/record.mts                       # live site recordings (screencast)
node --no-warnings scripts/prep.mts                         # audit keyframes; music if assets/music.mp3
npx remotion render Demo out/demo_raw.mp4 --concurrency=2
npx remotion render XCut out/x_raw.mp4 --concurrency=2
node --no-warnings scripts/finish.mts out/demo_raw.mp4 out/caliper_demo.mp4   # -16 LUFS
node --no-warnings scripts/finish.mts out/x_raw.mp4 out/caliper_x_cut.mp4
```

Narration: `narration.md` (ElevenLabs voice "River", `eleven_multilingual_v2`, stability 0.5).
Scene lengths follow the narration (`src/timeline.ts`); speech is never sped up.
