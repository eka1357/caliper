# Setup

Steps 1 to 3 and 6 are accounts, tools and data and can be done any time. Steps 4 and 5 create application code and start after Oct 27 00:00 ET (9:30 AM IST), the start of the official building period.

## 1. Accounts and keys

| What | Where | Env var |
| --- | --- | --- |
| Meta Model API key (hackathon credits). Add a credit card first (calls fail without one, even with credits); set a Spend Limit notification on the Billing page; claim the $150 credits when the link arrives | dev.meta.ai | `MODEL_API_KEY` |
| Baseten account; request the $100 hackathon credits (model `meta-models/muse-spark-open-1026`) | baseten.co | `BASETEN_API_KEY` |
| Hugging Face token, with access granted to the gated `facebook/sam3.1` model (fallback only) | huggingface.co | `HF_TOKEN` |
| Modal account and token (fallback SAM, backend hosting); request the $100 credits now, first 1,000 participants | modal.com | `MODAL_TOKEN_ID`, `MODAL_TOKEN_SECRET` |
| 21st.dev API key for the Magic MCP (optional) | 21st.dev (see github.com/21st-dev/magic) | `TWENTYFIRST_API_KEY` |
| GitHub repo `caliper` (private while building is fine; must be public at submission) | github.com | none |
| Vercel account for the web app | vercel.com | none |

## 2. System tools

- Python 3.11 or newer, Node.js 20 LTS or newer, git, make.
- ffmpeg and ffprobe on PATH. Check with `ffmpeg -version`.
- Optional: the `hf` CLI (`pip install -U huggingface_hub`) for dataset downloads.

## 3. Repo

```
git init caliper && cd caliper
# copy every file from this kit into the repo root
cp .env.example .env        # then fill in your keys; never commit .env
git add . && git commit -m "phase 0: project docs and config"
```

## 4. Backend (after Oct 27 00:00 ET)

```
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

## 5. Web app (after Oct 27 00:00 ET)

```
npx create-next-app@latest web --typescript --tailwind --eslint --app --src-dir --import-alias "@/*"
cd web
npx shadcn@latest init
npx shadcn@latest add button card badge tabs tooltip dialog sheet slider switch textarea collapsible skeleton progress table sonner
npm i motion gsap @gsap/react lenis
npx shadcn@latest add @bklit/line-chart @bklit/area-chart
# React Bits readout effect (pick the exact name on reactbits.dev):
# npx shadcn@latest add @react-bits/<Name>-TS-TW
# Fonts: Instrument Serif, Geist, Geist Mono via next/font/google in src/app/layout.tsx
```

shadcn MCP for Claude Code (run inside `web/`, then start Claude Code from `web/` for UI work):

```
npx shadcn@latest mcp init --client claude
```

21st.dev Magic MCP: already in the root `.mcp.json`. Export `TWENTYFIRST_API_KEY` in your shell before starting Claude Code, or remove the entry if you don't use it.

## 6. Evaluation data (can be done now)

```
git clone https://github.com/Paulineli/QuantiPhy eval/quantiphy
hf download PaulineLi/QuantiPhy-validation --repo-type dataset --local-dir data/quantiphy-val
# older CLI: huggingface-cli download PaulineLi/QuantiPhy-validation --repo-type dataset --local-dir data/quantiphy-val
```

Both folders are gitignored. The videos keep their original licenses: research and evaluation only.

## 7. First checks on Oct 27

1. `python -c "import os; print(bool(os.environ.get('MODEL_API_KEY')))"` prints True after loading `.env`.
2. One Muse Spark text call returns (Phase 0 script).
3. One SAM 3.1 call on a QuantiPhy clip returns frames (Phase 0 script).
4. `npm run dev` in `web/` serves the default page.

## 8. Agent files at a glance

| File | Read by |
| --- | --- |
| `AGENTS.md` | Codex, Cursor, Antigravity 1.20.5+, most agents (source of truth) |
| `CLAUDE.md` | Claude Code (imports AGENTS.md with `@AGENTS.md`) |
| `GEMINI.md` | Gemini CLI, older Antigravity |
| `.cursor/rules/caliper.mdc` | Cursor (always-apply pointer) |
| `.claude/settings.json` | Claude Code permissions (denies reading `.env`) |
| `.claude/commands/*.md` | Claude Code slash commands `/phase` and `/gate` |
| `.mcp.json` | Claude Code MCP servers (21st.dev Magic) |
| `PROMPTS.md` | You: copy-paste prompts per phase for any agent |
