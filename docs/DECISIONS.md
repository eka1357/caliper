# Decision log

Newest first. Add a row whenever a decision changes scope, architecture, metrics, tools, or thresholds.

| Date | Decision | Why | Revisit if |
| --- | --- | --- | --- |
| 2026-10-21 | Dark theme only | One polished theme beats two rushed ones; instrument aesthetic | Rules or judges require light mode |
| 2026-10-21 | Barba.js not used | Designed for multi-page sites; conflicts with Next.js client routing | Never for this project |
| 2026-10-21 | GSAP and Lenis on `/` only; Lenis driven by `gsap.ticker` | One animation clock; keeps `/workspace` fast | Landing performance fails QA |
| 2026-10-21 | Next.js + FastAPI instead of Streamlit | Design quality matters for the demo; reuse Gauntlet's replay-mode pattern | Time runs short on Day 7: fall back to Streamlit for the workspace |
| 2026-10-21 | Hosted demo in replay mode, `LIVE_RUNS_ENABLED=false` by default | Protects credits; demo never depends on live API | Rules require live judging access |
| 2026-10-21 | SAM 3.1: one request per concept (target, reference) | Meta docs: one concept per request, 16 objects per frame | API adds multi-concept prompts |
| 2026-10-21 | Dev and holdout split on QuantiPhy validation | 158 questions is small; avoid tuning on what we report | Never |
| 2026-10-21 | Muse Image not used | Not available in India per Meta's geographic policy | Policy changes |
| 2026-10-19 | Narrow scope to size, speed, acceleration | QuantiPhy tests exactly these; five quantity types was too broad | Phases 0 to 5 finish early |
| 2026-10-19 | One model call plus deterministic math; no multi-agent layer | Agents added no capability; the rule-parser ablation is the honest control | Ablation shows a specific gap a second call fixes |

## Measured facts to record (fill during Phase 0)

| Fact | Value | How measured |
| --- | --- | --- |
| Muse Spark tokens per QuantiPhy question with video | | |
| SAM 3.1 latency per 90-frame clip | | |
| Cost of one full validation run | | |
| SAM wrong-object rate on 20 clips | | |
