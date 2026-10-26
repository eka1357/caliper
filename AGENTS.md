# AGENTS.md: Caliper

Read this whole file before any task. It is the single source of truth for every coding agent on this repo (Claude Code, Cursor, Antigravity, Codex, Gemini CLI). Tool-specific files (CLAUDE.md, GEMINI.md, .cursor/rules) only point here. The official hackathon rules are in `docs/OFFICIAL_RULES.md`; if anything here conflicts with them, the rules win.

## 1. What we are building

Caliper gives AI a ruler. Input: a short video and a question such as "how fast is the white car in m/s?". Output: a measured number with a 90% interval, or an abstention that says exactly what is missing.

Thesis: vision-language models guess physical quantities from memory. On Stanford's QuantiPhy benchmark the best listed model scores below the human baseline. Caliper uses each tool for what it is good at:

- Muse Spark 1.3 understands: it reads the question and the scene, writes a measurement spec, and afterwards audits the evidence (right object? right reference? same plane?).
- SAM 3.1 finds and tracks the pixels of the target and the scale reference.
- Deterministic Python computes every number and its uncertainty.
- Checks and the audit refuse to answer when the video cannot support a number.

MVP quantities: size, speed, acceleration.

Real-world showcase: a **street speed study**. A resident or road engineer films a street for a few minutes with two marks a measured distance apart. Caliper measures every vehicle it can, gives each one an error range, refuses the ones it cannot measure, and reports the median and 85th-percentile speed (the number traffic engineers use to justify traffic calming). Same engine, validated against GPS in field set A.

Event: Meta Global AI Developer Hackathon, Indie track. Building period Oct 27 to Nov 4 2026 (ET). Submission due Nov 4 2026, 9:00 PM ET (7:30 AM IST Nov 5). Judged in Stage Two on four equal criteria: Impact, Use of Meta AI Tooling, Technical Depth and Execution, Demo (3-minute video plus the live product).

## 2. Non-negotiable rules

1. The LLM never produces a final number. Every number comes from `backend/caliper/engine.py` or `backend/caliper/study.py`.
2. Per question: at most two Muse Spark calls (spec, then visual audit) and one SAM 3.1 call per concept. The audit can only veto (turn a result into an abstention with its reason); it never edits a number.
3. If any check or the audit fails, abstain with a reason. Never guess.
4. Every result shown anywhere (README, UI, demo video, X post) is generated from `eval/results.csv`, `eval/field_results.csv`, or a cached run JSON. Never type a result by hand.
5. Cache every API response on disk under `data/cache/`. Reruns must cost $0.
6. Secrets live only in `.env` (gitignored). Never print, log, commit, or paste keys into another tool. The repo becomes public: check history for secrets before it does.
7. Tune thresholds only on the QuantiPhy dev split. Report holdout and full separately (see `docs/EVAL_PROTOCOL.md`).
8. QuantiPhy videos keep their original licenses and are for research and evaluation. Never commit them, never show them in the hosted demo or the demo video. Demo footage is our own.
9. New work only: all application code is written from the start of the building period (Oct 27 00:00 ET). The README lists exactly what existed before (planning docs, config, our field clips) and what was built during the event.
10. Stay inside the current phase. Each phase ends at a gate: stop, report, wait for the human.
11. Do not add a dependency that is not listed in `docs/SETUP.md` or `docs/TOOLS.md` without asking. Only use code, components, fonts and data we have the rights to; record each license in the README credits.
12. Muse Image is not available in India. Never use it.
13. Stay clear of the official anti-projects: no medical advice, no sports analysis or coaching framing, no education-chatbot framing, nothing political or involving war. The speed study is road-safety evidence for residents and engineers, not law enforcement.
14. The hosted demo always offers cached example runs. Live runs are enabled for judging with hard caps (`.env`): per-IP rate limit, clip length limits, a cost cap per measure run and per study (checked on a cost estimate before any API call), and a daily spend cap. When a cap is hit, the UI says so and offers the cached runs.

## 3. API facts (checked Oct 2026; re-check https://dev.meta.ai/docs if a call fails)

Meta Model API
- Base URL `https://api.meta.ai/v1`. Header `Authorization: Bearer $MODEL_API_KEY`.
- Compatible with the OpenAI SDK and the Anthropic SDK. The OpenAI SDK does not read `MODEL_API_KEY` on its own: pass `api_key=os.environ["MODEL_API_KEY"]` and `base_url` explicitly.
- Files: `POST /v1/files` with `purpose="user_data"`, then reference by `file_id`.
- A credit card must be on the account for calls to work, even with free credits.

Muse Spark 1.3 (`muse-spark-1.3`)
- Input: text, image, video, PDF. Output: text. Tool calling, structured output, 1M-token context.
- Audio on 1.3 is not fully reliable. We do not use audio.
- Video: Responses API with an `input_file` (file_id) or `input_video` block. Set `max_output_tokens` to at least 4000 because reasoning shares the output budget.
- Price: $1.25 per M input tokens, $4.25 per M output tokens.

