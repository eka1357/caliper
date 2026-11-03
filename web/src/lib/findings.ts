// The findings stated on / and /results, written as templates over the benchmark rows. A
// finding whose rows are missing is left out rather than filled with a typed number.
import { dimsFinding } from "./audit-finding";
import { h1Finding, heroClaim, intervalCover, posthocFinding, shareOf, vetoFinding } from "./holdout-finding";
import { fmtMra } from "./labels";
import { type Benchmark, findPaired, findRow } from "./results";

export interface Finding {
  id: string;
  title: string;
  body: string;
  /** "limit" findings are the honest caveats; they are styled like the rest, never hidden. */
  kind: "finding" | "limit";
  source: string;
}

const SRC_R = "eval/results.csv";
const SRC_P = "eval/paired_results.csv";
const SRC_A = "eval/quantiphy_answers.csv";
const pctOf = (v: number | null, n: number) => (v == null ? "n/a" : shareOf(v, n));

export function findings(b: Benchmark): Finding[] {
  const out: Finding[] = [];

  const museFull = findRow(b, "muse_spark_alone", "full");
  const museHold = findRow(b, "muse_spark_alone", "holdout");
  if (museFull && museHold) {
    out.push({
      id: "baseline",
      title: "The model alone",
      body: `Muse Spark 1.3 answering from the video alone scores ${fmtMra(museFull.mra_average)} MRA on all ${museFull.n} QuantiPhy validation questions and ${fmtMra(museHold.mra_average)} on the holdout split.`,
      kind: "finding",
      source: SRC_R,
    });
  }

  // Holdout first (EVAL_PROTOCOL section 2): Caliper as shipped, with the audit.
  const calHold = findRow(b, "caliper", "holdout");
  const pHold = findPaired(b, "caliper", "holdout");
  const pDev = findPaired(b, "caliper", "dev");
  if (pHold && pHold.n_answered > 0) {
    const dev = pDev && pDev.n_answered > 0
      ? ` On the dev split, which was used for tuning: ${fmtMra(pDev.mra_variant)} against ${fmtMra(pDev.mra_muse)} on ${pDev.n_answered} answered.`
      : "";
    out.push({
      id: "answered",
      title: "When it answers, it is closer",
      body: `On the ${pHold.n_answered} holdout questions Caliper answered, its MRA is ${fmtMra(pHold.mra_variant)} against ${fmtMra(pHold.mra_muse)} for Muse Spark alone on the same questions; ${pctOf(pHold.within10_variant, pHold.n_answered)} of its answers are within 10% against ${pctOf(pHold.within10_muse, pHold.n_answered)}, and ${pctOf(pHold.off2x_variant, pHold.n_answered)} are off by more than 2x against ${pctOf(pHold.off2x_muse, pHold.n_answered)}.${dev}`,
      kind: "finding",
      source: SRC_P,
    });
  }

  const h1 = calHold && museHold ? h1Finding(calHold, museHold) : null;
  if (h1) out.push({ id: "h1", ...h1, kind: "limit", source: SRC_R });

  const hybrid = (b.posthoc ?? []).find((r) => r.variant === "hybrid_posthoc" && r.split === "holdout");
  const post = hybrid && calHold && museHold ? posthocFinding(hybrid, museHold, calHold) : null;
  if (post) out.push({ id: "posthoc", ...post, kind: "limit", source: "eval/results.csv (post-hoc row)" });

  const veto = vetoFinding(b.answers ?? []);
  if (veto) out.push({ id: "audit", ...veto, kind: "limit", source: SRC_A });

  const p2 = findPaired(b, "caliper", "dev_2d");
  const p3 = findPaired(b, "caliper", "dev_3d");
  const dims = p2 && p3 && p2.n_answered > 0 && p3.n_answered > 0 ? dimsFinding(p2, p3, "dev") : null;
  if (dims) out.push({ id: "dims", ...dims, kind: "limit", source: SRC_P });

  return out;
}

/** The landing hero's claim: holdout, Caliper with the audit. Null when a row is missing. */
export function heroLine(b: Benchmark): string | null {
  const row = findRow(b, "caliper", "holdout");
  const p = findPaired(b, "caliper", "holdout");
  if (!row || !p) return null;
  return heroClaim(row, p, intervalCover(b.answers ?? [], "caliper", "holdout"));
}
