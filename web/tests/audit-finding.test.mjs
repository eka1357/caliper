// node --test tests/ (Node strips the TypeScript types; no test framework needed)
import assert from "node:assert/strict";
import { test } from "node:test";
import { auditFinding } from "../src/lib/audit-finding.ts";

test("equal rows get their own sentence, not 'from X to X'", () => {
  const row = { coverage: 9 / 42, n: 42, mra_answered: 0.9333 };
  const f = auditFinding(row, { ...row });
  assert.equal(f.title, "The audit changed nothing on dev");
  assert.match(f.body, /vetoed none/);
  assert.doesNotMatch(f.body, /from .* to /);
});

test("fewer answers at higher accuracy is a trade", () => {
  const f = auditFinding({ coverage: 11 / 89, n: 89, mra_answered: 0.9 }, { coverage: 10 / 89, n: 89, mra_answered: 0.92 });
  assert.equal(f.title, "The audit trades coverage for accuracy");
  assert.match(f.body, /vetoes 1 answer\./);
  assert.match(f.body, /answers 10 of 89 dev questions at answered-only MRA 92\.0; with the audit off it answers 11 at 90\.0/);
});

test("fewer answers without a gain says so", () => {
  const f = auditFinding({ coverage: 0.2, n: 50, mra_answered: 0.9 }, { coverage: 0.1, n: 50, mra_answered: 0.85 });
  assert.equal(f.title, "The audit costs coverage without gaining accuracy");
});

import { dimsFinding } from "../src/lib/audit-finding.ts";

test("3D tie on one answer is not called worse", () => {
  const f = dimsFinding({ n_answered: 9, mra_variant: 0.9333, mra_muse: 0.6667 }, { n_answered: 1, mra_variant: 0.8, mra_muse: 0.8 });
  assert.equal(f.title, "2D works; 3D is barely answered yet");
  assert.match(f.body, /On dev 3D questions they tie with it \(80\.0 against 80\.0, 1 question\)/);
  assert.doesNotMatch(f.body, /worse/);
});

test("3D behind with enough answers keeps the limit title", () => {
  const f = dimsFinding({ n_answered: 9, mra_variant: 0.93, mra_muse: 0.66 }, { n_answered: 5, mra_variant: 0.5, mra_muse: 0.7 });
  assert.equal(f.title, "2D works, 3D does not yet");
  assert.match(f.body, /they trail it/);
});
