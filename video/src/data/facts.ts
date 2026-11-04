// Every value the demo shows or says, built from web/public/results.json and the run JSONs in
// web/public/runs/ through the site's own functions (AGENTS rule 4: nothing typed by hand).
// Pure: the Remotion bundle and scripts/narration.mts both pass the parsed JSON in.
import type { Benchmark } from "../../../web/src/lib/results.ts";
import type { CachedRun, CachedStudyRun } from "../../../web/src/lib/types.ts";
import { decimalsFor, fmt } from "../../../web/src/lib/format.ts";
import { COPY, fixFor } from "../../../web/src/components/workspace/copy.ts";
import {
  h1Finding,
  intervalCover,
  vetoFinding,
} from "../../../web/src/lib/holdout-finding.ts";
import { gateSummary, reasonKey } from "../../../web/src/lib/proven.ts";
import { fmtMra } from "../../../web/src/lib/labels.ts";

export type Sources = {
  results: Benchmark;
  c07: CachedRun;
  a14: CachedRun;
  a08: CachedRun;
  /** Study runs keyed by clip id, A11 to A16 (web/public/runs/study-a1x). */
  study: Record<string, CachedStudyRun>;
};

const UNIT_WORD: Record<string, string> = {
  cm: "centimetres",
  m: "metres",
  "m/s": "metres a second",
  "km/h": "kilometres an hour",
};

/** km/h with one decimal, as the site's speed cards show it (the runs store m/s). */
const kmh = (ms: number) => fmt(ms * 3.6, 1);

function must<T>(v: T | null | undefined, what: string): T {
  if (v === null || v === undefined)
    throw new Error(`missing in the data: ${what}`);
  return v;
}

function measureFacts(run: CachedRun) {
  const r = run.result;
  const value = must(r.value, `${r.run_id} value`);
  const iv = must(r.interval_90, `${r.run_id} interval`);
  const d = decimalsFor(iv, value);
  return {
    value: fmt(value, d),
    lo: fmt(iv[0], d),
    hi: fmt(iv[1], d),
    decimals: d,
  };
}

