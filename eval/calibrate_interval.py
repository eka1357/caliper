"""Interval term calibration on the QuantiPhy dev split: before/after table. Costs $0 (no API).

Reads the dev run JSONs written by eval/quantiphy.py:
  data/cache/runs_k0/<variant>/   dev runs before the interval term (k = 0, run 2026-11-02)
  data/cache/runs/<variant>/      dev runs with config.INTERVAL_LOG_TERM
and the truths in eval/quantiphy/model_outputs/<variant>.csv. Writes eval/interval_calibration.csv:
per variant and k, answered questions, truths inside the 90% interval, answers newly refused by
the interval_width check, and (from the k = 0 runs) the smallest k that puts 90% of answered
truths inside. Field clips are never read here (DECISIONS 2026-11-02).

Usage: backend/.venv/Scripts/python.exe eval/calibrate_interval.py
"""

from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from caliper import config  # noqa: E402

RUNS = config.CACHE_DIR / "runs"
RUNS_K0 = config.CACHE_DIR / "runs_k0"
OUTPUTS = ROOT / "eval" / "quantiphy" / "model_outputs"
OUT = ROOT / "eval" / "interval_calibration.csv"
VARIANTS = ("caliper_no_audit", "caliper")  # calibrated on caliper_no_audit (more answers)
COLUMNS = ["variant", "split", "interval_log_term", "answered", "covered", "coverage",
           "newly_refused_interval_width", "k_for_90pct", "source"]  # fmt: skip


def load(folder: Path) -> dict[int, dict]:
    return {int(p.stem): json.loads(p.read_text(encoding="utf-8")) for p in folder.glob("*.json")}


def needed_k(lo: float, hi: float, truth: float) -> float:
    """Smallest log term that would put the truth inside [lo / e^k, hi * e^k]."""
    return max(0.0, math.log(lo / truth), math.log(truth / hi))


def rows_for(variant: str) -> list[dict]:
    outputs = pd.read_csv(OUTPUTS / f"{variant}.csv").set_index("Unnamed: 0")
    truth = outputs["ground_truth_posterior"]
    before, after = load(RUNS_K0 / variant), load(RUNS / variant)
    out = []
    for k, runs in ((0.0, before), (config.INTERVAL_LOG_TERM, after)):
        answered = {i: r for i, r in runs.items() if r["status"] == "measured"}
        covered = sum(r["interval_90"][0] <= float(truth[i]) <= r["interval_90"][1]
                      for i, r in answered.items())  # fmt: skip
        refused = sum(
            1 for i, r in runs.items()
            if r["status"] != "measured" and before[i]["status"] == "measured"
            and any(c["name"] == "interval_width" and not c["passed"] for c in r["checks"])
        )  # fmt: skip
        needs = sorted(needed_k(*r["interval_90"], float(truth[i])) for i, r in answered.items())
        k90 = needs[math.ceil(0.9 * len(needs)) - 1] if needs and k == 0.0 else None
        out.append({
            "variant": variant, "split": "dev", "interval_log_term": k,
            "answered": len(answered), "covered": covered,
            "coverage": round(covered / len(answered), 4) if answered else None,
            "newly_refused_interval_width": refused,
            "k_for_90pct": round(k90, 5) if k90 is not None else None,
            "source": f"eval/calibrate_interval.py, {'runs_k0' if k == 0 else 'runs'}/{variant}",
        })  # fmt: skip
    return out


def main() -> None:
    rows = [r for v in VARIANTS for r in rows_for(v)]
    with open(OUT, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({c: "" if r[c] is None else r[c] for c in COLUMNS})
    for r in rows:
        print(r)


if __name__ == "__main__":
    main()
