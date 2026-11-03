"""Post-hoc analysis row `hybrid_posthoc` ($0, no API calls): NOT a Caliper variant.

Defined 2026-11-03, after the holdout run, with no parameters: Caliper's answer (with the audit,
as shipped) where Caliper answered, Muse Spark alone's answer where Caliper abstained. It asks
"what if a refusal fell back to the model's guess?". EVAL_PROTOCOL 4a still governs every
Caliper variant (abstentions stay abstentions) and the product never returns a guess (AGENTS
rule 1); this row exists only as an analysis, labelled post-hoc everywhere it is shown.

Reads the cached prediction CSVs eval/quantiphy/model_outputs/{caliper,muse_spark_alone}.csv,
writes model_outputs/hybrid_posthoc.csv, scores dev, holdout and full with the official
evaluator, and replaces the hybrid_posthoc rows in eval/results.csv. Then `make report`.

Usage: backend/.venv/Scripts/python.exe eval/hybrid_posthoc.py
"""

from __future__ import annotations

from datetime import date

import pandas as pd
from baseline import QP, VARIANT, score, write_results
from baseline_analysis import update_results
from quantiphy import split_entries

NAME = "hybrid_posthoc"
SOURCE = ("eval/hybrid_posthoc.py (POST-HOC analysis defined 2026-11-03 after the holdout run, no "
          "parameters, not a Caliper variant: caliper where it answered, muse_spark_alone where "
          "it abstained)")  # fmt: skip


def hybrid() -> pd.DataFrame:
    cal = pd.read_csv(QP / "model_outputs" / "caliper.csv")
    muse = pd.read_csv(QP / "model_outputs" / f"{VARIANT}.csv").set_index("Unnamed: 0")
    assert len(cal) == 158 and set(cal["Unnamed: 0"]) == set(muse.index)
    pred = pd.to_numeric(cal.parsed_value, errors="coerce")
    answered = pred.notna() & (pred != 0)  # the evaluator's invalid rule
    fallback = pd.Series(muse.loc[cal["Unnamed: 0"], "parsed_value"].to_numpy(), index=cal.index)
    out = cal.copy()
    out["parsed_value"] = pred.where(answered, fallback)
    print(f"caliper answered {int(answered.sum())} of {len(cal)}; the rest take muse_spark_alone")
    return out


def main() -> None:
    rows = hybrid()
    rows.to_csv(QP / "model_outputs" / f"{NAME}.csv", index=False)
    dataset = rows.set_index("Unnamed: 0", drop=False)
    out = []
    for split in ("dev", "holdout", "full"):
        ids = {e["row_id"] for e in split_entries(split, dataset)}
        part = rows[rows["Unnamed: 0"].isin(ids)].reset_index(drop=True)
        m = score(part, split, NAME)
        out.append({
            "variant": NAME, "split": split,
            "mra_average": m.get("mra_average"),
            **{k: m.get(k) if pd.notna(m.get(k)) else "" for k in
               ("mra_S2", "mra_D2", "mra_S3", "mra_D3")},
            "abstain_rate": m.get("invalid_percentage", 0) / 100, "n": len(part),
            "cost_usd": 0.0, "run_date": date.today().isoformat(), "source": SOURCE,
        })  # fmt: skip
    write_results(out)
    update_results()


if __name__ == "__main__":
    main()
