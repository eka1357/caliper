# Decision log

Newest first. Add a row whenever a decision changes scope, architecture, metrics, tools, or thresholds.

| Date | Decision | Why | Revisit if |
| --- | --- | --- | --- |
| 2026-10-28 | Dev tuning B try 1 (human-approved, max 2 tries): simulation_0193 moon phrase "moon" -> "small sphere" in `eval/specs/phase1_dev_2d.json` | "moon" returned no detections in the untuned dev run, so all 12 questions on the clip abstained | Try 1 also finds nothing (then try 2, then stop) |
| 2026-10-28 | Dev tuning A (human-approved): the 30%-of-frames candidate filter applies only to `auto`; comparative selectors keep candidates with at least FIT_MIN_POINTS (5) frames. Abstain when the target and another role resolve to the same track with different selectors | Untuned dev run: "bird" on simulation_0089 found birds on 10 and 7 of 30 frames; the filter dropped one, so "largest" and "smallest" both picked the same bird (rows 139 to 144) | Holdout shows comparative selectors picking flicker detections |
| 2026-10-28 | Engine rules from Phase 0 findings: time base is ffprobe fps on the normalized video (dataset fps mismatches logged); fits and path lengths use detected frames only, no interpolation; size uses frames within 15% of the median mask area; acceleration is the magnitude of the fitted vector (or one axis component) | Phase 0 showed fps mismatch (internet_0001), dropped frames on 7 of 20 clips, and an object that changes mid-clip (captured_0034as); the motion direction is undefined at turning points | Dev results show a rule costing accuracy |
| 2026-10-28 | MeasurementSpec additions: instance selectors (left/right/middle/top/bottom/largest/smallest/center_rank:k/auto), second object, statistics `separation` and `orbit_diameter`, reference kind `acceleration` with `reference_statistic`/`reference_axis`, axes `shortest` and `disc`, `time_anchor`, `time_range_s`. Instance `auto` = longest continuous track (was: most frames), candidates under 30% of frames dropped | Dev 2D questions ask for distances between objects, orbit diameters, averages over time windows, and use a gravity prior; Phase 0 showed phrases matching up to 6 objects | Phase 2 spec writer cannot fill the fields reliably |
| 2026-10-28 | QuantiPhy split: seeded shuffle (seed 20261027) stratified by video dimension, 6 of 12 2D and 6 of 12 3D videos per side; frozen in `eval/split.csv` by `eval/make_split.py` | The sha256 rule gave 8 dev / 16 holdout videos, outside the protocol's 10 to 14, so its seeded-shuffle fallback applies; an unstratified shuffle left holdout with 15 2D vs 68 3D questions. Human chose stratified | Never (the split is frozen) |
| 2026-10-26 | Live cost caps: $0.50 per measure run, $1.50 per study (60 s max), $5 a day, each checked on a cost estimate before any API call | The first caps contradicted each other: a $0.25 run cap would have refused every live study (a 3-minute study is about $3.24) | Judges hit the caps often during judging |
| 2026-10-26 | Start all code at Oct 27 00:00 ET (9:30 AM IST) | Official building period is Oct 27 to Nov 4; removes any "new work only" doubt | Never |
| 2026-10-26 | Add a second Muse Spark call: visual audit, veto only | New rubric scores Use of Meta AI Tooling equally; the audit catches wrong-object tracks and out-of-plane references that checks cannot see, and it is measured (A2) | Audit vetoes many correct results on dev |
| 2026-10-26 | Add the street speed study as the real-world showcase | Impact is a quarter of the score; the 85th-percentile speed is the number engineers use; India road deaths 177,175 in 2024 with 70.3% attributed to over-speeding (MoRTH, via Hindustan Times) | Set A per-vehicle error misses the H5 target |
| 2026-10-26 | Acknowledge prior art: SpeedCam AI already estimates vehicle speeds and 85th percentiles from phone video | Honest positioning; our difference is per-vehicle error ranges, refusals, an audited and benchmarked method, and the general engine | n/a |
| 2026-10-26 | Live runs on for judging, with caps; cached runs always available | Judges score the live product and whether it "holds up live" | Spend approaches the cap |
| 2026-10-26 | Stretch: Muse Spark Open backend on Baseten | Eligible for the $10K open-weights bonus; another Meta model used meaningfully | Phases 0 to 5 slip |
| 2026-10-26 | Frequency module dropped | Time goes to the audit and the speed study instead | Never for this event |
| 2026-10-26 | Demo is 3 minutes; X post cut of 30 to 45 s | Official requirement; Most Viral bonus | n/a |
| 2026-10-21 | Dark theme only | One polished theme beats two rushed ones; instrument aesthetic | Rules or judges require light mode |
| 2026-10-21 | Barba.js not used | Designed for multi-page sites; conflicts with Next.js client routing | Never for this project |
| 2026-10-21 | GSAP and Lenis on `/` only; Lenis driven by `gsap.ticker` | One animation clock; keeps `/workspace` fast | Landing performance fails QA |
| 2026-10-21 | Next.js + FastAPI instead of Streamlit | Design quality matters for the demo; reuse Gauntlet's replay-mode pattern | Time runs short on Day 7: fall back to Streamlit for the workspace |
| 2026-10-21 | (Superseded 2026-10-26) Hosted demo in replay mode, `LIVE_RUNS_ENABLED=false` by default | Protects credits; demo never depends on live API | Rules require live judging access |
| 2026-10-21 | SAM 3.1: one request per concept (target, reference) | Meta docs: one concept per request, 16 objects per frame | API adds multi-concept prompts |
| 2026-10-21 | Dev and holdout split on QuantiPhy validation | 158 questions is small; avoid tuning on what we report | Never |
| 2026-10-21 | Muse Image not used | Not available in India per Meta's geographic policy | Policy changes |
| 2026-10-19 | Narrow scope to size, speed, acceleration | QuantiPhy tests exactly these; five quantity types was too broad | Phases 0 to 5 finish early |
| 2026-10-19 | (Amended 2026-10-26: audit call added) One model call plus deterministic math; no multi-agent layer | Agents added no capability; the rule-parser ablation is the honest control | Ablation shows a specific gap a second call fixes |

