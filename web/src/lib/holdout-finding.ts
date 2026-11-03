// Holdout sentences (the headline split, EVAL_PROTOCOL section 2), built from rows of
// web/public/results.json. No imports, so tests/holdout-finding.test.mjs runs them with node --test.
// MRA is shown on QuantiPhy's 0 to 100 scale, like the rest of the site.

export interface AnswerRow {
  variant: string;
  split: string;
  row_id: number;
  status: "measured" | "abstained";
  rel_error: number | null;
  covered: boolean | null;
  audit_approve: boolean | null;
}

export interface PairedShares {
  n_answered: number;
  within10_variant: number | null;
  within10_muse: number | null;
  off2x_variant: number | null;
  off2x_muse: number | null;
}

export interface SplitRow {
  n: number | null;
  coverage: number | null;
  mra_average: number | null;
}

const pct = (v: number) => `${Math.round(v * 100)}%`;
/** A share with its count beside it, e.g. "60% (9 of 15)". */
export const shareOf = (v: number, n: number) => `${pct(v)} (${Math.round(v * n)} of ${n})`;
const mra = (v: number) => (v * 100).toFixed(1);
const err = (v: number) => `${(v * 100).toFixed(1)}% error`;

/** Answered questions of one variant and split whose 90% range contains the truth. */
export function intervalCover(answers: AnswerRow[], variant: string, split: string) {
  const a = answers.filter((r) => r.variant === variant && r.split === split && r.status === "measured" && r.covered != null);
  return { covered: a.filter((r) => r.covered).length, answered: a.length };
}

/** The hero claim: holdout, Caliper as shipped (with the audit). */
export function heroClaim(row: SplitRow, p: PairedShares, cover: { covered: number; answered: number }): string | null {
  if (!row.coverage || p.within10_variant == null || p.within10_muse == null) return null;
  if (p.off2x_variant == null || p.off2x_muse == null || cover.answered === 0) return null;
  const oneIn = Math.round(1 / row.coverage);
  const n = p.n_answered;
  return (
    `Caliper answers about 1 question in ${oneIn}. When it answers, on unseen videos (QuantiPhy holdout) ` +
    `${shareOf(p.within10_variant, n)} of its answers are within 10%, against ${shareOf(p.within10_muse, n)} for Muse Spark alone ` +
    `on the same questions; ${shareOf(p.off2x_variant, n)} are off by more than 2x, against ${shareOf(p.off2x_muse, n)}; ` +
    `and its 90% range held on ${cover.covered} of ${cover.answered}.`
  );
}

/** Claim H1 (EVAL_PROTOCOL section 1) on the official score, refusals counted as misses. */
export function h1Finding(cal: SplitRow, muse: SplitRow): { title: string; body: string } | null {
  if (cal.mra_average == null || muse.mra_average == null || cal.n == null || cal.coverage == null) return null;
  const held = cal.mra_average - muse.mra_average >= 0.1;
  const answered = Math.round(cal.coverage * cal.n);
  return {
    title: held ? "Claim H1 held on holdout" : "Claim H1 failed on holdout",
    body:
      `We pre-registered that Caliper would beat Muse Spark alone by at least 10 points of official MRA on the holdout split. ` +
      `${held ? "It did" : "It did not"}: ${mra(cal.mra_average)} against ${mra(muse.mra_average)}. ` +
      `The official score counts every refusal as a miss, and Caliper answers ${answered} of ${cal.n} holdout questions.`,
  };
}

/**
 * Audit vetoes: questions Caliper (with the audit) refused after the audit said no, where the
 * same pipeline without the audit answered. "Wrong" means the truth lay outside that answer's
 * 90% range; "correct" means within 10%.
 */
export function vetoFinding(answers: AnswerRow[]): { title: string; body: string } | null {
  const off = new Map(answers.filter((r) => r.variant === "caliper_no_audit").map((r) => [r.row_id, r]));
  const vetoes = answers
    .filter((r) => r.variant === "caliper" && r.status === "abstained" && r.audit_approve === false)
    .map((r) => off.get(r.row_id))
    .filter((r): r is AnswerRow => r != null && r.status === "measured" && r.rel_error != null);
  if (vetoes.length === 0) return null;
  const describe = (r: AnswerRow) =>
    r.rel_error! < 0.1 ? `one that was correct (${err(r.rel_error!)})`
    : r.covered ? `one whose truth was inside its 90% range (${err(r.rel_error!)})`
    : `one that was wrong, truth outside its 90% range (${err(r.rel_error!)})`;
  const parts = ["holdout", "dev"].flatMap((split) => {
    const v = vetoes.filter((r) => r.split === split);
    return v.length ? [`on ${split} it vetoed ${v.map(describe).join(" and ")}`] : [];
  });
  const caught = vetoes.filter((r) => r.covered === false).length;
  const sentence = parts.join("; ");
  return {
    title: caught
      ? `The audit caught ${caught} wrong answer${caught === 1 ? "" : "s"}`
      : `The audit is a cautious check: ${vetoes.length === 1 ? "its one veto was a false alarm" : vetoes.length === 2 ? "both its vetoes were false alarms" : `all ${vetoes.length} of its vetoes were false alarms`}`,
    body:
      `${sentence[0].toUpperCase()}${sentence.slice(1)}. ` +
      (caught
        ? `${caught} of the ${vetoes.length} answers it vetoed had the truth outside their range.`
        : `${vetoes.length === 1 ? "The answer it vetoed was not wrong" : vetoes.length === 2 ? "Neither answer it vetoed was wrong" : "None of the answers it vetoed was wrong"}, so these were false alarms: each cost an answer, and a veto can never change a number.`) +
      " It ships as is, as frozen before the holdout run.",
  };
}

/**
 * The post-hoc analysis row (eval/hybrid_posthoc.py): Caliper where it answered, Muse Spark
 * alone where it refused. Defined after the holdout run and not a Caliper variant; the product
 * never returns a guess (EVAL_PROTOCOL 4a, AGENTS rule 1).
 */
export function posthocFinding(hybrid: SplitRow, muse: SplitRow, cal: SplitRow): { title: string; body: string } | null {
  if (hybrid.mra_average == null || muse.mra_average == null || cal.mra_average == null) return null;
  const diff = hybrid.mra_average - muse.mra_average;
  const rel = mra(Math.abs(diff)) === "0.0" ? "the same as" : diff > 0 ? `${mra(diff)} points above` : `${mra(-diff)} points below`;
  return {
    title: "Post-hoc: what if a refusal fell back to the model's guess?",
    body:
      `An analysis we defined after the holdout run, with no parameters, and not part of Caliper: take Caliper's answer where it answered and Muse Spark alone's guess where it refused. ` +
      `On holdout that scores ${mra(hybrid.mra_average)} official MRA, ${rel} Muse Spark alone (${mra(muse.mra_average)}); Caliper on its own scores ${mra(cal.mra_average)}. ` +
      `Caliper itself never returns a guess.`,
  };
}
