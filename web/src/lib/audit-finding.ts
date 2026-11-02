// The "what the audit changes" finding, from the two dev rows of eval/results.csv (through
// results.json). No imports, so tests/audit-finding.test.mjs can run it with node --test.

export interface AuditRow {
  coverage: number | null; // share of questions answered
  n: number | null;
  mra_answered: number | null; // 0 to 1
}

const mra = (v: number) => (v * 100).toFixed(1);

/** Title and sentence comparing Caliper with the audit (as shipped) against the audit off. */
export function auditFinding(off: AuditRow, on: AuditRow): { title: string; body: string } | null {
  if (off.coverage == null || on.coverage == null || off.n == null || on.n == null) return null;
  if (off.mra_answered == null || on.mra_answered == null) return null;
  const a0 = Math.round(off.coverage * off.n);
  const a1 = Math.round(on.coverage * on.n);
  const m0 = mra(off.mra_answered);
  const m1 = mra(on.mra_answered);
  const vetoed = a0 - a1;
  if (vetoed === 0 && m0 === m1) {
    return {
      title: "The audit changed nothing on dev",
      body: `On the dev split the visual audit vetoed none of the answers: with and without it Caliper answers ${a1} of ${on.n} questions, at answered-only MRA ${m1}.`,
    };
  }
  const base = `Caliper with the audit answers ${a1} of ${on.n} dev questions at answered-only MRA ${m1}; with the audit off it answers ${a0} at ${m0}.`;
  if (vetoed > 0 && Number(m1) > Number(m0)) {
    return {
      title: "The audit trades coverage for accuracy",
      body: `On the dev split (all four categories) the visual audit vetoes ${vetoed} answer${vetoed === 1 ? "" : "s"}. ${base} The samples are small.`,
    };
  }
  if (vetoed > 0) {
    return {
      title: "The audit costs coverage without gaining accuracy",
      body: `On the dev split the visual audit vetoes ${vetoed} answer${vetoed === 1 ? "" : "s"} but does not raise accuracy. ${base}`,
    };
  }
  return { title: "What the audit changes", body: `On the dev split: ${base}` };
}

export interface PairedMra {
  n_answered: number;
  mra_variant: number | null; // Caliper on the questions it answered
  mra_muse: number | null; // Muse Spark alone on the same questions
}

/** 2D against 3D, Caliper (with the audit) against Muse Spark alone on the same questions. */
export function dimsFinding(p2: PairedMra, p3: PairedMra, split = "dev"): { title: string; body: string } | null {
  if (p2.mra_variant == null || p2.mra_muse == null || p3.mra_variant == null || p3.mra_muse == null) return null;
  const cmp = (a: number, b: number) => (mra(a) === mra(b) ? "same" : a > b ? "better" : "worse");
  const c2 = cmp(p2.mra_variant, p2.mra_muse);
  const c3 = cmp(p3.mra_variant, p3.mra_muse);
  const pair = (p: PairedMra) => `${mra(p.mra_variant!)} against ${mra(p.mra_muse!)}, ${p.n_answered} question${p.n_answered === 1 ? "" : "s"}`;
  const word = { better: "beat", same: "tie with", worse: "trail" } as const;
  const body = `On ${split} 2D questions Caliper's answers ${word[c2]} the model alone (${pair(p2)}). On ${split} 3D questions they ${word[c3]} it (${pair(p3)}).`;
  const few = p3.n_answered < 3;
  const title =
    c2 === "better" && c3 === "better" ? "Closer than the model in 2D and 3D"
    : c2 === "better" && few ? "2D works; 3D is barely answered yet"
    : c2 === "better" ? "2D works, 3D does not yet"
    : "Not closer than the model yet";
  return { title, body: few ? `${body} Too few 3D answers to judge.` : body };
}
