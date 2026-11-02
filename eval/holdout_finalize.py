"""Score the frozen QuantiPhy runs ($0, no API calls): dev, holdout and full for caliper and
caliper_no_audit (EVAL_PROTOCOL sections 4 and 4a).

Reads the run JSONs that `eval/quantiphy.py --split full` wrote under data/cache/runs/<variant>/,
then for each variant:
  - writes eval/quantiphy/model_outputs/<variant>.csv with all 158 questions (abstention = blank),
  - scores dev, holdout and full with the official evaluator (must print "Matched n/n"),
  - replaces the <variant>/{dev,holdout,full} rows in eval/results.csv (cost_usd = the run from
    scratch: spec calls, audit calls, each (video, phrase) SAM request once),
and then fills the answered-only columns and eval/paired_results.csv (baseline_analysis), rebuilds
web/public/results.json (report.py), and prints the new rows, the dev rows before and after, and
90% interval coverage on the answered holdout questions (DECISIONS 2026-11-02 revisit trigger).

Usage: backend/.venv/Scripts/python.exe eval/holdout_finalize.py
"""

from __future__ import annotations

import csv
import json
import sys
from datetime import date

import pandas as pd
import report
from baseline import DATASET, EVAL, QP, score, write_results
from baseline_analysis import update_results
from caliper import config
from caliper.segment import sam_cost_usd
from quantiphy import (
    FREEZE_COMMIT,
    MUSE_SPEC_VARIANTS,
    check_frozen,
    contexts,
    muse_spec_cached,
    runs_dir,
    source_for,
    split_entries,
)

SPLITS = ("dev", "holdout", "full")
SHOW = ["variant", "split", "n", "mra_average", "abstain_rate", "coverage", "mra_answered",
        "share_within_10pct_answered", "share_off_2x_answered", "cost_usd"]  # fmt: skip


def results_rows() -> list[dict]:
    with open(EVAL / "results.csv", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def load_runs(variant: str, entries: list[dict]) -> dict[int, dict]:
    rd = runs_dir(variant)
    missing = [e["row_id"] for e in entries if not (rd / f"{e['row_id']}.json").exists()]
    if missing:
        sys.exit(f"STOP: {variant}: {len(missing)} run JSONs missing (first {missing[:5]}); "
                 "the run did not finish")  # fmt: skip
    return {e["row_id"]: json.loads((rd / f"{e['row_id']}.json").read_text(encoding="utf-8"))
            for e in entries}  # fmt: skip


def run_cost(runs: dict[int, dict], entries: list[dict], ctxs) -> float:
    """Cost of these questions from scratch: spec call, audit call, each SAM request once."""
    muse = sum((muse_spec_cached(e["row_id"]) or {}).get("cost_usd", 0.0) for e in entries)
    muse += sum((runs[e["row_id"]]["artifacts"].get("audit_call") or {}).get("cost_usd") or 0.0
                for e in entries)  # fmt: skip
    sam = {(e["video_id"], p) for e in entries
           for p in runs[e["row_id"]]["artifacts"].get("phrases_tried", [])}  # fmt: skip
    return muse + sam_cost_usd(sum(ctxs[v].frames for v, _ in sam))


def coverage_line(variant: str, runs: dict[int, dict], dataset: pd.DataFrame,
                  entries: list[dict]) -> str:  # fmt: skip
    inside = answered = 0
    for e in entries:
        r = runs[e["row_id"]]
        if r["status"] != "measured" or not r.get("interval_90"):
            continue
        answered += 1
        gt = float(dataset.loc[e["row_id"], "ground_truth_posterior"])
        lo, hi = r["interval_90"]
        inside += lo <= gt <= hi
    return f"{variant} holdout: 90% interval contains the truth on {inside} of {answered} answered"


def main() -> None:
    check_frozen()
    dataset = pd.read_csv(DATASET).set_index("Unnamed: 0", drop=False)
    by_split = {s: split_entries(s, dataset) for s in SPLITS}
    ctxs = contexts(by_split["full"], dataset)
    before = {(r["variant"], r["split"]): r for r in results_rows()}
    today = date.today().isoformat()
    notes = []
    for variant in MUSE_SPEC_VARIANTS:
        runs = load_runs(variant, by_split["full"])
        rows = dataset.reset_index(drop=True).copy()
        rows["parsed_value"] = [runs[int(r)]["value"] for r in rows["Unnamed: 0"]]
        rows.to_csv(QP / "model_outputs" / f"{variant}.csv", index=False)
        out = []
        for split in SPLITS:
            ids = {e["row_id"] for e in by_split[split]}
            part = rows[rows["Unnamed: 0"].isin(ids)].reset_index(drop=True)
            m = score(part, split, variant)
            out.append({
                "variant": variant, "split": split,
                "mra_average": m.get("mra_average") if pd.notna(m.get("mra_average")) else "",
                **{k: m.get(k) if pd.notna(m.get(k)) else "" for k in
                   ("mra_S2", "mra_D2", "mra_S3", "mra_D3")},
                "abstain_rate": m.get("invalid_percentage", 0) / 100, "n": len(part),
                "cost_usd": round(run_cost(runs, by_split[split], ctxs), 4), "run_date": today,
                "source": source_for(variant, split),
            })  # fmt: skip
        write_results(out)
        notes.append(coverage_line(variant, runs, dataset, by_split["holdout"]))
    update_results()  # error shares, answered-only columns, paired_results.csv
    report.main()  # web/public/results.json

    after = {(r["variant"], r["split"]): r for r in results_rows()}
    print(f"\n== frozen at {FREEZE_COMMIT[:7]}; interval term k = {config.INTERVAL_LOG_TERM}")
    print(",".join(SHOW))
    for v in MUSE_SPEC_VARIANTS:
        for s in SPLITS:
            print(",".join(str(after[(v, s)].get(c, "")) for c in SHOW))
    print("\n== dev rows before -> after (must match: dev answers come from the cache)")
    for v in MUSE_SPEC_VARIANTS:
        old, new = before.get((v, "dev"), {}), after[(v, "dev")]
        same = all(old.get(c) == new.get(c) for c in ("mra_average", "abstain_rate", "n"))
        print(f"{v}: mra_average {old.get('mra_average')} -> {new['mra_average']}, "
              f"abstain_rate {old.get('abstain_rate')} -> {new['abstain_rate']}  "
              f"{'SAME' if same else 'CHANGED: report this'}")  # fmt: skip
    print("\n== " + "\n== ".join(notes))


if __name__ == "__main__":
    main()
