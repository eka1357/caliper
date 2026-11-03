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
