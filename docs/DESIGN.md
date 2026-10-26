# Design system

Caliper should feel like a precision instrument: calm, dark, exact. The number is the hero, the evidence is one click away, and motion explains rather than decorates.

## 1. Principles

1. **The number is the hero.** One measured value, large, monospaced, with its range directly under it.
2. **Show the chain.** Every number can be expanded into spec, scale, fit and checks.
3. **Honest states.** "Measured" and "Abstained" look equally deliberate. A refusal is a feature, never an error style.
4. **Guesses look like guesses.** Muse Spark alone is shown dimmed with a dashed border and the label "guess".
5. **Motion explains.** On the landing page motion tells the story. In the workspace motion only confirms state changes.

## 2. Color tokens (starting values; finalize in Realtime Colors)

Dark theme only for the hackathon (see docs/DECISIONS.md). Semantic colors carry meaning everywhere, including the video overlay.

| Token | Start value | Meaning |
| --- | --- | --- |
| `--background` | `#0A0C0F` | Page |
| `--card` | `#12161B` | Panels, readout cards |
| `--muted` | `#181D23` | Inputs, secondary surfaces |
| `--border` | `#232A32` | Borders, measurement grid lines |
| `--foreground` | `#E9EDF1` | Main text, the measured number |
| `--muted-foreground` | `#8A96A3` | Secondary text, the "guess" |
| `--primary` | `#FFB224` | Amber: the ruler. Scale reference outline, primary button, "Measured" badge |
| `--track` | `#2FD3E6` | Cyan: the target being measured. Mask outline and trajectory |
| `--success` | `#3DDC97` | Passed checks |
| `--destructive` | `#FF5A5F` | Failed checks, "Abstained" badge accent |

