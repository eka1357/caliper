// Build-time reader for web/public/results.json, which eval/report.py generates from
// eval/results.csv, eval/paired_results.csv, eval/field_results.csv, eval/field_guesses.csv and
// eval/interval_calibration.csv, eval/quantiphy_answers.csv (AGENTS.md rule 4: nothing typed). Pages that import this are
// prerendered. Server only: it uses node:fs. The CSV download routes still serve eval/ as is.
import { readFile } from "node:fs/promises";
import { cacheLife } from "next/cache";
import path from "node:path";
import type { AnswerRow } from "./holdout-finding";

export const EVAL_DIR = path.join(process.cwd(), "..", "eval");
export const RESULTS_JSON = path.join(process.cwd(), "public", "results.json");

export interface ResultRow {
  variant: string;
  split: string;
  mra_average: number | null;
  mra_S2: number | null;
  mra_D2: number | null;
  mra_S3: number | null;
  mra_D3: number | null;
  abstain_rate: number | null;
  share_within_10pct: number | null;
  share_off_2x: number | null;
  coverage: number | null;
  mra_answered: number | null;
  share_within_10pct_answered: number | null;
  share_off_2x_answered: number | null;
  n: number | null;
  cost_usd: number | null;
  run_date: string;
  source: string;
}

export interface PairedRow {
  variant: string;
  split: string;
  category: string;
  n_answered: number;
  mra_variant: number | null;
  mra_muse: number | null;
  within10_variant: number | null;
  within10_muse: number | null;
  off2x_variant: number | null;
  off2x_muse: number | null;
}

/** One row of eval/field_results.csv with Muse Spark alone's answer from field_guesses.csv. */
export interface FieldRow {
  clip_id: string;
  set: string;
  path: string;
  truth: number | null;
  pred: number | null;
  lo: number | null;
  hi: number | null;
  rel_error: number | null;
  covered: boolean | null;
  status: "measured" | "abstained";
  reason: string;
  audit_approve: boolean | null;
  unit: string;
  guess_pred: number | null;
  guess_rel_error: number | null;
}

/** eval/field.py summary() for one set. */
export interface FieldSetSummary {
  n: number;
  measured: number;
  abstained: number;
  median_rel_error: number | null;
  p90_rel_error: number | null;
  coverage: number | null;
  guess_n: number;
  guess_answered: number;
  guess_median_rel_error: number | null;
}

/** One row of eval/interval_calibration.csv (QuantiPhy dev split only). */
export interface CalibrationRow {
  variant: string;
  split: string;
  interval_log_term: number;
  answered: number;
  covered: number;
  coverage: number | null;
  newly_refused_interval_width: number;
  k_for_90pct: number | null;
  source: string;
}

export interface Benchmark {
  generated_utc: string;
  results: ResultRow[];
  paired: PairedRow[];
  field: FieldRow[];
  field_summary: Record<string, FieldSetSummary>;
  interval_calibration: CalibrationRow[];
  /** eval/quantiphy_answers.csv: one row per (variant, question) of the frozen runs. */
  answers: AnswerRow[];
  /** Post-hoc analysis rows (eval/hybrid_posthoc.py), kept apart from the variants. */
  posthoc?: ResultRow[];
}

/** Read once at build time and never revalidate: the deployed server need not have eval/. */
export function buildTimeOnly(): void {
  cacheLife({ stale: Infinity, revalidate: Infinity, expire: Infinity });
}

export async function readEvalFile(name: string): Promise<string> {
  return readFile(path.join(EVAL_DIR, name), "utf8");
}

export async function loadBenchmark(): Promise<Benchmark> {
  "use cache";
  buildTimeOnly();
  return JSON.parse(await readFile(RESULTS_JSON, "utf8")) as Benchmark;
}

// ---- Lookups and the findings both / and /results state ----

export function findRow(b: Benchmark, variant: string, split: string): ResultRow | null {
  return b.results.find((r) => r.variant === variant && r.split === split) ?? null;
}

export function findPaired(b: Benchmark, variant: string, split: string, category = "all") {
  return (
    b.paired.find((r) => r.variant === variant && r.split === split && r.category === category) ??
    null
  );
}

export const SPLIT_ORDER = ["holdout", "dev", "full", "dev_2d", "dev_3d"] as const;

export function splitsPresent(b: Benchmark): string[] {
  const s = new Set(b.results.map((r) => r.split));
  return [...SPLIT_ORDER.filter((x) => s.has(x)), ...[...s].filter((x) => !(SPLIT_ORDER as readonly string[]).includes(x))];
}

/** True when some Caliper variant has a row on this split. */
export function caliperOn(b: Benchmark, split: string): boolean {
  return b.results.some((r) => r.split === split && r.variant.startsWith("caliper"));
}

// ---- Field set (eval/field_results.csv through results.json) ----

/** Field sets in display order with what each one tests. */
export const FIELD_SETS = [
  { set: "scooter", label: "Set A (scooter)", what: "our scooter's speed against a GPS app, its taped length as the ruler" },
  { set: "speed", label: "Set A (car, first filming)", what: "car speed against a GPS app" },
  { set: "gravity", label: "Set B", what: "a dropped ball, acceleration against 9.81 m/s²" },
  { set: "size", label: "Set C", what: "object size against a tape measure" },
  { set: "none", label: "Set D", what: "no reference in view: should refuse" },
] as const;

/** Field sets whose truth is a GPS speed (m/s in the CSVs). */
export const SPEED_SETS = new Set(["speed", "scooter"]);

export function fieldRows(b: Benchmark, set: string, path = "measure"): FieldRow[] {
  return b.field.filter((r) => r.set === set && r.path === path);
}

export function calibration(b: Benchmark, variant: string, k0: boolean): CalibrationRow | null {
  return (
    b.interval_calibration.find(
      (r) => r.variant === variant && (k0 ? r.interval_log_term === 0 : r.interval_log_term > 0),
    ) ?? null
  );
}
