# AGENTS.md: Caliper

Read this whole file before any task. It is the single source of truth for every coding agent on this repo (Claude Code, Cursor, Antigravity, Codex, Gemini CLI). Tool-specific files (CLAUDE.md, GEMINI.md, .cursor/rules) only point here.

## 1. What we are building

Caliper gives AI agents a ruler. Input: a short video and a question such as "how fast is the black car in m/s?". Output: a measured number with a 90% interval, or an abstention that says exactly what is missing.

Thesis: vision-language models guess physical quantities from memory. On Stanford's QuantiPhy benchmark the best listed model scores below the human baseline. Caliper measures instead of guessing by splitting the work:

- Muse Spark 1.3 reads the question and the scene and writes a measurement spec.
- SAM 3.1 finds and tracks the pixels of the target and the scale reference.
- Deterministic Python computes every number and its uncertainty.
- Checks refuse to answer when the video cannot support a number.

MVP quantities: size, speed, acceleration. Counting and frequency are stretch goals.

Event: Meta Global AI Developer Hackathon, Indie track, theme "Push the Frontier". Build window Oct 26 to Nov 4 2026, submission due Nov 4 2026, 9:00 PM ET. Judged on creativity, technical ambition, and whether it works.

## 2. Non-negotiable rules

1. The LLM never produces a final number. Every number comes from `backend/caliper/engine.py`.
2. Per question: one Muse Spark call to write the spec, and one SAM 3.1 call per concept (target, reference). No multi-agent layers.
3. If any check fails, abstain with a reason. Never guess.
4. Every result shown anywhere (README, UI, demo video) is generated from `eval/results.csv` or a cached run JSON. Never type a result by hand.
5. Cache every API response on disk under `data/cache/`. Reruns must cost $0.
6. Secrets live only in `.env` (gitignored). Never print, log, commit, or paste keys into another tool.
7. Tune thresholds only on the QuantiPhy dev split. Report holdout and full separately (see `docs/EVAL_PROTOCOL.md`).
8. QuantiPhy videos keep their original licenses and are for research and evaluation. Never commit them, never serve them from the hosted demo. Demo clips are our own field clips.
9. Stay inside the current phase. Each phase ends at a gate: stop, report, wait for the human.
10. Do not add a dependency that is not listed in `docs/SETUP.md` or `docs/TOOLS.md` without asking.
11. Muse Image is not available in India. Never use it.
12. Live API calls from the hosted demo are off by default (`LIVE_RUNS_ENABLED=false`). The hosted demo replays cached runs.

## 3. API facts (checked Oct 2026; re-check https://dev.meta.ai/docs if a call fails)

Meta Model API
- Base URL `https://api.meta.ai/v1`. Header `Authorization: Bearer $MODEL_API_KEY`.
- Compatible with the OpenAI SDK and the Anthropic SDK. The OpenAI SDK does not read `MODEL_API_KEY` on its own: pass `api_key=os.environ["MODEL_API_KEY"]` and `base_url` explicitly.
- Files: `POST /v1/files` with `purpose="user_data"`, then reference by `file_id`.

Muse Spark 1.3 (`muse-spark-1.3`)
- Input: text, image, video, PDF. Output: text. Tool calling, structured output, 1M-token context.
- Audio on 1.3 is not fully reliable. We do not use audio.
- Video: Responses API with an `input_file` (file_id) or `input_video` block. Set `max_output_tokens` to at least 4000 because reasoning shares the output budget.
- Price: $1.25 per M input tokens, $4.25 per M output tokens.

SAM 3.1 (`sam-3.1`)
- `POST /v1/responses`, `model="sam-3.1"`, `stream=true`.
- `input` is one user message with two parts: `input_text` and `input_video` (`file_id` or `video_url`).
- `input_text` is EITHER a short noun phrase for one concept ("black car") OR the box/point prompt grammar. Never both. One concept per request.
- Up to 16 tracked objects per frame. Up to 15,000 frames (about 10 minutes) per request.
- Containers MP4 or MOV; codecs H.264, H.265, MPEG-4. No VP9 or WebM. Export with faststart.
- Metadata: `include_confidence` must be the string "true" or "false"; `mask_encoding` "lossless" (default) or "one_bit"; `propagation_direction` for box/point prompts.
- Response: streamed lines, one per frame. Each line: frame marker `<Nf>`, object ordinal, box (x1, y1, x2, y2 inclusive, plus w, h; `c` when confidence is on), mask record.
- Concept prompts return frames in ascending order. Box/point prompts may not, so always read the frame marker.
- Parse with the Python package `meta-sam-parser` (`decode_mask_to_raster`, `decode_mask_to_rle`, `decode_mask_to_svg_path`, `build_object_prompt`).
- Price: $0.20 per 1,000 video frames.
- Errors: 400 means a bad prompt or metadata (fix input, do not retry). 404 `model_not_found` means no access.
- Fallback: open weights `facebook/sam3.1` (gated on Hugging Face) on a Modal GPU.

## 4. Architecture (full detail in docs/ARCHITECTURE.md)

