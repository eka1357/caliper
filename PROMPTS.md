# Prompts for your coding agent

Paste one prompt per phase. Each one ends at a gate: the agent stops and reports. Paste the next prompt only after you accept the gate report. In Claude Code, `/phase N` loads the matching section. Start no code before Oct 27 00:00 ET (9:30 AM IST).

---

## Phase 0: kickoff and go/no-go (Oct 27)

```
Read AGENTS.md fully, then docs/OFFICIAL_RULES.md, docs/ARCHITECTURE.md and docs/EVAL_PROTOCOL.md. Confirm in 5 lines what Caliper is, the non-negotiable rules, and anything in the official rules that affects this phase. Then do Phase 0 only.

1. Scaffold backend/ as described in AGENTS.md section 5 with empty modules, config.py, and a pytest that passes. Install with pip install -e ".[dev]".
2. Write backend/caliper/meta_client.py: an OpenAI SDK client with base_url https://api.meta.ai/v1 and api_key from MODEL_API_KEY, a Files API upload helper (purpose "user_data"), and a disk cache keyed by sha256 of the request.
3. Write a smoke test script that makes one muse-spark-1.3 text call and one sam-3.1 concept call on one 2D video from data/quantiphy-val/validation_videos (stream=true, include_confidence "true"), parses the stream with meta-sam-parser, and prints frames returned and objects per frame.
4. Write eval/split.csv (dev/holdout by hash of video_id, see EVAL_PROTOCOL section 2).
5. Baseline: patch eval/quantiphy/model_run_example/run_API_results.py to use the Meta endpoint and muse-spark-1.3 with the zero-shot "original" prompt unchanged. Save the diff to eval/baseline_patch.diff. Run all 158 questions, make sure the output CSV starts with the row ID column (EVAL_PROTOCOL section 4 step 7), score it, and write rows "muse_spark_alone" for dev, holdout and full into eval/results.csv.
6. Run SAM 3.1 on 20 of the 24 validation videos (10 dev, 10 holdout) using the target phrase from each question. Save an overlay MP4 per clip into eval/phase0_overlays/ and a table eval/phase0_tracking.csv: video_id, phrase, frames, objects_max, mean_confidence, my_verdict (leave empty for me).
7. Record token counts, latency and cost in docs/DECISIONS.md "Measured facts".

GATE: stop. Report the baseline MRA per split and category, total cost so far, and where the overlays are. I will fill my_verdict in the tracking table. Do not start Phase 1.
```

## Phase 1: engine for 2D questions (Oct 28)

```
Phase 1 only. Follow docs/ARCHITECTURE.md sections 5 and 6.

1. segment.py: concept requests for target and reference, instance selection rule, cache, Track model.
2. engine.py (pure): scale from size prior and from speed prior, centroid and leading-edge positions, local quadratic fit for instantaneous speed and acceleration, average speed from path length, size from mask extent, bootstrap 90% interval (B=500).
3. Tests: render synthetic clips with numpy/opencv (a disc moving at a known speed and acceleration, a bar of known length next to a reference square) and assert the engine recovers them within 2%.
4. eval/quantiphy.py: run Caliper on the 2D categories (S2, D2) of the dev split with a temporary hand-written spec from the question's prior field, write the predictions CSV, score, and add rows "caliper" (2D only, dev) to eval/results.csv.
5. Run the three pilot clips in data/field/pilot/ through the engine with hand-written specs and report anything phone-specific that breaks (stabilization, rolling shutter, 60 fps). Do not tune on them.

GATE: report 2D MRA on dev next to muse_spark_alone, the 5 worst questions with why they failed, pilot-clip findings, and cost. Stop.
```

## Phase 2: spec writer and ablation (Oct 29)

```
Phase 2 only.

1. backends.py: one interface for language-model calls; implement the Meta API backend now (muse-spark-1.3, video via Files API). Leave a stub for Muse Spark Open.
2. spec.py: Muse Spark call 1 with the uploaded video and the question, output MeasurementSpec JSON. Use structured output if the Meta docs confirm the parameter; otherwise schema in prompt + pydantic validation + one retry. Known objects only from config.KNOWN_OBJECTS. The model must never return the answer.
3. Wire spec.py into pipeline.py and rerun eval on all 2D questions, dev split.
4. ablation.py: a rule-based parser that builds the same MeasurementSpec from the question text and prior with regex. Score it as "caliper_rule_parser".

GATE: report caliper vs caliper_rule_parser vs muse_spark_alone on dev (2D), plus 3 examples where the model's spec beat the rules and 3 where it lost. Stop.
```

## Phase 3: checks, audit, abstention, 3D (Oct 30)

```
Phase 3 only.

1. Inspect the depth_info field on 5 QuantiPhy 3D rows and describe its format before writing any code. Then implement the pinhole handling the data supports.
2. checks.py with the checks and messages in docs/ARCHITECTURE.md section 7; thresholds in config.py. Abstain with the reason when any check fails.
3. audit.py exactly as docs/ARCHITECTURE.md section 8: render 3 to 4 overlay keyframes (no numbers on them), Muse Spark call 2 returns AuditVerdict, veto only. Add a config switch to turn it off.
4. Run all four categories on dev with the audit on and off. Tune thresholds, windows and the audit prompt on dev only. Then run holdout and full once and write rows caliper and caliper_no_audit to eval/results.csv with abstain_rate.
5. Compare audit vetoes with my verdicts in eval/phase0_tracking.csv: wrong-object tracks caught, correct results vetoed.

GATE: report MRA per category and split for both rows, abstention rate, the audit's catches and false vetoes, and the threshold values you chose with why. Stop.
```