SAM 3.1 (`sam-3.1`)
- `POST /v1/responses`, `model="sam-3.1"`, `stream=true`.
- `input` is one user message with two parts: `input_text` and `input_video` (`file_id` or `video_url`).
- `input_text` is EITHER a short noun phrase for one concept ("white car") OR the box/point prompt grammar. Never both. One concept per request.
- Up to 16 tracked objects per frame. Up to 15,000 frames (about 10 minutes) per request.
- Containers MP4 or MOV; codecs H.264, H.265, MPEG-4. No VP9 or WebM. Export with faststart.
- Metadata: `include_confidence` must be the string "true" or "false"; `mask_encoding` "lossless" (default) or "one_bit"; `propagation_direction` for box/point prompts.
- Response: streamed lines, one per frame. Each line: frame marker `<Nf>`, object ordinal, box (x1, y1, x2, y2 inclusive, plus w, h; `c` when confidence is on), mask record.
- Concept prompts return frames in ascending order. Box/point prompts may not, so always read the frame marker.
- Parse with the Python package `meta-sam-parser` (`decode_mask_to_raster`, `decode_mask_to_rle`, `decode_mask_to_svg_path`, `build_object_prompt`).
- Price: $0.20 per 1,000 video frames.
- Errors: 400 means a bad prompt or metadata (fix input, do not retry). 404 `model_not_found` means no access.
- Fallback: open weights `facebook/sam3.1` (gated on Hugging Face) on a Modal GPU.

