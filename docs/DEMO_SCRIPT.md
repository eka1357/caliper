# Demo: 90 seconds

Every number in the video comes from `eval/results.csv` or a cached run JSON. Brackets mark values to fill from those files, never from memory.

## Script

| Time | On screen | Voiceover |
| --- | --- | --- |
| 0 to 8 s | Jitter title card: "AI guesses." then "Caliper measures." | "Ask an AI how fast this car is going." |
| 8 to 18 s | Workspace, compare switch on. Muse Spark alone answers with its guess, dashed card. Cut to the GPS reading | "Muse Spark says [guess]. The GPS says [truth]. That's a guess, not a measurement." |
| 18 to 38 s | Same clip in Caliper: spec appears, cyan target outline, amber reference, trajectory, then the number with its range beside the GPS value | "Caliper reads the question, finds the car and the 10-metre markers with SAM 3.1, and does the maths in plain code: [value] plus or minus [half-width]." |
| 38 to 55 s | Live: drop a ball next to the marker card; result card shows gravity with its range | "Live, a dropped ball: [g value]. Gravity is 9.81." |
| 55 to 68 s | A clip with no reference. The "I won't guess" card with its reason and fix | "And when the video can't support a number, it says so instead of guessing." |
| 68 to 83 s | `/results`: bklit bar chart, holdout MRA by variant with the human baseline line; field accuracy line | "On Stanford's QuantiPhy holdout: Muse Spark alone [x], Caliper [y], humans 55.6. On our 30 real clips, median error [z]." |
| 83 to 90 s | Jitter architecture animation lights up; repo URL | "One model call, SAM 3.1, and verifiable maths. Every number traces back to a mask." |

If a result disproves a claim (see docs/EVAL_PROTOCOL.md), change the voiceover to say so. Do not cut it.

## Jitter assets

1. Title card: two lines, Instrument Serif, amber underline on "measures". 4 s.
2. Architecture: five boxes (Video + question, Muse Spark 1.3, SAM 3.1, Physics engine, Checks) lighting up left to right, then splitting to "Answer" or "Abstain". 6 s.
3. Chart reveal (optional): only if the bklit chart recording looks weak. Use the exact values from `results.json`.

Export at the resolution the rules require (assume 1080p if unstated). Check the Jitter plan's export limits on day 1 of filming.

## Recording checklist

- [ ] Browser at 1440 x 900, dark OS theme, notifications off, bookmarks bar hidden
- [ ] Demo clips cached so recording does not depend on the API
- [ ] One live take for the ball drop, with the cached run as backup
- [ ] Voiceover recorded separately, clean audio
- [ ] Captions burned in or provided
- [ ] Final length under the limit in the official rules
- [ ] Every number in the video checked against the data files
