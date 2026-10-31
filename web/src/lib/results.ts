// Build-time reader for the benchmark files. The only sources are eval/results.csv and
// eval/paired_results.csv (AGENTS.md rule 4). Pages that import this are prerendered, so the
// deployed site carries the numbers without shipping eval/. Server only: it uses node:fs.
import { readFile } from "node:fs/promises";
import { cacheLife } from "next/cache";
import path from "node:path";

export const EVAL_DIR = path.join(process.cwd(), "..", "eval");
export const RESULTS_CSV = "results.csv";
export const PAIRED_CSV = "paired_results.csv";

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

export interface Benchmark {
  results: ResultRow[];
  paired: PairedRow[];
}

/** RFC 4180 style: commas, double quotes, "" escapes. Enough for our own CSVs. */
export function parseCsv(text: string): Record<string, string>[] {
  const rows: string[][] = [];
  let row: string[] = [];
  let cell = "";
  let quoted = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (quoted) {
      if (c === '"' && text[i + 1] === '"') {
        cell += '"';
        i++;
      } else if (c === '"') quoted = false;
      else cell += c;
    } else if (c === '"') quoted = true;
    else if (c === ",") {
      row.push(cell);
      cell = "";
    } else if (c === "\n" || c === "\r") {
      if (c === "\r" && text[i + 1] === "\n") i++;
      row.push(cell);
      cell = "";
      if (row.some((v) => v !== "")) rows.push(row);
      row = [];
    } else cell += c;
  }
  row.push(cell);
  if (row.some((v) => v !== "")) rows.push(row);
  const [header, ...body] = rows;
  if (!header) return [];
  return body.map((r) => Object.fromEntries(header.map((h, i) => [h, r[i] ?? ""])));
}

function num(v: string | undefined): number | null {
  if (v == null || v === "" || v.toLowerCase() === "nan") return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

const RESULT_NUMERIC = [
  "mra_average", "mra_S2", "mra_D2", "mra_S3", "mra_D3", "abstain_rate", "share_within_10pct",
  "share_off_2x", "coverage", "mra_answered", "share_within_10pct_answered",
  "share_off_2x_answered", "n", "cost_usd",
] as const;

const PAIRED_NUMERIC = [
  "mra_variant", "mra_muse", "within10_variant", "within10_muse", "off2x_variant", "off2x_muse",
] as const;

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
  const [r, p] = await Promise.all([readEvalFile(RESULTS_CSV), readEvalFile(PAIRED_CSV)]);
  const results = parseCsv(r).map((row) => {
    const out: Record<string, unknown> = { ...row };
    for (const k of RESULT_NUMERIC) out[k] = num(row[k]);
    return out as unknown as ResultRow;
  });
  const paired = parseCsv(p).map((row) => {
    const out: Record<string, unknown> = { ...row };
    for (const k of PAIRED_NUMERIC) out[k] = num(row[k]);
    out.n_answered = num(row.n_answered) ?? 0;
    return out as unknown as PairedRow;
  });
  return { results, paired };
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