Muse Spark Open (open weights, stretch backend)
- Served through Baseten for the hackathon as `meta-models/muse-spark-open-1026` (the docs' `meta-models/muse-spark-open` is the wrong ID for this event).
- OpenAI-compatible chat completions; accepts images and audio. Send sampled keyframes as images instead of video.
- Confirm the base URL and auth in Baseten's quickstart before coding. Using it for the spec and audit makes Caliper eligible for the "Best Build on Meta Open Weight Models" bonus prize.

## 4. Architecture (full detail in docs/ARCHITECTURE.md)

```
video + question (+ optional prior)
  -> normalize   ffmpeg to H.264 MP4, faststart, no audio, original fps
  -> spec        Muse Spark 1.3 writes MeasurementSpec (JSON, validated by pydantic)
  -> segment     SAM 3.1 tracks target, then reference (2 requests)
  -> engine      scale, position over time, local fits, bootstrap interval
  -> checks      presence, continuity, stability, agreement, physical bounds
  -> audit       Muse Spark looks at overlay keyframes; may veto, never edits numbers
  -> Result      measured (value + 90% interval) | abstained (reason)

street video + gate distance
  -> segment     SAM 3.1 per vehicle class (car, motorcycle, auto rickshaw, bus)
  -> study       gate crossing times per vehicle -> speed + interval, or no reading
  -> report      count, median, 85th percentile with interval, share over the limit
```

## 5. Repo map

```
AGENTS.md            this file (source of truth)
CLAUDE.md            Claude Code pointer + Claude-only notes
GEMINI.md            Gemini CLI / older Antigravity pointer
PROMPTS.md           copy-paste prompt for each phase
README.md            public project page (results generated, never typed)
Makefile             all commands
.env.example         every env var with comments
.mcp.json            MCP servers for Claude Code (21st.dev Magic)
.claude/             Claude Code settings and slash commands
.cursor/rules/       Cursor pointer
docs/                OFFICIAL_RULES, PRD, ARCHITECTURE, EVAL_PROTOCOL, DESIGN, TOOLS,
                     DEMO_SCRIPT, DATA_COLLECTION, RULES_CHECKLIST, SETUP, DECISIONS
backend/             Python package `caliper` (FastAPI + pipeline)
  caliper/config.py      every threshold, limit and known-object size, each with its source
  caliper/meta_client.py OpenAI SDK client for Meta Model API, Files API upload, disk cache
  caliper/backends.py    language-model backends: Meta API (default), Muse Spark Open on Baseten
  caliper/normalize.py   ffmpeg: H.264 MP4, faststart, no audio, original fps
  caliper/spec.py        question + video -> MeasurementSpec
  caliper/segment.py     SAM 3.1 client, parser, cache, open-weights fallback
  caliper/engine.py      pure math: scale, kinematics, intervals (no I/O)
  caliper/checks.py      checks and abstention reasons (pure)
  caliper/audit.py       Muse Spark visual audit of overlay keyframes (veto only)
  caliper/study.py       street speed study: gate method, per-vehicle intervals, summary
  caliper/pipeline.py    measure(video, question, prior=None) -> Result
  caliper/api.py         FastAPI app with live-run caps and replay mode
  caliper/mcp_server.py  STRETCH: measure() as an MCP tool
  tests/
eval/
  baseline.py          Muse Spark alone on QuantiPhy (official zero-shot prompt)
  quantiphy.py         Caliper on QuantiPhy, writes predictions CSV
  ablation.py          rule-based parser instead of Muse Spark; audit on/off
  field.py             field clips vs data/field/truth.csv
  report.py            builds results.csv, results.json, README table
  quantiphy/           clone of github.com/Paulineli/QuantiPhy (gitignored)
data/
  field/               our clips + truth.csv (clips gitignored; compressed demo copies in web/public)
  quantiphy-val/       validation set download (gitignored)
  cache/               API response cache (gitignored)
web/                   Next.js 16 app (created in the building period, see docs/SETUP.md)
```

Our code under `backend/caliper/`, `eval/` and `web/` is written during the building period, not before. The QuantiPhy clone and downloads are third-party data, set up in advance.

## 6. Commands (Makefile)

```
make setup        install backend (editable) and web dependencies
make dev-api      run FastAPI on :8000
make dev-web      run Next.js on :3000
make test         pytest + web typecheck
make lint         ruff + eslint
make baseline     Muse Spark alone on QuantiPhy validation
make eval         Caliper on QuantiPhy validation (dev, holdout, full)
make field        Caliper on data/field
make ablation     rule-parser and audit-off variants on QuantiPhy validation
make study CLIP=data/field/S01.mp4 GATE_M=10.0   street speed study on one clip
make report       regenerate eval/results.csv, web/public/results.json, README table
```

## 7. Phases and gates (prompts in PROMPTS.md; dates are IST)

| Phase | Day | Deliverable | Gate (stop and report) |
| --- | --- | --- | --- |
| 0 | Oct 27 (after 9:30 AM IST) | API access, Muse Spark baseline on 158 questions, SAM 3.1 on 20 clips | Baseline MRA; tracking table. If SAM tracks the wrong object on more than 10 of 20 clips, stop |
| 1 | Oct 28 | Engine for 2D questions, synthetic-clip tests | 2D categories scored on dev split |
| 2 | Oct 29 | Spec writer + rule-parser ablation | Both variants scored |
| 3 | Oct 30 | Checks, visual audit, abstention, 3D questions | All four categories scored; audit on/off compared |
| 4 | Oct 31 | Field set run + street speed study validated on set A | Field metrics; per-vehicle speed error vs GPS |
| 5 | Nov 1 to 2 | API with capped live mode; workspace, study view, results, landing | Demo flow works live and on cached runs |
| 6 | Nov 2 evening | Stretch: Muse Spark Open backend, then MCP tool | Only if Phases 0 to 5 are green |
| 7 | Nov 3 to 4 | Freeze, README, 3-minute video, X post, submission by Nov 4 11:59 PM IST | Checklist in docs/RULES_CHECKLIST.md complete |

## 8. Code conventions

Python
- Python 3.11+. Type hints everywhere. pydantic v2 models at every boundary (spec, tracks, audit, result, study).
- `engine.py`, `checks.py` and the math in `study.py` are pure functions: no network, no file I/O, fully unit-tested.
- Network and disk I/O only in `meta_client.py`, `backends.py`, `spec.py`, `segment.py`, `audit.py`, `pipeline.py`, `api.py`.
- `logging`, never `print`, in library code. ruff for lint and format. pytest for tests.
- Every threshold lives in one `config.py` with a comment saying where its value came from.

TypeScript (web/)
- Strict mode, no `any`. Next.js App Router. Server components by default; `"use client"` only for interactive or animated components.
- All backend calls go through `web/src/lib/api.ts`. Types mirror the pydantic models in `docs/ARCHITECTURE.md`.
- Imported components (shadcn registries, 21st.dev, React Bits, Skiper UI, Watermelon UI, bklit) must be the TypeScript + Tailwind variants, restyled to the tokens in `docs/DESIGN.md`, with their license noted.

## 9. Frontend rules (full detail in docs/DESIGN.md and docs/TOOLS.md)

- Four routes: `/` landing (the story), `/workspace` (the tool), `/study` (street speed study), `/results` (the evidence).
- shadcn/ui is the base. bklit for every chart. Motion (`motion/react`) for component animation on every route.
- GSAP (ScrollTrigger, SplitText, DrawSVG) and Lenis only on `/`. Lenis is driven by `gsap.ticker` (one animation clock), with `data-lenis-prevent` on any inner scroll area.
- At most 3 decorative effects on `/`, zero on `/workspace`, `/study` and `/results`.
- Barba.js is not used (it is built for multi-page sites; Next.js already routes on the client).
- `prefers-reduced-motion: reduce` disables Lenis, scroll scenes and text effects; content stays fully readable.
- `/workspace`, `/study` and `/results` must not import GSAP, Lenis, or decorative components.

## 10. Definition of done (every task)

1. `make test` and `make lint` pass.
2. If the engine, checks or audit changed, `make eval` was rerun and the before/after numbers are in the report.
3. One commit per concern, message starting with the phase: `phase 1: local quadratic fit for speed`.
4. A short report to the human: what changed, numbers before and after, open risks.

## 11. Ask the human when

- A phase gate is reached.
- An API behaves differently from section 3.
- A change would alter the scope, the thesis, or the metrics.
- Spend would exceed $2 in a day.
- Anything might break a rule in docs/OFFICIAL_RULES.md.
