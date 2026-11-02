// The findings stated on / and /results, written as templates over the benchmark rows. A
// finding whose rows are missing is left out rather than filled with a typed number.
import { auditFinding, dimsFinding } from "./audit-finding";
import { fmtMra, fmtPct } from "./labels";
import { type Benchmark, caliperOn, findPaired, findRow } from "./results";

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

  const museDev = findRow(b, "muse_spark_alone", "dev");
  const calDev = findRow(b, "caliper", "dev"); // with the audit: the product as shipped
  if (museDev && calDev && calDev.n != null && calDev.coverage != null) {
    out.push({
      id: "coverage",
      title: "Caliper answers far fewer questions",
      body: `On the dev split Caliper answers ${Math.round(calDev.coverage * calDev.n)} of ${calDev.n} questions (${fmtPct(calDev.coverage)}) and abstains on the rest. The official score counts every abstention as a miss, so its MRA is ${fmtMra(calDev.mra_average)} against ${fmtMra(museDev.mra_average)} for the model alone.`,
      kind: "limit",
      source: SRC_R,
    });
  }

  const pDev = findPaired(b, "caliper", "dev");
  if (pDev && pDev.n_answered > 0) {
    out.push({
      id: "answered",
      title: "When it answers, it is closer",
      body: `On the ${pDev.n_answered} dev questions Caliper answered, its MRA is ${fmtMra(pDev.mra_variant)} against ${fmtMra(pDev.mra_muse)} for Muse Spark alone on the same questions; ${fmtPct(pDev.within10_variant)} of its answers are within 10% against ${fmtPct(pDev.within10_muse)}.`,
      kind: "finding",
      source: SRC_P,
    });
  }

  const p2 = findPaired(b, "caliper", "dev_2d");
  const p3 = findPaired(b, "caliper", "dev_3d");
  const dims = p2 && p3 && p2.n_answered > 0 && p3.n_answered > 0 ? dimsFinding(p2, p3) : null;
  if (dims) out.push({ id: "dims", ...dims, kind: "limit", source: SRC_P });

  const onDev = findRow(b, "caliper", "dev");
  const offDev = findRow(b, "caliper_no_audit", "dev");
  const audit = onDev && offDev ? auditFinding(offDev, onDev) : null;
  if (audit) out.push({ id: "audit", ...audit, kind: "finding", source: SRC_R });

  if (!caliperOn(b, "holdout")) {
    out.push({
      id: "holdout",
      title: "No holdout result yet",
      body: "Caliper has not been scored on the holdout split, so every Caliper number here comes from the dev split that was used for tuning. Whether Caliper beats the model on unseen videos (claim H1) is still open.",
      kind: "limit",
      source: SRC_R,
    });
  }

  return out;
}
