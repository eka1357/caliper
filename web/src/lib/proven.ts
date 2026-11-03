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

function setPart(label: string, s: FieldSummary | undefined, rows: FieldClip[], set: string): string | null {
  if (!s) return null;
  if (s.measured > 0) return `${label}: ${s.measured} of ${s.n} measured`;
  const top = topReason(rows, set);
  const why = top ? ` (most often "${top.reason}", ${top.count} of ${top.n})` : "";
  return `all ${s.n} of our ${label} were refused${why}`;
}

/** Hero subline: size proven on our own clips; speed and acceleration not yet on our footage. */
export function provenLine(summary: Record<string, FieldSummary>, rows: FieldClip[]): string | null {
  const size = summary.size;
  if (!size || size.measured === 0 || size.median_rel_error == null) return null;
  const covered = size.coverage == null ? null : Math.round(size.coverage * size.measured);
  const sizePart =
    `Proven on our own clips: size, ${size.measured} of ${size.n} measured against a tape, median error ${pct(size.median_rel_error)}` +
    (covered == null ? "" : `, truth inside the 90% range on ${covered} of ${size.measured}`) +
    ".";
  const speed = setPart("car-speed clips", summary.speed, rows, "speed");
  const drop = setPart("drop clips", summary.gravity, rows, "gravity");
  const notYet = [speed, drop].filter(Boolean).join(", and ");
  if (!notYet) return sizePart;
  const proven = (summary.speed?.measured ?? 0) > 0 || (summary.gravity?.measured ?? 0) > 0;
  return proven
    ? `${sizePart} Speed and acceleration on our own footage: ${notYet}.`
    : `${sizePart} Speed and acceleration work on the QuantiPhy benchmark but are not yet measured on our own footage: ${notYet}.`;
}
