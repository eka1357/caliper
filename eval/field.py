"""Caliper on the field set: measure path on Sets B, C and D, plus Muse Spark alone's answer on
every measurement clip (Sets A to D). Writes eval/field_results.csv (EVAL_PROTOCOL section 5).

Set A normally runs only through the study path (DECISIONS 2026-11-01). As filmed, its markers
stand on the far kerb while the car drives in the near lane, so they cannot set the scale.
--measure-speed runs the measure path on Set A with the vehicle as its own reference (truth.csv
`measure_prior`, e.g. the car's length) and
only the frames where the whole car is in the picture (DECISIONS 2026-11-02). Each clip's
reference from
truth.csv is passed as the prior, the sentence a user types in "I know one real size"; Set D gets
none. Muse Spark alone gets exactly the same question and prior.

Usage: backend/.venv/Scripts/python.exe eval/field.py [--max-spend 9.0] [--clips B01 C02]
       [--measure-speed]
Every API response is cached, so a rerun costs $0. Real spend is metered from the new cache
records each clip creates; the run stops before a clip whose worst case would pass --max-spend.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from caliper import checks, config, engine, guess, pipeline  # noqa: E402
from caliper.meta_client import muse_cost_usd  # noqa: E402
from caliper.models import Result  # noqa: E402
from caliper.normalize import normalize, probe  # noqa: E402

log = logging.getLogger("field")
FIELD = ROOT / "data" / "field"
TRUTH = FIELD / "truth.csv"
OUT = ROOT / "eval" / "field_results.csv"
GUESSES = ROOT / "eval" / "field_guesses.csv"
RUNS = config.CACHE_DIR / "field_runs"  # full Result + guess per clip (gitignored)
MEASURE_SETS = ("gravity", "size", "none")
GUESS_SETS = ("speed", "scooter", "gravity", "size", "none")
# Speed sets: the vehicle is its own reference on the measure path (--measure-speed). Set A as first
# filmed (car, A01-A10) and Set A (scooter, A11-A16, filmed 2026-11-03), DECISIONS 2026-11-03.
SPEED_SETS = ("speed", "scooter")
COLUMNS = [
    "clip_id",
    "set",
    "path",
    "truth",
    "pred",
    "lo",
    "hi",
    "rel_error",
    "covered",
    "status",
    "reason",
    "audit_approve",
    "unit",
]  # EVAL_PROTOCOL 5 columns, then the unit of truth/pred/lo/hi
GUESS_COLUMNS = ["clip_id", "set", "truth", "unit", "guess_pred", "guess_rel_error", "guess_text"]

# How each reference in truth.csv is said in words; the size comes from reference_size_m.
PRIOR_TEMPLATES = {
    "A4 sheet long side": "The A4 sheet's long side is {m} m.",
    "INR 10 coin": "The INR 10 coin is {m} m in diameter.",
    "two markers 10.0 m apart": "The two markers are {m} m apart.",
}


def prior_text(row: dict[str, str], car_reference: bool = False) -> str | None:
    """The prior sentence for one clip. With car_reference (--measure-speed), a Set A clip gets its
    truth.csv `measure_prior`: the vehicle as its own reference, e.g. "The car is 3.995 m long."
    (DECISIONS 2026-11-02) or "The motorcycle is X m long." for a bike clip."""
    if car_reference and row["set"] in SPEED_SETS:
        prior = (row.get("measure_prior") or "").strip()
        if not prior:
            raise ValueError(f"no measure_prior in truth.csv for {row['clip_id']}")
        return prior
    ref = row["reference_object"].strip()
    if ref in ("", "none"):
        return None
    if ref not in PRIOR_TEMPLATES:
        raise ValueError(f"no wording for reference {ref!r} ({row['clip_id']})")
    return PRIOR_TEMPLATES[ref].format(m=row["reference_size_m"])


def to_si(value: float, unit: str) -> float:
    return value / engine.to_unit(1.0, unit)


def convert(value: float, src: str, dst: str) -> float:
    return engine.to_unit(to_si(value, src), dst)


def rel_error(pred: float | None, truth: float | None) -> float | None:
    if pred is None or truth is None or truth == 0:
        return None
    return abs(pred - truth) / abs(truth)


class SpendMeter:
    """Real spend = cost of cache records created during this run (cache hits cost nothing)."""

    def __init__(self) -> None:
        self.root = config.CACHE_DIR / "api"
        self.seen = set(self.root.glob("*/*.json"))
        self.total = 0.0

    def settle(self, frames: int) -> float:
        new = set(self.root.glob("*/*.json")) - self.seen
        self.seen |= new
        cost = 0.0
        for p in new:
            rec = json.loads(p.read_text(encoding="utf-8"))
            if rec["kind"] == "responses":
                cost += muse_cost_usd(rec["usage"])
            elif rec["kind"] == "sam":
                cost += frames * config.SAM_USD_PER_FRAME  # every SAM request bills all frames
        self.total += cost
        return cost


def worst_case(frames: int, measure: bool) -> float:
    """Upper bound for one clip: 3 phrases each for target and reference, spec, audit, guess."""
    muse_max = 0.0309 * 1.5  # max cost per Responses call in the cache (cost_summary), +50%
    sam = frames * 6 * config.SAM_USD_PER_FRAME if measure else 0.0
    return sam + (3 if measure else 1) * muse_max


def run_clip(row: dict[str, str], measure_sets: tuple[str, ...] = MEASURE_SETS) -> dict:
    src = FIELD / row["file"]
    video = normalize(src)  # the pipeline normalizes src itself; guess() takes the normalized copy
    car = any(s in measure_sets for s in SPEED_SETS)
    prior = prior_text(row, car_reference=car)
    rec: dict = {
        "clip_id": row["clip_id"],
        "prior": prior,
        "video": video.name,
        "interval_log_term": config.INTERVAL_LOG_TERM,
    }
    if row["set"] in measure_sets:
        res = pipeline.measure(
            src, row["question"], prior, run_id=f"field-{row['clip_id']}", audit=True,
            with_overlay=True, whole_object_only=car and row["set"] in SPEED_SETS,
        )  # fmt: skip
        rec["result"] = json.loads(res.model_dump_json())
    out, info = guess.guess(video, row["question"], prior=prior)
    rec["guess"] = {**out, "cost_usd": info.get("cost_usd")}
    return rec


def guess_row(row: dict[str, str], rec: dict) -> dict:
    truth = float(row["true_value"]) if row["true_value"] else None
    g = rec["guess"].get("parsed_value")  # Muse Spark alone answers in the unit the question asks
    return {"clip_id": row["clip_id"], "set": row["set"], "truth": truth, "unit": row["unit"],
            "guess_pred": g, "guess_rel_error": rel_error(g, truth),
            "guess_text": rec["guess"].get("text", "")}  # fmt: skip


def result_row(row: dict[str, str], rec: dict) -> dict | None:
    if "result" not in rec:
        return None
    truth = float(row["true_value"]) if row["true_value"] else None
    res = Result.model_validate(rec["result"])
    pred = lo = hi = err = covered = None
    if res.status == "measured" and res.value is not None:
        pred = convert(res.value, res.unit, row["unit"])
        if res.interval_90:
            lo = convert(res.interval_90[0], res.unit, row["unit"])
            hi = convert(res.interval_90[1], res.unit, row["unit"])
            covered = (lo <= truth <= hi) if truth is not None else None
        err = rel_error(pred, truth)
    return {
        "clip_id": row["clip_id"],
        "set": row["set"],
        "path": "measure",
        "truth": truth,
        "pred": pred,
        "lo": lo,
        "hi": hi,
        "rel_error": err,
        "covered": covered,
        "status": res.status,
        "reason": res.abstain_reason or "",
        "audit_approve": res.audit.approve if res.audit else "",
        "unit": row["unit"],
    }


def merge_write(path: Path, columns: list[str], rows: list[dict], key: tuple[str, ...]) -> None:
    """Merge rows into a CSV by key, keeping rows written by other runs (the study adds Set A)."""
    old: list[dict] = []
    if path.exists():
        with open(path, encoding="utf-8", newline="") as fh:
            new_keys = {tuple(str(r.get(k, "")) for k in key) for r in rows}
            old = [r for r in csv.DictReader(fh)
                   if tuple(r.get(k, "") for k in key) not in new_keys]  # fmt: skip
    allrows = sorted(old + rows, key=lambda r: tuple(str(r.get(k, "")) for k in key))
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=columns, lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        for r in allrows:
            w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in columns})


def _f(v: object) -> float | None:
    return None if v in (None, "") else float(v)  # type: ignore[arg-type]


def summary(results: list[dict], guesses: list[dict]) -> dict[str, dict]:
    """Per set: median and 90th percentile relative error over measured clips, coverage, counts,
    and Muse Spark alone's median relative error on the same set."""
    out: dict[str, dict] = {}
    for s in sorted({r["set"] for r in results} | {g["set"] for g in guesses}):
        rs = [r for r in results if r["set"] == s]
        meas = [r for r in rs if r.get("status") == "measured"]
        errs = sorted(e for r in meas if (e := _f(r.get("rel_error"))) is not None)
        cov = [str(r["covered"]) for r in meas if r.get("covered") not in (None, "")]
        g = sorted(e for r in guesses if r["set"] == s
                   if (e := _f(r.get("guess_rel_error"))) is not None)  # fmt: skip
        out[s] = {
            "n": len(rs),
            "measured": len(meas),
            "abstained": len(rs) - len(meas),
            "median_rel_error": statistics.median(errs) if errs else None,
            "p90_rel_error": errs[min(len(errs) - 1, int(0.9 * len(errs)))] if errs else None,
            "coverage": cov.count("True") / len(cov) if cov else None,
            "guess_n": sum(1 for r in guesses if r["set"] == s),
            "guess_answered": len(g)
            if s != "none"
            else sum(1 for r in guesses if r["set"] == s and r.get("guess_pred") not in (None, "")),
            "guess_median_rel_error": statistics.median(g) if g else None,
        }
    return out


