// node --test tests/*.test.mjs (Node strips the TypeScript types; no test framework needed)
import assert from "node:assert/strict";
import { test } from "node:test";
import { provenLine, reasonKey, scooterLine, topReason } from "../src/lib/proven.ts";

const clip = (set, status, reason = "") => ({ set, path: "measure", status, reason });

test("per-clip numbers are dropped from a reason", () => {
  assert.equal(reasonKey("The gray car is never fully inside the picture on enough frames (0 whole-object frames, 5 needed)."),
    "The gray car is never fully inside the picture on enough frames");
  assert.equal(reasonKey("The scale changes across the picture (perspective), so one ruler doesn't fit."),
    "The scale changes across the picture (perspective), so one ruler doesn't fit");
});

test("the most common reason is counted across clips", () => {
  const rows = [clip("speed", "abstained", "Never fully inside (0 frames, 5 needed)."),
    clip("speed", "abstained", "Never fully inside (3 frames, 5 needed)."), clip("speed", "abstained", "Two ways disagree.")];
  assert.deepEqual(topReason(rows, "speed"), { reason: "Never fully inside", count: 2, n: 3 });
});

test("hero subline: size proven, speed and drops refused with reasons", () => {
  const summary = {
    size: { n: 10, measured: 10, median_rel_error: 0.1068, coverage: 0.9 },
    speed: { n: 10, measured: 0, median_rel_error: null, coverage: null },
    gravity: { n: 10, measured: 0, median_rel_error: null, coverage: null },
  };
  const rows = [
    ...Array.from({ length: 9 }, () => clip("speed", "abstained", "Car never fully inside (0 frames, 5 needed).")),
    clip("speed", "abstained", "Two ways disagree."),
    ...Array.from({ length: 4 }, () => clip("gravity", "abstained", "Scale changes (perspective).")),
    ...Array.from({ length: 6 }, (_, i) => clip("gravity", "abstained", `Other reason ${i < 3 ? "a" : String.fromCharCode(98 + i)}.`)),
  ];
  const s = provenLine(summary, rows);
  assert.match(s, /^Proven on our own clips: size, 10 of 10 measured against a tape, median error 11%, truth inside the 90% range on 9 of 10\./);
  assert.match(s, /not yet measured on our own footage: all 10 of our first car-speed clips were refused \(most often "Car never fully inside", 9 of 10\)/);
  assert.match(s, /and all 10 of our drop clips were refused \(most often "Scale changes \(perspective\)", 4 of 10\)\.$/);
});

test("hero subline: a measured speed set is stated with its counts, refusals stay listed", () => {
  const summary = {
    size: { n: 10, measured: 10, median_rel_error: 0.1068, coverage: 0.9 },
    scooter: { n: 6, measured: 5, median_rel_error: 0.0706, coverage: 1.0 },
    speed: { n: 10, measured: 0, median_rel_error: null, coverage: null },
    gravity: { n: 10, measured: 0, median_rel_error: null, coverage: null },
  };
  const rows = [
    ...Array.from({ length: 10 }, () => clip("speed", "abstained", "Car never fully inside (0 frames, 5 needed).")),
    ...Array.from({ length: 10 }, () => clip("gravity", "abstained", "Scale changes (perspective).")),
    clip("scooter", "abstained", "Two ways disagree."),
  ];
  const s = provenLine(summary, rows);
  assert.match(s, /Speed on our own footage: our scooter passes, 5 of 6 measured against GPS, median error 7%, GPS inside the 90% range on 5 of 5\./);
  assert.match(s, /Refused on our own footage: all 10 of our first car-speed clips were refused \(most often "Car never fully inside", 10 of 10\), and all 10 of our drop clips were refused/);
  assert.doesNotMatch(s, /not yet measured/);
});

test("scooter line reads its counts from the summary", () => {
  const f = scooterLine({ n: 6, measured: 5, median_rel_error: 0.0706, coverage: 1.0, guess_median_rel_error: 0.2971 });
  assert.equal(f.title, "6 passes of our own scooter against GPS");
  assert.equal(f.body, "Caliper measured 5 of the 6 passes: median error 7%, GPS inside its 90% range on 5 of 5; it refused 1, with its reason. Muse Spark alone, given the same length, was off by a median 30%, with no range.");
});

import { gateLine, gateSummary, gpsDisagreeNote } from "../src/lib/proven.ts";

const kmh = (v) => v / 3.6;
const study = (clip_id, pred, lo, hi, truth, covered) =>
  ({ clip_id, set: "scooter", path: "study", status: "measured", pred: kmh(pred), lo: kmh(lo), hi: kmh(hi), truth: kmh(truth), covered });

test("gate summary reads error, coverage and range width from the rows", () => {
  const rows = [study("A11", 31.2, 30.8, 31.8, 20, false), study("A12", 31.2, 30.7, 31.6, 32, false), study("A14", 42.6, 41.9, 43.5, 42, true)];
  const s = gateSummary(rows, "scooter");
  assert.equal(s.measured, 3);
  assert.equal(s.covered, 1);
  assert.ok(Math.abs(s.medianErrKmh - 0.8) < 1e-9);
  const line = gateLine(rows, "scooter", 7.92);
  assert.match(line, /^The gate method \(two gate lines 7\.92 m apart on the riding line\) timed 3 of 3 passes, median error 0\.8 km\/h\./);
  assert.match(line, /covers only frame timing, gate placement and the tape tolerance \(about ±1\.\d% to 1\.\d%\), so GPS falls inside it on 1 of 3\.$/);
});

test("GPS disagreement note lists each pass with both readings against GPS", () => {
  const meas = (clip_id, pred, truth) => ({ clip_id, set: "scooter", path: "measure", status: "measured", pred: kmh(pred), lo: null, hi: null, truth: kmh(truth), covered: true });
  const rows = [meas("A11", 29.4, 20), study("A11", 31.2, 30.8, 31.8, 20, false), meas("A15", 34.1, 45), study("A15", 35.2, 34.6, 35.7, 45, false)];
  assert.equal(gpsDisagreeNote(rows, ["A11", "A15"]),
    "On 2 passes Caliper and the gate method agree with each other but not with GPS (A11: 29.4 and 31.2 km/h against GPS 20.0; A15: 34.1 and 35.2 km/h against GPS 45.0), possibly GPS error. Observation only: the GPS readings stay as recorded.");
});

import { h5Line } from "../src/lib/proven.ts";

test("H5 verdict follows the protocol's thresholds", () => {
  const mk = (errs, cov) => errs.map((e, i) => study(`P${i}`, 40 + e, 39 + e, 41 + e, 40, i < cov));
  assert.match(h5Line(mk([0.6, 0.8, 0.9, 6.7, 9.8, 11.2], 1), "scooter"), /3\.8 km\/h and 1 of 6, not met \(not disproved/);
  assert.match(h5Line(mk([1, 2, 2, 3], 4), "scooter"), /, met\.$/);
  assert.match(h5Line(mk([7, 8, 9], 0), "scooter"), /, disproved\.$/);
});
