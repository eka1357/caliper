# Demo narration

Spoken English for the 3-minute demo, written for about 130 words a minute, no hype. One audio file
per scene. Voice: ElevenLabs "River" (relaxed, neutral, calm), model `eleven_multilingual_v2`,
stability 0.5.

**No number is typed here.** Every `{token}` is filled by `scripts/narration.mts` from
`web/public/results.json` and the run JSONs in `web/public/runs/`, through the same functions the site
uses (`web/src/lib/format.ts`, `holdout-finding.ts`, `proven.ts`, `components/workspace/copy.ts`).
The captions are built from what was actually spoken, so they match the numbers on screen.

Markup inside the `>` lines:

- `{token}`: a value from the data (see `src/data/facts.ts`).
- `[@cue]`: a timing mark, not spoken. The scene starts an animation when the voice reaches it.
- `[@k_name]...[@/k_name]`: a key line shown as large type; captions are hidden while it is on screen.
- `[[Shown|spoken]]`: the caption shows the first word, the voice says the second (pronunciation only).

Commands: `node scripts/narration.mts resolve` fills the tokens and rewrites the "Spoken text" block
at the end of this file ($0). `node scripts/narration.mts generate s1 s2 ...` calls ElevenLabs.

## s1 · Cold open: the phone and the coin (C07), 0:00 to 0:25

On screen: the clip full frame; SAM's outlines draw on (cyan phone, amber coin); three cards land:
Muse Spark alone's guess, Caliper's value with its 90% range, the tape.

> How long is this phone? [@guess]Asked on its own, Muse Spark guesses {c07.guess} {c07.unitWord}.
> [@caliper]Caliper measures it against the [@coin]coin beside it: {c07.value} {c07.unitWord},
> with a 90% range of {c07.lo} to {c07.hi}. [@tape]The tape says {c07.tape}.
> [@k_title]AI guesses. Caliper measures.[@/k_title]

## s2 · Speed: our scooter (A14), 0:25 to 0:50

On screen: the scooter pass in slow motion with its cyan outline; Caliper, the gate method, GPS and
Muse Spark alone, in that order.

> [@scooter]Speed works the same way, on our own scooter.
> [@caliper]With its taped length as the ruler, Caliper measures {a14.cal} kilometres an hour,
> range {a14.calLo} to {a14.calHi}. [@gate]The gate method, which times it between two lines,
> gives {a14.gate}. [@gps]The GPS read {a14.gps}. [@guess]Muse Spark alone guessed {a14.guess}.

## s3 · A refusal (A08), 0:50 to 1:10

On screen: the car crossing, cut off by the frame edge; the refusal card with the reason and the
fix, as the site shows it.

> [@car]When the video can't support a number, Caliper says so. This car is never fully in the
> picture, so it can't be its own ruler. [@refuse]Caliper's answer:
> [@k_refuse]I won't guess.[@/k_refuse] [@fix]It says why, and how to film it next time.

## s4 · How it works, 1:10 to 1:40

On screen: the question; Muse Spark's plan (the spec JSON); SAM 3.1 tracking; Python measuring;
the checks; the audit keyframes and its verdict.

> [@spec]Muse Spark 1.3 reads the question and the video, and plans what to track and what sets
> the scale. [@sam][[SAM|Sam]] 3.1 outlines both, frame by frame. [@python]Python computes the
> number and its range. [@k_rule]The model never writes the number.[@/k_rule] [@checks]Checks
> refuse when something is off, [@audit]and Muse Spark audits the outlined frames. It can only
> veto. [@veto]So far, {audit.vetoPhrase}.

## s5 · Street speed study, 1:40 to 2:10

On screen: `/study` with the six scooter passes and their speeds. A slot for the S02 street clip
is used only if its results exist (they do not yet).

> [@study]For residents asking for traffic calming, the same engine runs a speed study:
> [@gates]it times each vehicle between two gate lines, or says why it can't. [@passes]On our
> {study.n} scooter passes it timed {study.measured} of {study.n}, median error {study.medianErr}
> kilometres an hour against GPS. [@narrow]But its range is too narrow: GPS fell inside it on
> {study.covered} of {study.measured}.

## s6 · An AI agent calls Caliper over MCP, 2:10 to 2:30

On screen: the captured MCP request and response JSON (measure on C07, then study on A14).

> [@agent]Other agents can call Caliper as a tool, over MCP. [@measure]Here an agent asks it to
> measure the phone, [@studycall]then to run the study on the scooter clip. [@result]The numbers
> come back from Caliper, with their ranges, not from the agent.