## Phase 4: field set and street speed study (Oct 31)

```
Phase 4 only. Do not change any threshold in this phase.

1. eval/field.py: run Caliper on every clip in data/field/truth.csv; write eval/field_results.csv as defined in docs/EVAL_PROTOCOL.md section 5.
2. study.py exactly as docs/ARCHITECTURE.md section 9 (gate method, per-vehicle intervals, no-reading reasons, summary with 85th percentile). Pure math with unit tests on synthetic tracks with known crossing times.
3. Run set A clips through the study path too (gate = the two markers, distance from truth.csv) and report H5 against the GPS speeds.
4. Run make study on the set S street clip(s) and save the StudySummary.
5. Report H2, H3, H4, H5 as pass or fail with the numbers. Set D clips must all abstain.
6. Cache every run JSON into web/public/runs/ for replay (only our own clips, compressed with ffmpeg to under 3 MB each; blur or crop any readable number plate or face first).

GATE: report the claims table with numbers. Engine, study and audit parameters are now frozen. Stop.
```

## Phase 5a: API and workspace (Nov 1)

```
Phase 5a. Read docs/DESIGN.md and docs/TOOLS.md fully first.

1. backend api.py: endpoints in docs/ARCHITECTURE.md section 10 with the live-run caps from .env (per-IP rate limit, max clip and study length, per-run and per-study cost caps checked on a cost estimate before any API call, daily spend cap) and cached runs that never count against caps.
2. web/: apply the tokens from docs/DESIGN.md section 2 in globals.css (dark only), fonts Instrument Serif, Geist, Geist Mono via next/font/google. web/src/lib/types.ts mirrors the pydantic models; web/src/lib/api.ts is the only place that calls the backend.
3. /workspace exactly as docs/DESIGN.md section 6, including the audit panel in "Show the chain". Motion only. No GSAP, no Lenis, no decorative components on this route.

GATE: screen-record the workspace on 3 runs (one measured, one abstained by a check, one vetoed by the audit) plus one live run, and list any design QA items from docs/DESIGN.md section 8 that fail. Stop.
```

## Phase 5b: study view, results page and landing (Nov 2)

```
Phase 5b. Read docs/DESIGN.md sections 5 to 8 again.

1. /study as specified: gate drawing on the first frame, distance input, live or cached run, per-vehicle labels on the video, summary card with the 85th percentile and its range, histogram (bklit), and a printable report page.
2. /results from web/public/results.json and field_results: table plus bklit charts as specified. Nothing typed by hand.
3. / landing, sections as specified. Lenis via lenis/react with root and autoRaf false, driven by gsap.ticker together with ScrollTrigger (pattern in docs/TOOLS.md). Exactly three decorative effects. Full reduced-motion fallback.
4. Run the design QA checklist (docs/DESIGN.md section 8), including the build output check that /workspace, /study and /results ship no gsap or lenis code.

GATE: report Lighthouse mobile scores for /, the QA checklist with pass/fail, and screenshots at 1440 and 390 px. Stop.
```

## Phase 6: stretch (Nov 2 evening, only if everything above is green)

```
Phase 6. In this order, stopping after each:
1. Muse Spark Open backend in backends.py: Baseten, model meta-models/muse-spark-open-1026, keyframes as images for spec and audit (confirm base URL and auth in Baseten's quickstart). Run the dev split as caliper_open and report it next to caliper. Add a backend switch in the workspace.
2. backend/caliper/mcp_server.py exposing measure(video_path, question, prior=None) and study(video_path, gates, distance_m) with the pydantic schemas, plus a README snippet showing another agent calling it.
GATE after each item.
```

## Phase 7: freeze and ship (Nov 3 to 4)

```
Phase 7. No new features.
1. make report regenerates eval/results.csv, web/public/results.json and the README results table.
2. README: problem and who it helps, how it works (diagram), results table, the speed study, how to reproduce in one command, limitations stated honestly, a section "Built during the hackathon (Oct 27 to Nov 4)" versus "Existed before" (planning docs, config, field clips), credits and licenses for every model, dataset, font and component.
3. Make the repo public after checking git history for secrets. Deploy web to Vercel and the backend with live-run caps on. Test live and cached runs from a private window.
4. Walk docs/RULES_CHECKLIST.md pre-submission list and report each item.
GATE: give me the deployed URL, the repo URL, and the checklist. Stop.
```

---

## Utility prompts

Fix one failure class
```
Look at the 10 worst rows in the latest eval on the dev split only. Group them by cause. Fix the single largest cause, rerun dev, and report before and after. Do not touch holdout or the field set.
```

Gate report template
```
Write the gate report: phase, what was built (files), commands run, numbers before and after (with the file each number came from), cost so far, failing items, risks for the next phase. No adjectives.
```
