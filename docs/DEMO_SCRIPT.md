# Demo: 3 minutes

The official rules require a three-minute video showing only what was built during the hackathon. Judges score it on Impact, Use of Meta AI Tooling, Technical Depth and Execution, and Demo, and the final round watches it live. Every number comes from `eval/results.csv`, `eval/field_results.csv` or a cached run JSON. Brackets mark values to fill from those files, never from memory.

## Script

| Time | On screen | Voiceover | Criterion it serves |
| --- | --- | --- | --- |
| 0:00 to 0:12 | Jitter title: "AI guesses." then "Caliper measures." over a passing car | "Ask an AI how fast this car is going." | Demo hook |
| 0:12 to 0:30 | Workspace, compare switch on. Muse Spark alone gives its guess on a dashed card; cut to the friend's GPS reading | "Muse Spark says [guess]. The GPS says [truth]. Stanford's QuantiPhy shows this isn't a one-off: frontier models guess physical numbers from memory." | Impact, problem |
| 0:30 to 0:58 | Same clip through Caliper: spec JSON appears, cyan car outline and amber markers from SAM 3.1, the trajectory, the fit, then [value] with its range beside the GPS value | "Caliper uses each tool for what it's good at. Muse Spark reads the question and decides what to measure against. SAM 3.1 tracks the pixels. Plain code does every number and its error range." | Meta tooling, depth |
| 0:58 to 1:12 | The audit panel: keyframes with overlays, Muse Spark's verdict; then a clip where the audit vetoes (wrong object, or a coin held closer to the camera) | "Then Muse Spark audits the evidence, without seeing any numbers. Here it caught SAM following the wrong object, so Caliper refuses instead of answering." | Meta tooling (surprising use), depth |
| 1:12 to 1:25 | Live: drop a ball in front of the A4 sheet; result card shows gravity with its range | "Live: a dropped ball. [g value], against 9.81." | Demo holds up live |
| 1:25 to 2:05 | `/study`: a real Hyderabad street, two gates 10 m apart, every vehicle tagged with speed and range, some marked "no reading"; summary card with median and 85th-percentile speed with its range, share over the limit, printable report | "Road deaths in India reached 177,175 in 2024, and the ministry attributes 70.3% to over-speeding. Traffic engineers decide on calming with the 85th-percentile speed. Caliper turns three minutes of phone video into that number, with honest error bars and no guesses on vehicles it can't measure." | Impact |
| 2:05 to 2:35 | `/results`: holdout MRA chart (Muse Spark alone, Caliper, humans 55.6); field accuracy; speed study error vs GPS on set A; audit catches vs false vetoes | "On QuantiPhy's held-out videos: Muse Spark alone [x], Caliper [y], humans 55.6. On our own 30 clips, median error [z]. Per-vehicle speed against GPS: [w] km/h." | Depth, evidence |
| 2:35 to 2:50 | Stretch, only if built: the backend switch set to Muse Spark Open on Baseten, same clip, same answer; or an agent calling `measure()` over MCP | "The same pipeline runs on Meta's open weights. And any agent can call it as a tool." | Meta tooling, bonus prizes |
| 2:50 to 3:00 | Jitter architecture card; text "Built Oct 27 to Nov 4 2026"; repo URL | "Every number traces to a mask, a formula, and an audit. Everything you saw was built during this hackathon." | Rules compliance |

If a result disproves a claim (see docs/EVAL_PROTOCOL.md), change the voiceover to say so. Do not cut it. If the stretch items are not built, give their 15 seconds to the street study.

## X post (for the Most Viral Project prize)

- A 30 to 45 second cut: the guess vs GPS hook, the street full of tagged vehicles, the refusal. Burned-in captions; first frame must make sense without sound.
- Text: one line on the problem, one on what Caliper does, the repo link. Tag the official hackathon accounts named on the event page.
- Post as soon as the submission is in; submit the post link on the CV platform. Engagement counts until Nov 8 EOD.

## Jitter assets

1. Title card: two lines, Instrument Serif, amber underline on "measures". 4 s.
2. Architecture card: Video + question, Muse Spark 1.3, SAM 3.1, Physics engine, Checks, Audit, then "Answer" or "Abstain". 6 s.
3. Closing card with "Built Oct 27 to Nov 4 2026" and the repo URL.

Export 1080p or higher. Check the Jitter plan's export limits before relying on it.

## Recording checklist

- [ ] Browser at 1440 x 900, dark OS theme, notifications off, bookmarks bar hidden
- [ ] Cached runs ready so recording does not depend on the API; one live take for the ball drop
- [ ] No QuantiPhy video frames anywhere in the video
- [ ] No readable number plates or faces in the street footage (blur or crop)
- [ ] Voiceover recorded separately, clean audio; captions burned in
- [ ] Length 3:00 or less
- [ ] Every number checked against the data files
- [ ] Only features built during the hackathon are shown