## Measured facts to record (fill during Phase 0)

| Fact | Value | How measured |
| --- | --- | --- |
| Muse Spark tokens per QuantiPhy question with video | Input mean 41,259 (median 29,334; range 14,677 to 219,261); output mean 8,857 (median 7,726; range 1,741 to 32,106), mostly reasoning; about 514 input tokens per frame image; latency median 74 s, max 252 s | `eval/cost_summary.py` over the 158 cached baseline chat records (official zero-shot v3 prompt, every frame sent as an image) |
| SAM 3.1 latency per 90-frame clip | Median 8.3 s on the 7 clips with 60 to 120 frames; median 11.6 s when each request is scaled to 90 frames; range 4.2 to 31.7 s per request (30 to 428 frames). Includes the Files upload | `eval/cost_summary.py` over the 23 cached SAM records (20 tracking clips, 3 phrase-corrected reruns; the smoke clip is one of the 20) |
| Cost of one full validation run | $14.10 for the Muse Spark alone baseline (158 questions, $0.089 per question, no retries needed). All of Phase 0 so far: $14.62 ($14.10 baseline, $0.47 SAM for 2,359 frames, $0.06 smoke and phrase calls) | `eval/cost_summary.py`; token prices from AGENTS.md section 3 |
| SAM wrong-object rate on 20 clips | 0 of 20 wrong object; 3 of 20 lost (simulation_0089, internet_0005, internet_0013: no detections with the first-question phrase), 17 right object. With the phrase corrected for those 3 (`eval/phase0_tracking_corrected.csv`): 3 of 3 right object, so 20 of 20 right object, 0 wrong, 0 lost | Human verdict per overlay in `eval/phase0_overlays/`, stored in `my_verdict` of both tracking CSVs; counted by `eval/cost_summary.py` |
