// node --test tests/*.test.mjs (Node strips the TypeScript types; no test framework needed)
import assert from "node:assert/strict";
import { test } from "node:test";
import { h1Finding, heroClaim, intervalCover, posthocFinding, vetoFinding } from "../src/lib/holdout-finding.ts";

const a = (variant, split, row_id, status, rel_error, covered, audit_approve = null) =>
  ({ variant, split, row_id, status, rel_error, covered, audit_approve });

test("hero claim reads its numbers from the rows (and the full set when given)", () => {
  const s = heroClaim({ n: 69, coverage: 15 / 69, mra_average: 0.2 },
    { n_answered: 15, within10_variant: 0.6, within10_muse: 0.2667, off2x_variant: 0.0667, off2x_muse: 0.2 },
    { covered: 13, answered: 15 });
  assert.match(s, /^On holdout \(videos never used for tuning\), Caliper answers about 1 question in 5 \(15 of 69\)\. When it answers on holdout, /);
  assert.match(s, /60% \(9 of 15\) of its answers are within 10%, against 27% \(4 of 15\)/);
  assert.match(s, /7% \(1 of 15\) are off by more than 2x, against 20% \(3 of 15\)/);
  assert.match(s, /held on 13 of 15\./);
  const withFull = heroClaim({ n: 69, coverage: 15 / 69, mra_average: 0.2 },
    { n_answered: 15, within10_variant: 0.6, within10_muse: 0.2667, off2x_variant: 0.0667, off2x_muse: 0.2 },
    { covered: 13, answered: 15 }, { n: 158, coverage: 25 / 158, mra_average: 0.15 });
  assert.match(withFull, /about 1 question in 5 \(15 of 69\); on the full set, 25 of 158\./);
});

test("H1 fails when Caliper is not 10 points above", () => {
  const f = h1Finding({ n: 69, coverage: 15 / 69, mra_average: 0.2011 }, { n: 69, coverage: 0.97, mra_average: 0.5809 });
  assert.equal(f.title, "Claim H1 failed on holdout");
  assert.match(f.body, /It did not: 20\.1 against 58\.1\./);
  assert.match(f.body, /answers 15 of 69 holdout questions/);
});

test("vetoes of a correct and an in-range answer have not caught a wrong one", () => {
  const rows = [
    a("caliper", "holdout", 1, "abstained", null, null, false),
    a("caliper_no_audit", "holdout", 1, "measured", 0.0154, true),
    a("caliper", "dev", 2, "abstained", null, null, false),
    a("caliper_no_audit", "dev", 2, "measured", 0.2222, true),
    a("caliper", "dev", 3, "abstained", null, null, null), // refused by a check, not the audit
    a("caliper_no_audit", "dev", 3, "abstained", null, null),
  ];
  const f = vetoFinding(rows);
  assert.equal(f.title, "The audit is a cautious check: both its vetoes were false alarms");
  assert.match(f.body, /false alarms: each cost an answer, and a veto can never change a number\. It ships as is/);
  assert.match(f.body, /^On holdout it vetoed one that was correct \(1\.5% error\); on dev it vetoed one whose truth was inside its 90% range \(22\.2% error\)\./);
});

test("a veto of an out-of-range answer counts as caught", () => {
  const f = vetoFinding([a("caliper", "dev", 1, "abstained", null, null, false), a("caliper_no_audit", "dev", 1, "measured", 1.5, false)]);
  assert.equal(f.title, "The audit caught 1 wrong answer");
});

test("interval coverage counts answered rows only", () => {
  const rows = [a("caliper", "holdout", 1, "measured", 0.1, true), a("caliper", "holdout", 2, "measured", 0.9, false),
    a("caliper", "holdout", 3, "abstained", null, null), a("caliper", "dev", 4, "measured", 0.1, true)];
  assert.deepEqual(intervalCover(rows, "caliper", "holdout"), { covered: 1, answered: 2 });
});

test("post-hoc finding is labelled and compares with both rows", () => {
  const f = posthocFinding({ n: 69, coverage: 0.99, mra_average: 0.6171 }, { n: 69, coverage: 0.97, mra_average: 0.5809 },
    { n: 69, coverage: 0.22, mra_average: 0.2011 });
  assert.match(f.title, /^Post-hoc:/);
  assert.match(f.body, /defined after the holdout run, with no parameters, and not part of Caliper/);
  assert.match(f.body, /scores 61\.7 official MRA, 3\.6 points above Muse Spark alone \(58\.1\); Caliper on its own scores 20\.1\./);
  assert.match(f.body, /never returns a guess/);
});
