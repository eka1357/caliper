# Decision log

Newest first. Add a row whenever a decision changes scope, architecture, metrics, tools, or thresholds.

| Date | Decision | Why | Revisit if |
| --- | --- | --- | --- |
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
| Muse Spark tokens per QuantiPhy question with video | | |
| SAM 3.1 latency per 90-frame clip | | |
| Cost of one full validation run | | |
| SAM wrong-object rate on 20 clips | | |
