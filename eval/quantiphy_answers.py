"""Per-question answers of the frozen QuantiPhy runs -> eval/quantiphy_answers.csv ($0).

One row per (variant, question) for caliper and caliper_no_audit over all 158 validation questions,
read from the run JSONs in data/cache/runs/<variant>/ that `eval/quantiphy.py --split full` wrote.
report.py copies it into web/public/results.json, where the site derives 90% interval coverage
per split and the audit vetoes (caliper abstained where caliper_no_audit answered). Numbers only:
no question text, no video.

Usage: backend/.venv/Scripts/python.exe eval/quantiphy_answers.py
"""

from __future__ import annotations

import csv
import json

import pandas as pd
from baseline import DATASET, EVAL
from quantiphy import MUSE_SPEC_VARIANTS, runs_dir

OUT = EVAL / "quantiphy_answers.csv"
COLUMNS = ["variant", "split", "row_id", "category", "status", "value", "lo", "hi", "truth",
           "rel_error", "covered", "audit_approve"]  # fmt: skip


def rows() -> list[dict]:
    d = pd.read_csv(DATASET)
    split = pd.read_csv(EVAL / "split.csv").set_index("video_id")["split"]
    out = []
    for variant in MUSE_SPEC_VARIANTS:
        for _, q in d.iterrows():
            rid = int(q["Unnamed: 0"])
            r = json.loads((runs_dir(variant) / f"{rid}.json").read_text(encoding="utf-8"))
            truth = float(q.ground_truth_posterior)
            v = r["value"]
            lo, hi = r["interval_90"] or (None, None)
            measured = r["status"] == "measured" and v is not None
            out.append({
                "variant": variant, "split": split[q.video_id], "row_id": rid,
                "category": q.inference_type[0] + q.video_type[1], "status": r["status"],
                "value": v, "lo": lo, "hi": hi, "truth": truth,
                "rel_error": round(abs(abs(v) - truth) / truth, 4) if measured else None,
                "covered": (lo <= truth <= hi) if measured and lo is not None else None,
                "audit_approve": (r["audit"] or {}).get("approve"),
            })  # fmt: skip
    return out


def main() -> None:
    data = rows()
    with open(OUT, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(data)
    print(f"wrote {len(data)} rows to {OUT}")


if __name__ == "__main__":
    main()