## s7 · The honest numbers, 2:30 to 2:52

On screen: holdout official MRA (claim H1 failed), then like for like on the holdout answers.

> [@official]On [[QuantiPhy's|Quantify's]] holdout videos, the official score counts a refusal as a
> miss: Caliper {holdout.calMra}, Muse Spark alone {holdout.museMra}. [@h1]Our pre-registered claim
> {holdout.h1Verb}. [@within]But when Caliper answers, {holdout.within10Cal} of
> {holdout.nAnswered} are within 10%, against {holdout.within10Muse} for the model alone,
> [@range]and its range held on {holdout.rangeHeld} of {holdout.rangeAnswered}.

## s8 · Close, 2:52 to 3:00

On screen: the line, the live URL, the repo URL.

> [@k_line]It would rather say no than guess.[@/k_line]

## x1 · X cut: the phone

> How long is this phone? [@guess]Muse Spark alone guesses {c07.guess} {c07.unitWord}.
> [@caliper]Caliper measures {c07.value}, with a 90% range of {c07.lo} to {c07.hi}. [@tape]The tape
> says {c07.tape}.

## x3 · X cut: the refusal

> [@refuse]When the video can't support a number, Caliper says: [@k_refuse]I won't guess.[@/k_refuse]
> [@fix]And it tells you why.

## x7 · X cut: the numbers

> [@within]On held-out benchmark videos it answers only {holdout.answered} of {holdout.n}. When it
> answers, {holdout.within10Cal} of {holdout.nAnswered} are within 10%, against
> {holdout.within10Muse} for the model alone. [@k_line]It would rather say no than guess.[@/k_line]

## Spoken text

<!-- spoken:start (generated by node scripts/narration.mts resolve; do not edit) -->

**s1** (40 words, 219 characters): How long is this phone? Asked on its own, Muse Spark guesses 16.2 centimetres. Caliper measures it against the coin beside it: 14 centimetres, with a 90% range of 9 to 22. The tape says 14. AI guesses. Caliper measures.

**s2** (46 words, 254 characters): Speed works the same way, on our own scooter. With its taped length as the ruler, Caliper measures 39.4 kilometres an hour, range 25.2 to 61.5. The gate method, which times it between two lines, gives 42.6. The GPS read 42. Muse Spark alone guessed 28.8.

**s3** (40 words, 201 characters): When the video can't support a number, Caliper says so. This car is never fully in the picture, so it can't be its own ruler. Caliper's answer: I won't guess. It says why, and how to film it next time.

**s4** (64 words, 354 characters): Muse Spark 1.3 reads the question and the video, and plans what to track and what sets the scale. SAM 3.1 outlines both, frame by frame. Python computes the number and its range. The model never writes the number. Checks refuse when something is off, and Muse Spark audits the outlined frames. It can only veto. So far, both its vetoes were false alarms.

**s5** (58 words, 294 characters): For residents asking for traffic calming, the same engine runs a speed study: it times each vehicle between two gate lines, or says why it can't. On our 6 scooter passes it timed 6 of 6, median error 3.8 kilometres an hour against GPS. But its range is too narrow: GPS fell inside it on 1 of 6.

**s6** (41 words, 212 characters): Other agents can call Caliper as a tool, over MCP. Here an agent asks it to measure the phone, then to run the study on the scooter clip. The numbers come back from Caliper, with their ranges, not from the agent.

**s7** (47 words, 259 characters): On QuantiPhy's holdout videos, the official score counts a refusal as a miss: Caliper 20.1, Muse Spark alone 58.1. Our pre-registered claim failed. But when Caliper answers, 9 of 15 are within 10%, against 4 for the model alone, and its range held on 13 of 15.

**s8** (7 words, 34 characters): It would rather say no than guess.

**x1** (26 words, 134 characters): How long is this phone? Muse Spark alone guesses 16.2 centimetres. Caliper measures 14, with a 90% range of 9 to 22. The tape says 14.

**x3** (17 words, 89 characters): When the video can't support a number, Caliper says: I won't guess. And it tells you why.

**x7** (32 words, 161 characters): On held-out benchmark videos it answers only 15 of 69. When it answers, 9 of 15 are within 10%, against 4 for the model alone. It would rather say no than guess.

Main cut: 343 words. Data generated 2026-11-03T15:12:35+00:00.
<!-- spoken:end -->
