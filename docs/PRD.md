# Product requirements: Caliper

## Problem

People and AI agents ask numeric questions about video ("how fast was that car?", "how tall is that shelf?") and act on the answers. Vision-language models answer with confident guesses. On Stanford's QuantiPhy benchmark, which asks for size, speed and acceleration from short videos, the best model on the public leaderboard scores below the human baseline, and the authors found models still answer plausibly with no video at all ([Stanford HAI](https://hai.stanford.edu/news/ai-cant-do-physics-well-and-thats-a-roadblock-to-autonomy), [leaderboard](https://quantiphy.stanford.edu/)). Measurement tools such as Tracker are accurate but need a person to calibrate, click and choose the method for every clip.

## Solution

Caliper takes a free-form question and a video, decides what to measure against, tracks the pixels, computes the number with deterministic code, attaches a 90% interval, and refuses when the video cannot support an answer.

## Users

| User | Job | Demo moment |
| --- | --- | --- |
| Agent builders | Give an agent a reliable physical measurement instead of a guess | Another agent calls `measure()` and uses the result (stretch) |
| Everyday asker | Check a speed or size from a phone clip | A parent checks how fast cars pass a school |
| Judges | Decide if it works | Same clip: Muse Spark guesses, Caliper measures, the instrument agrees |

## Scope

Must have (MVP)
- Quantities: size, speed (instantaneous and average), acceleration.
- Scale from a given prior, a known-size object, or a printed marker card.
- 90% interval for every measured value; abstention with a reason and a fix.
- QuantiPhy validation evaluation (dev, holdout, full) against Muse Spark alone and a rule-parser ablation.
- Field set of 30 clips with instrument truth plus 5 no-reference clips.
- Web app: `/` landing, `/workspace` tool, `/results` evidence; hosted demo in replay mode.

Stretch (only after Phase 5 is green)
- `measure()` as an MCP tool.
- Frequency (rotation or oscillation rate) from mask signals.
- Live recording on mobile with upload.

Out of scope
- Counting, medical or legal measurements, face or identity recognition, real-time streaming, image generation (Muse Image is unavailable in India).

## Success criteria

Defined in docs/EVAL_PROTOCOL.md (H1 to H4, A1). Targets, not results.

## Risks

| Risk | Mitigation |
| --- | --- |
| SAM 3.1 tracks the wrong instance | Instance selection rule, then a frame-0 box prompt; Phase 0 gate |
| Overfitting to 158 validation questions | Dev and holdout split; field set never used for tuning |
| 3D questions and noisy acceleration | Parametric local fits; report per category honestly |
| API outage or rate limits during the demo | Replay mode with cached runs; open-weights SAM on Modal |
| Credit burn | Disk cache, spend caps in `.env`, cost logged per run |
| Rules disallow pre-built code | Only docs and config exist before Oct 26; disclose in README |

## Timeline

See the phase table in AGENTS.md section 7.