Workflow in [Realtime Colors](https://www.realtimecolors.com/):
1. Enter text `#E9EDF1`, background `#0A0C0F`, primary `#FFB224`, secondary `#2FD3E6`, accent `#3DDC97`.
2. Set heading font "Instrument Serif", body font "Geist", type scale 1.250.
3. Fix every pair the contrast checker marks red. Every text pair must pass at least AA.
4. Export with the shadcn custom-code preset in OKLCH and paste the variables into `web/src/app/globals.css`. Add `--track` and `--success` by hand.
5. Record the final values in this table and in docs/DECISIONS.md.

## 3. Typography

| Role | Font (next/font/google) | Use |
| --- | --- | --- |
| Display | Instrument Serif | Landing H1 and H2 only |
| UI | Geist | Everything else |
| Numbers and code | Geist Mono, `font-variant-numeric: tabular-nums` | Measured values, units, intervals, JSON |

Scale (rem): 0.75, 0.875, 1, 1.25, 1.563, 1.953, 2.441, 3.052, 3.815. The workspace readout number is 3.5rem Geist Mono; its unit is 1.25rem in `--muted-foreground`.

## 4. Layout

- 4 px spacing base. Radius 10 px on cards, 6 px on controls.
- Landing: 12-column grid, max width 1200 px, generous vertical rhythm (section padding 128 px desktop, 72 px mobile).
- Workspace: two panes at 1024 px and up (video stage 7/12, control panel 5/12). Stacked below 1024 px.
- Measurement grid motif: a CSS background of 1 px `--border` lines every 24 px on the landing hero and the video stage. No library needed.

## 5. Motion

One clock per page. On `/` GSAP's ticker drives Lenis and ScrollTrigger. Motion handles component state changes on every page.

| Element | Library | Spec |
| --- | --- | --- |
| Hover and press | Motion | 120 to 160 ms, ease `[0.2, 0, 0, 1]` |
| Result card enter and exit | Motion `AnimatePresence mode="wait"` | 240 ms, opacity 0 to 1, y 8 px to 0 |
| Readout number | Motion `animate` | Counts to the value over 600 ms, ease-out; the interval bar grows after it |
| Mask outlines | CSS or Motion | 200 ms fade per object |
| Panel layout changes | Motion `layout` | Spring, no overshoot |
| Landing hero headline | GSAP SplitText | Words rise 12 px with 0.03 s stagger, once on load |
| Landing trajectory | GSAP DrawSVG + ScrollTrigger | The cyan path draws as the user scrolls through the hero |
| "How it works" | GSAP ScrollTrigger pin | 4 steps pinned, scrub 0.6 |
| Landing readout digits | React Bits DecryptedText (or CountUp) | Digits scramble, then lock to the measured value: guess turns into measurement |
| Smooth scroll | Lenis via `lenis/react`, `autoRaf: false`, driven by `gsap.ticker` | Landing only; `data-lenis-prevent` on inner scroll areas |

Reduced motion (`prefers-reduced-motion: reduce`): no Lenis, no pin, no scrub, no text effects; elements appear at their final state with a 150 ms opacity fade at most.

Effect budget: exactly three decorative effects on `/` (hero SplitText, DrawSVG trajectory, DecryptedText readout). Zero on `/workspace`, `/study` and `/results`.

## 6. Pages

### `/` Landing: the story (find two Unsection references for each section before building it)

1. **Hero.** H1 "AI guesses. Caliper measures." Subline: "Ask how big, how fast, or how hard something accelerates in a video. Get a measured number with an error range, or an honest no." Primary button "Measure a clip" to `/workspace`; secondary "See the evidence" to `/results`. Visual: a looping muted field clip with the cyan target outline, amber reference outline, the trajectory, and a small readout card.
2. **The gap.** Three readout cards for one real clip: "Muse Spark alone" (guess style), "Caliper" (measured), "Instrument" (GPS or tape). Values load from the cached run JSON. Line: "Same model. Same video. One guesses, one measures."
3. **How it works.** Pinned four-step scene using real artifacts from one cached run: Read (the spec JSON), Find (masks appear), Measure (the fit curve draws), Check (checks tick, or the refusal appears).
4. **The audit.** One keyframe with overlays and Muse Spark's verdict beside it; one vetoed example ("SAM followed the wrong car, so Caliper refused").
5. **On a real street.** A still from the street study with vehicles tagged by speed and range, the 85th-percentile card, and one line of context with its source (177,175 road deaths in India in 2024; 70.3% attributed to over-speeding). Button "Run a speed study" to `/study`.
6. **Evidence.** bklit bar chart of MRA by variant on the holdout split with the human baseline as a labelled reference line; field-set accuracy and speed-vs-GPS error in one sentence each; link to `/results`.
7. **When Caliper says no.** Two or three abstention cards with their exact reasons, from cached runs.
8. **For agents and open weights (stretch).** The `measure()` MCP tool call and its JSON result; the Muse Spark Open backend badge if built.
9. **Footer.** Built with Muse Spark 1.3 and SAM 3.1 on Meta Model API (plus Muse Spark Open if built); "Built Oct 27 to Nov 4 2026"; QuantiPhy credit and license note; repo link; limitations link.

### `/workspace`: the tool

- Left pane: video stage with overlay toggles (target, reference, trajectory), a scrubber (shadcn Slider) with the fit window shaded, play and frame-step buttons.
- Right pane: question box with three example chips; collapsible "I know one real size or speed" for an optional prior; primary "Measure" button; switch "Compare with Muse Spark alone".
- Result card: status badge, the number, unit, interval bar, one method line ("centroid, local quadratic, window 0.30 s").
- "Show the chain" (Collapsible): Spec (JSON), Scale (reference, value, source, metres per pixel), Fit (bklit line chart of position and fit over time; speed over time), Checks (name, value, threshold, pass or fail), Audit (the keyframes Muse Spark saw and its verdict in plain words), Backend (Meta API or Muse Spark Open), Cost and timing.
- States and copy:

| State | Copy |
| --- | --- |
| Idle | "Drop a clip or record one. Keep the phone still." |
| Uploading | "Uploading {n}%" |
| Preparing | "Preparing the video" |
| Reading | "Reading your question" |
| Finding | "Finding the {target} and the {reference}" |
| Measuring | "Measuring" |
| Checking | "Checking the measurement" |
| Auditing | "Muse Spark is checking the evidence" |
| Measured | Number, range, method |
| Abstained | "I won't guess." followed by the reason from the failed check or the audit, and one fix ("Add a coin next to the object") |
| Live cap reached | "Live runs are paused for now. Try one of these recorded runs." with the cached runs listed |
| Error | "Something broke on our side." plus a retry button; never a fake number |

- Mobile capture flow (study ScreensDesign onboarding and camera-permission flows first): a one-screen guide before recording ("Keep the phone still. Put a coin beside the object, at the same distance. Film the motion side to side, not toward you."), then `<input type="file" accept="video/*" capture="environment">`, then a review step before upload.

### `/study`: street speed study

- Step 1: drop or record a street clip (guide: "Phone fixed, side-on to the road. Two marks a measured distance apart along the road edge, both in frame.").
- Step 2: on the first frame, drag two gate lines across the road onto the marks; type the distance in metres and, optionally, the speed limit.
- Step 3: run. The video plays with each vehicle outlined in cyan as it crosses the gates, its speed and range in a small mono label; vehicles Caliper cannot measure get a grey "no reading" label with the reason on hover.
- Summary card: vehicles seen, measured, no reading; median; 85th-percentile speed in large mono with its range under it; share over the limit.
- bklit histogram of measured speeds with the 85th percentile and the limit as labelled reference lines.
- "Printable report" opens a clean page (date, place typed by the user, method in one paragraph, the summary, the histogram, the per-vehicle table, the limitations) for `window.print()`.
- Copy never implies enforcement: "Speed survey for road-safety requests", not "catch speeders". No plates or faces are stored or shown.

### `/results`: the evidence

- Table of every row in `results.json` (variant by split) with source notes.
- bklit charts: MRA by variant (holdout) with the human baseline line, including audit on and off; MRA by category (S2, D2, S3, D3); field-set relative error per clip as dots with the 10% target line; speed study error vs GPS for set A; interval coverage as one number with its target; audit catches and false vetoes as two numbers.
- Download links for `results.csv` and `field_results.csv`; a short methodology summary linking docs/EVAL_PROTOCOL.md.

## 7. Component sources

| Need | Source | Install |
| --- | --- | --- |
| Button, Card, Badge, Tabs, Tooltip, Dialog, Sheet, Slider, Switch, Textarea, Collapsible, Skeleton, Progress, Table, Sonner | shadcn/ui | `npx shadcn@latest add button card badge tabs tooltip dialog sheet slider switch textarea collapsible skeleton progress table sonner` |
| Line and area charts | bklit | `npx shadcn@latest add @bklit/line-chart @bklit/area-chart` (pick the bar chart name from the bklit catalog) |
| Readout digit effect | React Bits | Install the TS-TW variant shown on the DecryptedText (or CountUp) page, e.g. `npx shadcn@latest add @react-bits/<Name>-TS-TW` |
| Upload dropzone, section shells | 21st.dev | "Copy prompt" or the shadcn command on the component page (free tier: 2 copies a day, so pick these two first) |
| Dashboard shell for the workspace (optional) | Watermelon UI | shadcn command shown on the block page |
| One distinctive interaction (optional) | Skiper UI free components | `npx shadcn@latest add @skiper-ui/<id>` |

Rules for imported components: TypeScript + Tailwind variant only; restyle to the tokens above; reject anything that pulls in a library outside docs/TOOLS.md (for example three.js); every animated import must honour reduced motion.

## 8. Design QA (run before Phase 5 gate and before submission)

- [ ] Every text pair passes WCAG AA (Realtime Colors checker or browser devtools).
- [ ] Keyboard only: every control reachable, focus ring visible.
- [ ] Reduced motion verified in the OS setting.
- [ ] Landing Lighthouse mobile: LCP under 2.5 s, CLS under 0.1.
- [ ] `next build` output shows no gsap or lenis chunk on `/workspace`, `/study` or `/results`.
- [ ] Landing scroll holds 60 fps in the Chrome performance panel on a mid-range laptop.
- [ ] No layout shift when the result card appears.
- [ ] Every number on screen traces to `results.json` or a run JSON.