def widen_cached(rec: dict) -> dict:
    """Apply config.INTERVAL_LOG_TERM to a field run cached before the term existed, exactly as
    the pipeline now would: widen the interval, rerun the interval_width check, and abstain
    before the audit if it fails (the audit only runs after every check passes)."""
    if "interval_log_term" in rec or "result" not in rec:
        return rec
    res = Result.model_validate(rec["result"])
    rec = {**rec, "interval_log_term": config.INTERVAL_LOG_TERM, "widened_from": res.interval_90}
    if res.status != "measured" or res.interval_90 is None or res.value is None:
        rec["result"] = json.loads(res.model_dump_json())
        return rec
    lo, hi = engine.widen(*res.interval_90)
    rel = (hi - lo) / 2 / abs(res.value)
    ok = rel <= config.INTERVAL_HALF_MAX
    new_checks = [
        c.model_copy(update={"passed": ok, "value": rel}) if c.name == "interval_width" else c
        for c in res.checks
    ]
    if ok:
        res = res.model_copy(update={"interval_90": (lo, hi), "checks": new_checks})
    else:
        res = pipeline.abstained(
            checks.first_failure(new_checks, res.spec.target_phrase) or "", res.run_id,
            res.spec, res.method, res.artifacts, res.cost_usd, new_checks,
        )  # fmt: skip
    rec["result"] = json.loads(res.model_dump_json())
    return rec


