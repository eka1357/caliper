// "What is proven so far" for the landing hero, from the field rows and summary in
// web/public/results.json (eval/field_results.csv). No imports, so tests/proven.test.mjs runs it
// with node --test. Every number is read from the rows.

export interface FieldClip {
  set: string;
  path: string;
  status: "measured" | "abstained";
  reason: string;
}

export interface FieldSummary {
  n: number;
  measured: number;
  median_rel_error: number | null;
  coverage: number | null;
}

const pct = (v: number) => `${Math.round(v * 100)}%`;

/** A refusal reason without its per-clip numbers, e.g. "(0 whole-object frames, 5 needed)". */
export function reasonKey(reason: string): string {
  return reason.replace(/\s*\([^)]*\d[^)]*\)\s*\.?\s*$/, "").replace(/\.\s*$/, "").trim();
}

/** The most common refusal reason in a set, with how many clips gave it. */
export function topReason(rows: FieldClip[], set: string): { reason: string; count: number; n: number } | null {
  const refused = rows.filter((r) => r.set === set && r.path === "measure" && r.status === "abstained" && r.reason);
  if (refused.length === 0) return null;
  const counts = new Map<string, number>();
  for (const r of refused) counts.set(reasonKey(r.reason), (counts.get(reasonKey(r.reason)) ?? 0) + 1);
  const [reason, count] = [...counts.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))[0];
  return { reason, count, n: refused.length };
}

// Speed sets in display order: Set A (scooter, filmed 2026-11-03) and Set A as first filmed (car).
const SPEED_SETS: [string, string][] = [["scooter", "scooter passes"], ["speed", "first car-speed clips"]];

function refusedPart(label: string, s: FieldSummary, rows: FieldClip[], set: string): string {
  const top = topReason(rows, set);
  const why = top ? ` (most often "${top.reason}", ${top.count} of ${top.n})` : "";
  return `all ${s.n} of our ${label} were refused${why}`;
}

function measuredPart(label: string, s: FieldSummary): string {
  const covered = s.coverage == null ? null : Math.round(s.coverage * s.measured);
  return (
    `our ${label}, ${s.measured} of ${s.n} measured against GPS` +
    (s.median_rel_error == null ? "" : `, median error ${pct(s.median_rel_error)}`) +
    (covered == null ? "" : `, GPS inside the 90% range on ${covered} of ${s.measured}`)
  );
}

/** Hero subline: what is measured on our own clips, and what was refused there (with reasons). */
export function provenLine(summary: Record<string, FieldSummary>, rows: FieldClip[]): string | null {
  const size = summary.size;
  if (!size || size.measured === 0 || size.median_rel_error == null) return null;
  const covered = size.coverage == null ? null : Math.round(size.coverage * size.measured);
  const sizePart =
    `Proven on our own clips: size, ${size.measured} of ${size.n} measured against a tape, median error ${pct(size.median_rel_error)}` +
    (covered == null ? "" : `, truth inside the 90% range on ${covered} of ${size.measured}`) +
    ".";
  const measured: string[] = [];
  const refused: string[] = [];
  for (const [set, label] of SPEED_SETS) {
    const s = summary[set];
    if (!s) continue;
    if (s.measured > 0) measured.push(measuredPart(label, s));
    else refused.push(refusedPart(label, s, rows, set));
  }
  if (summary.gravity) {
    if (summary.gravity.measured > 0) measured.push(`drops, ${summary.gravity.measured} of ${summary.gravity.n} measured`);
    else refused.push(refusedPart("drop clips", summary.gravity, rows, "gravity"));
  }
  if (measured.length === 0) {
    return refused.length
      ? `${sizePart} Speed and acceleration work on the QuantiPhy benchmark but are not yet measured on our own footage: ${refused.join(", and ")}.`
      : sizePart;
  }
  const speed = `Speed on our own footage: ${measured.join("; ")}.`;
  return refused.length ? `${sizePart} ${speed} Refused on our own footage: ${refused.join(", and ")}.` : `${sizePart} ${speed}`;
}

export interface SetGuess {
  n: number;
  measured: number;
  median_rel_error: number | null;
  coverage: number | null;
  guess_median_rel_error: number | null;
}

/** The scooter set on the landing: single passes on the measure path against GPS. */
export function scooterLine(s: SetGuess | undefined): { title: string; body: string } | null {
  if (!s || s.n === 0) return null;
  const refused = s.n - s.measured;
  const covered = s.coverage == null ? null : Math.round(s.coverage * s.measured);
  const parts = [
    s.measured > 0
      ? `Caliper measured ${s.measured} of the ${s.n} passes` +
        (s.median_rel_error == null ? "" : `: median error ${pct(s.median_rel_error)}`) +
        (covered == null ? "" : `, GPS inside its 90% range on ${covered} of ${s.measured}`)
      : `Caliper refused all ${s.n} passes`,
  ];
  if (s.measured > 0 && refused > 0) parts.push(`it refused ${refused}, with its reason`);
  const guess = s.guess_median_rel_error == null ? "" : ` Muse Spark alone, given the same length, was off by a median ${pct(s.guess_median_rel_error)}, with no range.`;
  return { title: `${s.n} passes of our own scooter against GPS`, body: `${parts.join("; ")}.${guess}` };
}

