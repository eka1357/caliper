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