export function buildFacts(src: Sources) {
  const { results, c07, a14, a08, study } = src;

  // ---- s1: the phone and the coin (C07) ----
  const c = measureFacts(c07);
  const c07Facts = {
    question: c07.meta.question,
    unit: c07.result.unit,
    unitWord: UNIT_WORD[c07.result.unit] ?? c07.result.unit,
    value: c.value,
    lo: c.lo,
    hi: c.hi,
    valueNum: must(c07.result.value, "C07 value"),
    decimals: c.decimals,
    // The site prints these two raw (GuessCard and InstrumentCard on the landing page).
    guess: String(must(c07.guess?.parsed_value, "C07 guess")),
    guessNum: must(c07.guess?.parsed_value, "C07 guess"),
    tape: String(must(c07.meta.instrument?.value, "C07 tape")),
    tapeNum: must(c07.meta.instrument?.value, "C07 tape"),
    instrument: must(c07.meta.instrument, "C07 instrument").instrument,
    target: c07.result.spec.target_phrase,
    reference: must(c07.result.spec.reference_phrase, "C07 reference"),
    /** The coin's diameter as given in the question prior, in the answer's unit. */
    referenceSize: fmt(
      must(c07.result.spec.reference_value_si, "C07 reference size") * 100,
      1,
    ),
    interval: must(c07.result.interval_90, "C07 interval"),
  };

  // ---- s2: our scooter (A14), measure path and gate method ----
  const a14Study = must(study.A14, "study A14");
  const gateReading = must(
    a14Study.result.readings.find((x) => x.status === "measured"),
    "A14 gate reading",
  );
  const gateIv = must(gateReading.interval_90_kmh, "A14 gate interval");
  const a14Iv = must(a14.result.interval_90, "A14 interval");
  const a14Facts = {
    question: a14.meta.question,
    cal: kmh(must(a14.result.value, "A14 value")),
    calNum: must(a14.result.value, "A14 value") * 3.6,
    calLo: kmh(a14Iv[0]),
    calHi: kmh(a14Iv[1]),
    gate: fmt(must(gateReading.speed_kmh, "A14 gate speed"), 1),
    gateNum: must(gateReading.speed_kmh, "A14 gate speed"),
    gateLo: fmt(gateIv[0], 1),
    gateHi: fmt(gateIv[1], 1),
    gateM: String(a14Study.result.gate_distance_m),
    // The GPS app reads whole km/h; the study run stores that reading in km/h.
    gps: String(must(a14Study.meta.instrument?.value, "A14 GPS")),
    gpsNum: must(a14Study.meta.instrument?.value, "A14 GPS"),
    guess: kmh(must(a14.guess?.parsed_value, "A14 guess")),
    guessNum: must(a14.guess?.parsed_value, "A14 guess") * 3.6,
    scooterLength: String(
      must(a14.result.spec.reference_value_si, "A14 scooter length"),
    ),
  };

  // ---- s3: the refusal (A08) ----
  const reason = must(a08.result.abstain_reason, "A08 reason");
  const a08Facts = {
    question: a08.meta.question,
    status: a08.result.status,
    reason,
    reasonShort: reasonKey(reason),
    fix: fixFor(a08.result),
    refusal: COPY.abstained,
  };

  // ---- s4: the audit's record ----
  const veto = must(vetoFinding(results.answers), "veto finding");
  const vetoPhrase = veto.title.includes(": ")
    ? veto.title.slice(veto.title.indexOf(": ") + 2)
    : veto.title.charAt(0).toLowerCase() + veto.title.slice(1);

  // ---- s5: the gate method on our six scooter passes ----
  const gs = must(gateSummary(results.field, "scooter"), "gate summary");
  const passes = Object.keys(study)
    .sort()
    .map((clip) => {
      const run = study[clip];
      const m = run.result.readings.find((x) => x.status === "measured");
      return {
        clip,
        gps: run.meta.instrument?.value ?? null,
        speed: m?.speed_kmh == null ? null : fmt(m.speed_kmh, 1),
        speedNum: m?.speed_kmh ?? null,
        lo: m?.interval_90_kmh ? fmt(m.interval_90_kmh[0], 1) : null,
        hi: m?.interval_90_kmh ? fmt(m.interval_90_kmh[1], 1) : null,
        seen: run.result.vehicles_seen,
        measured: run.result.vehicles_measured,
      };
    });

  // ---- s7: the holdout split ----
  const row = (variant: string) =>
    must(
      results.results.find(
        (r) => r.variant === variant && r.split === "holdout",
      ),
      `${variant} holdout row`,
    );
  const cal = row("caliper");
  const muse = row("muse_spark_alone");
  const paired = must(
    results.paired.find(
      (r) =>
        r.variant === "caliper" &&
        r.split === "holdout" &&
        r.category === "all",
    ),
    "paired holdout row",
  );
  const h1 = must(h1Finding(cal, muse), "H1 finding");
  const cover = intervalCover(results.answers, "caliper", "holdout");
  const nAnswered = paired.n_answered;

  return {
    c07: c07Facts,
    a14: a14Facts,
    a08: a08Facts,
    audit: { vetoPhrase, vetoTitle: veto.title },
    study: {
      n: String(gs.n),
      measured: String(gs.measured),
      medianErr: gs.medianErrKmh.toFixed(1),
      covered: String(gs.covered),
      gateM: String(a14Study.result.gate_distance_m),
      passes,
    },
    holdout: {
      calMra: fmtMra(cal.mra_average),
      museMra: fmtMra(muse.mra_average),
      calMraNum: must(cal.mra_average, "caliper MRA") * 100,
      museMraNum: must(muse.mra_average, "muse MRA") * 100,
      h1Title: h1.title,
      h1Verb: h1.title.includes("failed") ? "failed" : "held",
      n: String(must(cal.n, "holdout n")),
      answered: String(
        Math.round(must(cal.coverage, "coverage") * must(cal.n, "holdout n")),
      ),
      nAnswered: String(nAnswered),
      within10Cal: String(
        Math.round(
          must(paired.within10_variant, "within10 caliper") * nAnswered,
        ),
      ),
      within10Muse: String(
        Math.round(must(paired.within10_muse, "within10 muse") * nAnswered),
      ),
      rangeHeld: String(cover.covered),
      rangeAnswered: String(cover.answered),
    },
    generatedUtc: results.generated_utc,
  };
}

export type Facts = ReturnType<typeof buildFacts>;

/** Looks up "c07.guess" style tokens (narration.md) in the facts. */
export function token(facts: Facts, path: string): string {
  let v: unknown = facts;
  for (const key of path.split(".")) {
    if (v === null || typeof v !== "object" || !(key in v))
      throw new Error(`unknown token {${path}}`);
    v = (v as Record<string, unknown>)[key];
  }
  if (typeof v !== "string") throw new Error(`token {${path}} is not text`);
  return v;
}