def rescore_cached(truth: list[dict]) -> None:
    """--widen-cached: rewrite field rows from cached runs with the interval term ($0)."""
    results = []
    for row in truth:
        path = RUNS / f"{row['clip_id']}.json"
        rec = widen_cached(json.loads(path.read_text(encoding="utf-8")))
        path.write_text(json.dumps(rec, indent=1), encoding="utf-8")
        if (r := result_row(row, rec)) is not None:
            results.append(r)
            log.info("%s %s pred=%s [%s, %s] truth=%s covered=%s", row["clip_id"], r["status"],
                     r["pred"], r["lo"], r["hi"], r["truth"], r["covered"])  # fmt: skip
    merge_write(OUT, COLUMNS, results, ("clip_id", "path"))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-spend", type=float, default=9.0)
    ap.add_argument("--clips", nargs="*", default=[])
    ap.add_argument("--measure-speed", action="store_true", help="Set A, vehicle as reference")
    ap.add_argument("--widen-cached", action="store_true", help="interval term on cached runs")
    args = ap.parse_args()
    measure_sets = MEASURE_SETS + (SPEED_SETS if args.measure_speed else ())

    with open(TRUTH, encoding="utf-8", newline="") as fh:
        truth = [r for r in csv.DictReader(fh) if r["set"] in GUESS_SETS]
    if args.clips:
        truth = [r for r in truth if r["clip_id"] in args.clips]
    RUNS.mkdir(parents=True, exist_ok=True)
    if args.widen_cached:
        rescore_cached(truth)
        return
    meter = SpendMeter()
    results: list[dict] = []
    guesses: list[dict] = []
    stopped = None
    for row in truth:
        frames = int(probe(normalize(FIELD / row["file"]))["frames"])
        bound = worst_case(frames, row["set"] in measure_sets)
        if meter.total + bound > args.max_spend:
            stopped = (f"stopped before {row['clip_id']}: spent ${meter.total:.4f}, "
                       f"worst case for it ${bound:.4f}")  # fmt: skip
            log.warning(stopped)
            break
        t = time.time()
        rec = run_clip(row, measure_sets)
        spent = meter.settle(frames)
        (RUNS / f"{row['clip_id']}.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
        g = guess_row(row, rec)
        guesses.append(g)
        r = result_row(row, rec)
        if r:
            results.append(r)
        log.info("%s %s pred=%s truth=%s guess=%s spent=$%.4f total=$%.4f %.0fs", row["clip_id"],
                 r["status"] if r else "guess only", r["pred"] if r else None, g["truth"],
                 g["guess_pred"], spent, meter.total, time.time() - t)  # fmt: skip
        merge_write(OUT, COLUMNS, results, ("clip_id", "path"))
        merge_write(GUESSES, GUESS_COLUMNS, guesses, ("clip_id",))
    print(json.dumps({"real_spend_usd": round(meter.total, 4), "stopped": stopped,
                      "summary": summary(results, guesses)}, indent=1))  # fmt: skip


if __name__ == "__main__":
    main()
