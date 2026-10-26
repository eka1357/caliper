# Tools: what we use, where, and what we skip

Your 15 recommended tools, each with a verdict. Rule of thumb: libraries go on the landing page where they tell the story; the workspace stays fast and plain.

| Tool | Verdict | Where | How | Caveat |
| --- | --- | --- | --- | --- |
| [Motion](https://motion.dev/) | **Use** | Every route | `npm i motion`; import from `motion/react` | Use for state changes only, not scroll scenes |
| [GSAP](https://gsap.com/) | **Use** | `/` only | `npm i gsap @gsap/react`; `useGSAP` inside `"use client"` files; ScrollTrigger, SplitText, DrawSVG | Free including all bonus plugins and commercial use since 3.13 ([GSAP 3.13](https://gsap.com/blog/3-13/)) |
| [Lenis](https://lenis.dev/) | **Use** | `/` only | `npm i lenis`; `ReactLenis` from `lenis/react` with `root` and `autoRaf: false`; drive with `gsap.ticker`; import `lenis/dist/lenis.css` | No CSS scroll-snap without `lenis/snap`; Safari capped at 60 fps; add `data-lenis-prevent` to inner scroll areas |
| [bklit](https://bklit.com/) | **Use** | All charts | shadcn-based chart library: `npx shadcn@latest add @bklit/line-chart` | Requires shadcn/ui set up first |
| [React Bits](https://reactbits.dev/) | **Use (1 effect)** | `/` readout digits | `npx shadcn@latest add @react-bits/<Name>-TS-TW` | Code is copied into the repo; restyle to tokens |
| [21st.dev](https://21st.dev/) | **Use** | Dropzone, section shells | "Copy prompt" or shadcn command per component; optional Magic MCP in `.mcp.json` | Free tier: 2 component copies a day; choose carefully |
| [Watermelon UI](https://ui.watermelon.sh/) | **Optional** | Workspace shell | shadcn command on each block page | Only if a block fits the two-pane layout |
| [Skiper UI](https://skiper-ui.com/) | **Optional** | One interaction at most | `npx shadcn@latest add @skiper-ui/<id>` (free components) | Premium is $129 one-time; not needed |
| [Realtime Colors](https://www.realtimecolors.com/) | **Use** | Palette and fonts, before Phase 5 | Preview, contrast check, export shadcn variables in OKLCH | Verify every pair passes AA |
| [Unsection](https://www.unsection.com/) | **Use (inspiration)** | Landing sections | Collect two references per section type | Image gallery only, no code |
| [ScreensDesign](https://screensdesign.com/) | **Use (inspiration)** | Mobile capture flow | Study camera-permission and onboarding flows | Library is mostly iOS apps |
| [Jitter](https://jitter.video/) | **Use** | Demo video | Title card, architecture animation, chart reveal; exports up to 4K video, GIF, Lottie | Check the free plan's export limits before relying on it |
| [Manus](https://manus.im/) | **Use outside the code** | Research and QA | Pre-kickoff research brief; adversarial QA of the deployed demo; slides if required | Now owned by Meta ([acquisition report](https://www.businesstoday.in/amp/technology/news/story/meta-acquires-ai-startup-manus-in-milestone-deal-worth-over-2-billion-508760-2025-12-31)); never give it secrets; do not let it write project code |
| [Toolfolio](https://toolfolio.com/) | **Discovery only** | When a tool is missing | Search, then log any choice in docs/DECISIONS.md | Not a dependency |
| [Barba.js](https://barba.js.org/) | **Skip** | n/a | n/a | Built for transitions between pages of a multi-page site. Next.js already routes on the client, so two routers would fight over the same links. Route transitions use Motion `AnimatePresence` instead |

## Core stack (not on your list, required)

| Tool | Why |
| --- | --- |
| Next.js 16 (App Router), TypeScript, Tailwind CSS | Web app; `npx create-next-app@latest` |
| shadcn/ui | Base components and the registry CLI that installs bklit, React Bits and Skiper UI |
| FastAPI, pydantic v2, uvicorn | Backend API and data contracts |
| openai (Python SDK) | Calls Meta Model API at `https://api.meta.ai/v1` |
| meta-sam-parser | Parses SAM 3.1 stream lines and decodes masks |
| numpy, scipy, opencv-python-headless, pandas | Engine math, video frames, CSVs |
| ffmpeg | Normalizes video to H.264 MP4 with faststart |
| Modal | SAM 3.1 open-weights fallback and backend hosting ($100 credits for the first 1,000 who request) |
| Baseten | Muse Spark Open (`meta-models/muse-spark-open-1026`) for the stretch open-weights backend ($100 credits, reviewed by use case) |

## How the animation libraries share one page

- `/` creates Lenis with `autoRaf: false`, then in one client component: `lenis.on('scroll', ScrollTrigger.update)`, `gsap.ticker.add((time) => lenis.raf(time * 1000))`, `gsap.ticker.lagSmoothing(0)`. This is the pattern in the Lenis README.
- Motion components on `/` run their own animations but never drive scroll.
- `/workspace`, `/study` and `/results` import only Motion. Check the build output to confirm.
