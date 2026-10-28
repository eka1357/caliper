"""Breakdown of the muse_spark_alone baseline from cached predictions (no API calls).

Per-question MRA uses the official evaluator's formula: the share of the 10 thresholds
theta in C for which |pred - gt| / gt < 1 - theta, with pred = |parsed_value|.

Also fills share_within_10pct and share_off_2x in eval/results.csv for every variant that has
eval/quantiphy/model_outputs/<variant>.csv. Both are over all n questions; an invalid answer
(blank, non-numeric or zero) counts as a miss for both (EVAL_PROTOCOL section 4.4).

  python eval/baseline_analysis.py
"""

from __future__ import annotations

import csv

import pandas as pd
from baseline import DATASET, EVAL, QP, RESULTS_COLUMNS, VARIANT

C = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95]  # evaluator.py
RESULTS = EVAL / "results.csv"


def error_shares(part: pd.DataFrame) -> dict[str, float]:
    """Share within 10% and share off by more than 2x; invalid answers are misses for both."""
    ok = ~part.invalid
    within = ok & (part.rel_err < 0.1)
    off = ~ok | (part.ratio > 2) | (part.ratio < 0.5)
    return {"share_within_10pct": within.mean(), "share_off_2x": off.mean()}


def update_results() -> None:
    """Fill the two error-share columns for every variant row whose predictions exist."""
    with open(RESULTS, encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    loaded: dict[str, pd.DataFrame | None] = {}
    for row in rows:
        v = row["variant"]
        if v not in loaded:
            path = QP / "model_outputs" / f"{v}.csv"
            loaded[v] = load(v) if path.exists() else None
        df = loaded[v]
        if df is None:
            continue
        part = df if row["split"] == "full" else df[df.split == row["split"]]
        row.update({k: round(x, 4) for k, x in error_shares(part).items()})
    with open(RESULTS, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=RESULTS_COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(f"updated share_within_10pct and share_off_2x in {RESULTS}")


def load(variant: str = VARIANT) -> pd.DataFrame:
    pred = pd.read_csv(QP / "model_outputs" / f"{variant}.csv")
    gt = pd.read_csv(DATASET)
    assert pred["Unnamed: 0"].tolist() == gt["Unnamed: 0"].tolist()
    split = pd.read_csv(EVAL / "split.csv").set_index("video_id")["split"]
    df = pred.assign(split=pred.video_id.map(split), dim=pred.video_type.str[1] + "D")
    df["category"] = df.inference_type.str[0] + df.video_type.str[1]
    df["pred"] = pd.to_numeric(df.parsed_value, errors="coerce")
    df["invalid"] = df.pred.isna() | (df.pred == 0)
    df["rel_err"] = (df.pred.abs() - df.ground_truth_posterior).abs() / df.ground_truth_posterior
    df["ratio"] = df.pred.abs() / df.ground_truth_posterior
    df["mra"] = [sum(e < 1 - t for t in C) / 10 for e in df.rel_err]
    return df


def main() -> None:
    df = load()
    pd.set_option("display.width", 140)
    for name in ("dev", "holdout", "full"):
        part = df if name == "full" else df[df.split == name]
        print(f"\n== {name} (n={len(part)})")
        g = part.groupby("video_type").agg(n=("mra", "size"), mra=("mra", "mean"))
        print("MRA by video_type (mean over questions):")
        print(g.round(3).to_string())
        d = part.groupby("dim").agg(n=("mra", "size"), mra=("mra", "mean"))
        print("MRA by dimension (mean over questions):")
        print(d.round(3).to_string())

        shares = error_shares(part)
        print(
            f"over all n (invalid = miss): within 10% {shares['share_within_10pct']:.3f}  "
            f"off by more than 2x {shares['share_off_2x']:.3f}"
        )
        valid = part[~part.invalid]
        r = valid.ratio
        print(
            f"relative error (valid n={len(valid)}): median={valid.rel_err.median():.3f} "
            f"p25={valid.rel_err.quantile(0.25):.3f} p75={valid.rel_err.quantile(0.75):.3f}"
        )
        print(
            f"within 10%: {(valid.rel_err < 0.1).mean():.3f}  "
            f"off by more than 2x (pred/gt > 2 or < 0.5): {((r > 2) | (r < 0.5)).mean():.3f}  "
            f"too high {(r > 2).mean():.3f} / too low {(r < 0.5).mean():.3f}"
        )

    print("\n== invalid answers (evaluator counts blank, non-numeric and zero)")
    cols = ["Unnamed: 0", "video_id", "split", "category", "parsed_value", "ground_truth_posterior"]
    print(df[df.invalid][cols].to_string(index=False))
    update_results()


if __name__ == "__main__":
    main()
