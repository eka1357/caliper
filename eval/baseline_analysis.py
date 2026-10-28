"""Breakdown of the muse_spark_alone baseline from cached predictions (no API calls).

Per-question MRA uses the official evaluator's formula: the share of the 10 thresholds
theta in C for which |pred - gt| / gt < 1 - theta, with pred = |parsed_value|.

Also fills share_within_10pct and share_off_2x in eval/results.csv for every variant that has
eval/quantiphy/model_outputs/<variant>.csv. Both are over all n questions; an invalid answer
(blank, non-numeric or zero) counts as a miss for both (EVAL_PROTOCOL section 4.4).
Also fills the answered-only columns and writes eval/paired_results.csv (EVAL_PROTOCOL 4a).

  python eval/baseline_analysis.py
"""

from __future__ import annotations

import csv

import pandas as pd
from baseline import DATASET, EVAL, QP, RESULTS_COLUMNS, VARIANT

C = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95]  # evaluator.py
RESULTS = EVAL / "results.csv"
PAIRED = EVAL / "paired_results.csv"
PAIRED_COLUMNS = [
    "variant", "split", "category", "n_answered", "mra_variant", "mra_muse",
    "within10_variant", "within10_muse", "off2x_variant", "off2x_muse",
]  # fmt: skip


def error_shares(part: pd.DataFrame) -> dict[str, float]:
    """Share within 10% and share off by more than 2x; invalid answers are misses for both."""
    ok = ~part.invalid
    within = ok & (part.rel_err < 0.1)
    off = ~ok | (part.ratio > 2) | (part.ratio < 0.5)
    return {"share_within_10pct": within.mean(), "share_off_2x": off.mean()}


def split_part(df: pd.DataFrame, split: str) -> pd.DataFrame:
    """Rows of a results split: full, dev, holdout, or dev_2d / dev_3d (one dimension)."""
    name, _, dim = split.partition("_")
    part = df if name == "full" else df[df.split == name]
    return part[part.dim == dim.upper()] if dim else part


def answered_metrics(part: pd.DataFrame) -> dict[str, float | str]:
    """Coverage, and MRA and error shares over the answered questions only (pooled)."""
    ans = part[~part.invalid]
    out: dict[str, float | str] = {"coverage": round(len(ans) / len(part), 4)}
    if len(ans) == 0:
        return {**out, "mra_answered": "", "share_within_10pct_answered": "",
                "share_off_2x_answered": ""}  # fmt: skip
    return {
        **out,
        "mra_answered": round(ans.mra.mean(), 4),
        "share_within_10pct_answered": round((ans.rel_err < 0.1).mean(), 4),
        "share_off_2x_answered": round(((ans.ratio > 2) | (ans.ratio < 0.5)).mean(), 4),
    }


def write_paired(loaded: dict[str, pd.DataFrame | None], rows: list[dict]) -> None:
    """muse_spark_alone on exactly the questions each other variant answered."""
    muse = loaded.get(VARIANT)
    if muse is None:
        return
    muse = muse.set_index("Unnamed: 0")
    out = []
    for row in rows:
        v, split = row["variant"], row["split"]
        df = loaded.get(v)
        if v == VARIANT or df is None:
            continue
        part = split_part(df, split)
        ans = part[~part.invalid]
        for cat in [*sorted(ans.category.unique()), "all"]:
            a = ans if cat == "all" else ans[ans.category == cat]
            m = muse.loc[a["Unnamed: 0"]]
            out.append(
                {
                    "variant": v, "split": split, "category": cat, "n_answered": len(a),
                    "mra_variant": round(a.mra.mean(), 4), "mra_muse": round(m.mra.mean(), 4),
                    "within10_variant": round((a.rel_err < 0.1).mean(), 4),
                    "within10_muse": round((m.rel_err < 0.1).mean(), 4),
                    "off2x_variant": round(((a.ratio > 2) | (a.ratio < 0.5)).mean(), 4),
                    "off2x_muse": round(((m.ratio > 2) | (m.ratio < 0.5)).mean(), 4),
                }
            )  # fmt: skip
    with open(PAIRED, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=PAIRED_COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(out)
    print(f"wrote {len(out)} rows to {PAIRED}")


def update_results() -> None:
    """Fill the error-share and answered-only columns for every row whose predictions exist."""
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
        part = split_part(df, row["split"])
        row.update({k: round(x, 4) for k, x in error_shares(part).items()})
        row.update(answered_metrics(part))
    with open(RESULTS, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=RESULTS_COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(f"updated error-share and answered-only columns in {RESULTS}")
    write_paired(loaded, rows)


def load(variant: str = VARIANT) -> pd.DataFrame:
    pred = pd.read_csv(QP / "model_outputs" / f"{variant}.csv")
    gt = pd.read_csv(DATASET)
    assert set(pred["Unnamed: 0"]) <= set(gt["Unnamed: 0"])  # a variant may cover a subset
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
