# Product requirements: Caliper

## Problem

People and AI agents ask numeric questions about video ("how fast was that car?", "how tall is that shelf?") and act on the answers. Vision-language models answer with confident guesses. On Stanford's QuantiPhy benchmark, which asks for size, speed and acceleration from short videos, the best model on the public leaderboard scores below the human baseline, and the authors found models still answer plausibly with no video at all ([Stanford HAI](https://hai.stanford.edu/news/ai-cant-do-physics-well-and-thats-a-roadblock-to-autonomy), [leaderboard](https://quantiphy.stanford.edu/)). Measurement tools such as Tracker are accurate but need a person to calibrate, click and choose the method for every clip.

The cost is real on roads. India recorded 177,175 road deaths in 2024, and the transport ministry attributes 70.3% of them to over-speeding ([Hindustan Times on the MoRTH 2024 report](https://www.hindustantimes.com/india-news/road-accident-deaths-increased-2-5-in-2024-from-2023-morth-report-101781204793385.html)). Decisions about speed humps and calming rest on the 85th-percentile speed of a street ([FHWA traffic calming ePrimer](https://highways.dot.gov/safety/speed-management/traffic-calming-eprimer/module-4-effects-traffic-calming-measures-motor)), which residents cannot measure without a radar gun or a survey.

## Solution

Caliper takes a free-form question and a video, decides what to measure against, tracks the pixels, computes the number with deterministic code, attaches a 90% interval, has Muse Spark audit the evidence, and refuses when the video cannot support an answer. The street speed study applies the same engine to every vehicle on a street and reports the 85th-percentile speed with its range.

## Users

| User | Job | Demo moment |
| --- | --- | --- |
| Residents and road engineers | Get a defensible speed survey of a street from a phone | `/study`: three minutes of street video becomes a median and 85th-percentile speed with ranges and refusals |
| Agent builders | Give an agent a physical measurement instead of a guess | Another agent calls `measure()` (stretch) |
| Judges | Decide if it works | Same clip: Muse Spark guesses, Caliper measures, the GPS agrees; the audit catches a wrong object |

## Prior art and our difference

- Tracker and similar tools: accurate, manual. Caliper is automatic from a free-form question.
- QuantiPhy challenge entries: tool pipelines on a benchmark. Caliper adds abstention, an audit, field validation, and a product.
- SpeedCam AI (iOS) estimates vehicle speeds and 85th percentiles from phone video and states its accuracy is for trend analysis, not individual vehicles ([App Store](https://apps.apple.com/us/app/speedcam-ai-traffic-monitor/id6762230721)). Caliper's difference: a stated error range per vehicle, explicit refusals, an audited method, and validation against GPS.

## Scope

Must have
- Quantities: size, speed (instantaneous and average), acceleration.
- Scale from a given prior or a known-size object (A4 sheet, INR 10 coin, measured markers).
- 90% interval for every measured value; abstention with a reason and a fix.
- Visual audit by Muse Spark (veto only).
- Street speed study with gate method, per-vehicle ranges, no-reading reasons, 85th percentile.
- QuantiPhy validation evaluation (dev, holdout, full) against Muse Spark alone, a rule-parser ablation, and audit off.
- Field set of 30 clips with instrument truth plus 5 no-reference clips; set A also validates the speed study.
- Web app: `/`, `/workspace`, `/study`, `/results`; live runs with caps plus cached runs.

Stretch (only after Phase 5 is green)
- Muse Spark Open backend on Baseten.
- `measure()` and `study()` as MCP tools.

Out of scope
- Counting, frequency, medical or legal measurement, law enforcement use, face or identity recognition, real-time streaming, image generation (Muse Image is unavailable in India), sports analysis.

## Success criteria

Defined in docs/EVAL_PROTOCOL.md (H1 to H5, A1, A2). Targets, not results.

## Risks

| Risk | Mitigation |
| --- | --- |
| SAM 3.1 tracks the wrong instance | Instance selection rule, frame-0 box prompt, visual audit; Phase 0 gate |
| Overfitting to 158 validation questions | Dev and holdout split by video; field set never used for tuning |
| 3D questions and noisy acceleration | Parametric local fits; report per category honestly |
| Speed study errors from perspective or occlusion | Gate method on the road plane, per-vehicle refusals, validated on set A |
| API outage or rate limits during judging | Cached runs; open-weights SAM on Modal |
| Credit burn from live runs | Disk cache, per-IP and daily caps, Billing spend notification |
| "New work only" doubt | No code before Oct 27 ET; README lists what existed before |

## Timeline

See the phase table in AGENTS.md section 7.