/** A study-path or measure-path row of a speed set (results.json field rows; speeds in m/s). */
export interface SpeedRow {
  clip_id: string;
  set: string;
  path: string;
  status: "measured" | "abstained";
  pred: number | null;
  lo: number | null;
  hi: number | null;
  truth: number | null;
  covered: boolean | null;
}

const kmh1 = (v: number) => (v * 3.6).toFixed(1);
const median = (xs: number[]) => {
  const s = [...xs].sort((a, b) => a - b);
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
};

/**
 * The gate method (study path) on one speed set: median absolute error in km/h, how often GPS
 * falls inside its range, and how wide that range is (it covers frame timing, gate placement
 * and the tape tolerance only).
 */
export function gateSummary(rows: SpeedRow[], set: string) {
  const g = rows.filter((r) => r.set === set && r.path === "study");
  const m = g.filter((r) => r.status === "measured" && r.pred != null && r.truth != null);
  if (g.length === 0 || m.length === 0) return null;
  const errKmh = m.map((r) => Math.abs(r.pred! - r.truth!) * 3.6);
  const half = m.filter((r) => r.lo != null && r.hi != null).map((r) => (r.hi! - r.lo!) / 2 / r.pred!);
  return {
    n: g.length,
    measured: m.length,
    medianErrKmh: median(errKmh),
    covered: m.filter((r) => r.covered).length,
    halfMin: Math.min(...half),
    halfMax: Math.max(...half),
  };
}

const pct1 = (v: number) => `${(v * 100).toFixed(1)}%`;

/** Plain sentence about the gate method beside the measure-path results. */
export function gateLine(rows: SpeedRow[], set: string, distanceM: number | null): string | null {
  const s = gateSummary(rows, set);
  if (!s) return null;
  const dist = distanceM == null ? "" : ` (two gate lines ${distanceM} m apart on the riding line)`;
  return (
    `The gate method${dist} timed ${s.measured} of ${s.n} passes, median error ${s.medianErrKmh.toFixed(1)} km/h. ` +
    `Its 90% range covers only frame timing, gate placement and the tape tolerance (about ±${pct1(s.halfMin)} to ${pct1(s.halfMax)}), ` +
    `so GPS falls inside it on ${s.covered} of ${s.measured}.`
  );
}

/**
 * Passes where Caliper and the gate method agree with each other but not with GPS, stated as the
 * human's observation (DECISIONS 2026-11-03), possibly GPS error. Truth stays as recorded; the
 * numbers come from the rows.
 */
export function gpsDisagreeNote(rows: SpeedRow[], clips: readonly string[]): string | null {
  const parts = clips.flatMap((clip) => {
    const m = rows.find((r) => r.clip_id === clip && r.path === "measure" && r.status === "measured");
    const g = rows.find((r) => r.clip_id === clip && r.path === "study" && r.status === "measured");
    if (!m?.pred || !g?.pred || m.truth == null) return [];
    return [`${clip}: ${kmh1(m.pred)} and ${kmh1(g.pred)} km/h against GPS ${kmh1(m.truth)}`];
  });
  if (parts.length === 0) return null;
  const who = parts.length === 1 ? "one pass" : `${parts.length} passes`;
  return `On ${who} Caliper and the gate method agree with each other but not with GPS (${parts.join("; ")}), possibly GPS error. Observation only: the GPS readings stay as recorded.`;
}

// EVAL_PROTOCOL section 1, claim H5 (pre-registered): median absolute error at most 3 km/h and the
// 90% range containing GPS on at least 8 of 10 passes; disproved if the median is above 6 km/h.
const H5_TARGET_KMH = 3;
const H5_DISPROVED_KMH = 6;
const H5_COVER_SHARE = 0.8;

/** Claim H5 on the gate method's passes, in the protocol's own terms. */
export function h5Line(rows: SpeedRow[], set: string): string | null {
  const s = gateSummary(rows, set);
  if (!s) return null;
  const met = s.medianErrKmh <= H5_TARGET_KMH && s.covered >= H5_COVER_SHARE * s.measured;
  const verdict = met ? "met" : s.medianErrKmh > H5_DISPROVED_KMH ? "disproved" : "not met (not disproved: that needs a median above 6 km/h)";
  return `Claim H5 (median error at most ${H5_TARGET_KMH} km/h, GPS inside the range on at least 8 of 10 passes): ${s.medianErrKmh.toFixed(1)} km/h and ${s.covered} of ${s.measured}, ${verdict}.`;
}