```
video + question (+ optional prior)
  -> normalize   ffmpeg to H.264 MP4, faststart, no audio, original fps
  -> spec        Muse Spark 1.3 writes MeasurementSpec (JSON, validated by pydantic)
  -> segment     SAM 3.1 tracks target, then reference (2 requests)
  -> engine      scale, position over time, local fits, bootstrap interval
  -> checks      presence, continuity, stability, agreement, physical bounds
  -> Result      measured (value + 90% interval) | abstained (reason)
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
docs/                PRD, ARCHITECTURE, EVAL_PROTOCOL, DESIGN, TOOLS, DEMO_SCRIPT,
                     DATA_COLLECTION, RULES_CHECKLIST, SETUP, DECISIONS
backend/             Python package `caliper` (FastAPI + pipeline)
  caliper/config.py      every threshold, limit and known-object size, each with its source
  caliper/meta_client.py OpenAI SDK client for Meta Model API, Files API upload, disk cache
  caliper/normalize.py   ffmpeg: H.264 MP4, faststart, no audio, original fps
  caliper/spec.py        question + video -> MeasurementSpec
  caliper/segment.py     SAM 3.1 client, parser, cache, open-weights fallback
  caliper/engine.py      pure math: scale, kinematics, intervals (no I/O)
  caliper/checks.py      checks and abstention reasons
  caliper/pipeline.py    measure(video, question, prior=None) -> Result
  caliper/api.py         FastAPI app
  caliper/mcp_server.py  STRETCH: measure() as an MCP tool
  tests/
eval/
  baseline.py          Muse Spark alone on QuantiPhy (official zero-shot prompt)
  quantiphy.py         Caliper on QuantiPhy, writes predictions CSV
  ablation.py          rule-based parser instead of Muse Spark
  field.py             field clips vs data/field/truth.csv
  report.py            builds results.csv, results.json, README table
  quantiphy/           clone of github.com/Paulineli/QuantiPhy (gitignored)
data/
  field/               our clips + truth.csv
  quantiphy-val/       validation set download (gitignored)
  cache/               API response cache (gitignored)
web/                   Next.js 16 app (created at kickoff, see docs/SETUP.md)
```

Our code under `backend/caliper/`, `eval/` and `web/` is written during the build window, not before. The QuantiPhy clone and downloads are third-party data, set up in advance.

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
make ablation     rule-parser variant on QuantiPhy validation
make report       regenerate eval/results.csv, web/public/results.json, README table
```

## 7. Phases and gates (prompts in PROMPTS.md)

| Phase | Day | Deliverable | Gate (stop and report) |
| --- | --- | --- | --- |
| 0 | Oct 26 | API access, Muse Spark baseline on 158 questions, SAM 3.1 on 20 clips | Baseline MRA; tracking table. If SAM tracks the wrong object on more than 10 of 20 clips, stop |
| 1 | Oct 27 to 28 | Engine for 2D questions, synthetic-clip tests | 2D categories scored on dev split |
| 2 | Oct 29 | Spec writer + rule-parser ablation | Both variants scored |
| 3 | Oct 30 | Checks, abstention, 3D questions | All four categories scored, abstention rate reported |
| 4 | Oct 31 | Field set run | Median relative error and interval coverage |
| 5 | Nov 1 | Web app: workspace, results page, landing | Demo flow works end to end on cached runs |
| 6 | Nov 2 | Stretch: MCP tool, then frequency module | Only if Phases 0 to 5 are green |
| 7 | Nov 3 to 4 | Freeze, README, demo video, submission | Checklist in docs/RULES_CHECKLIST.md complete |

## 8. Code conventions

Python
- Python 3.11+. Type hints everywhere. pydantic v2 models at every boundary (spec, tracks, result).
- `engine.py` and `checks.py` are pure functions: no network, no file I/O, fully unit-tested.
- Network and disk I/O only in `spec.py`, `segment.py`, `pipeline.py`, `api.py`.
- `logging`, never `print`, in library code. ruff for lint and format. pytest for tests.
- Every threshold lives in one `config.py` with a comment saying where its value came from.

TypeScript (web/)
- Strict mode, no `any`. Next.js App Router. Server components by default; `"use client"` only for interactive or animated components.
- All backend calls go through `web/src/lib/api.ts`. Types mirror the pydantic models in `docs/ARCHITECTURE.md`.
- Imported components (shadcn registries, 21st.dev, React Bits, Skiper UI, Watermelon UI, bklit) must be the TypeScript + Tailwind variants and must be restyled to the tokens in `docs/DESIGN.md`.

## 9. Frontend rules (full detail in docs/DESIGN.md and docs/TOOLS.md)

- Three routes: `/` landing (the story), `/workspace` (the tool), `/results` (the evidence).
- shadcn/ui is the base. bklit for every chart. Motion (`motion/react`) for component animation on every route.
- GSAP (ScrollTrigger, SplitText, DrawSVG) and Lenis only on `/`. Lenis is driven by `gsap.ticker` (one animation clock), with `data-lenis-prevent` on any inner scroll area.
- At most 3 decorative effects on `/`, zero on `/workspace` and `/results`.
- Barba.js is not used (it is built for multi-page sites; Next.js already routes on the client).
- `prefers-reduced-motion: reduce` disables Lenis, scroll scenes and text effects; content stays fully readable.
- `/workspace` must not import GSAP, Lenis, or decorative components.

## 10. Definition of done (every task)

1. `make test` and `make lint` pass.
2. If the engine or checks changed, `make eval` was rerun and the before/after numbers are in the report.
3. One commit per concern, message starting with the phase: `phase 1: local quadratic fit for speed`.
4. A short report to the human: what changed, numbers before and after, open risks.

## 11. Ask the human when

- A phase gate is reached.
- An API behaves differently from section 3.
- A change would alter the scope, the thesis, or the metrics.
- Spend would exceed $2 in a day.
- Anything might break a hackathon rule (see docs/RULES_CHECKLIST.md).
