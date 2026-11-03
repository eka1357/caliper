"""Build web/public/results.json from the eval CSVs (make report). Costs $0; nothing is typed.

Sources (AGENTS.md rule 4): eval/results.csv, eval/paired_results.csv, eval/field_results.csv,
eval/field_guesses.csv, eval/interval_calibration.csv and eval/quantiphy_answers.csv
(per-question QuantiPhy answers, eval/quantiphy_answers.py). The web app reads only this JSON, so
every number on /results and the landing comes from these files. The README results block
(between its markers) is generated from the same data by readme_results.py.

Usage: backend/.venv/Scripts/python.exe eval/report.py
"""

from __future__ import annotations

import csv
import json
import math
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "eval"
sys.path[:0] = [str(EVAL), str(ROOT / "backend")]

from field import summary  # noqa: E402
from readme_results import write_readme  # noqa: E402

OUT = ROOT / "web" / "public" / "results.json"
README = ROOT / "README.md"
SOURCES = {
    "results": "results.csv",
    "paired": "paired_results.csv",
    "field": "field_results.csv",
    "field_guesses": "field_guesses.csv",
    "interval_calibration": "interval_calibration.csv",
    "answers": "quantiphy_answers.csv",
}
TEXT = {"variant", "split", "run_date", "source", "category", "clip_id", "set", "path", "status",
        "reason", "unit", "guess_text"}  # fmt: skip
FIELD_BOOL = {"covered", "audit_approve"}  # booleans in field_results.csv and quantiphy_answers.csv
COUNTS = {"n", "n_answered", "answered", "covered", "newly_refused_interval_width", "row_id"}


def read(name: str) -> list[dict[str, str]]:
    with open(EVAL / name, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def typed(row: dict[str, str], bools: set[str] | frozenset[str] = frozenset()) -> dict:
    """CSV strings to JSON types: numbers, booleans, null for blanks and NaN."""
    out: dict = {}
    for k, v in row.items():
        if k in TEXT:
            out[k] = v
        elif v in ("", None) or v.lower() == "nan":
            out[k] = None
        elif k in bools:
            out[k] = v == "True"
        else:
            x = float(v)
            out[k] = int(x) if x.is_integer() and k in COUNTS else x
            if isinstance(out[k], float) and not math.isfinite(out[k]):
                out[k] = None
    return out


def main() -> None:
    raw = {key: read(name) for key, name in SOURCES.items()}
    guesses = {g["clip_id"]: typed(g) for g in raw["field_guesses"]}
    field = []
    for r in raw["field"]:
        row = typed(r, FIELD_BOOL)
        g = guesses.get(row["clip_id"], {})
        row.update(guess_pred=g.get("guess_pred"), guess_rel_error=g.get("guess_rel_error"))
        field.append(row)
    data = {
        "generated_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "sources": {k: f"eval/{v}" for k, v in SOURCES.items()},
        # post-hoc analysis rows (eval/hybrid_posthoc.py) are kept apart from the variants
        "results": [typed(r) for r in raw["results"] if not r["variant"].endswith("_posthoc")],
        "posthoc": [typed(r) for r in raw["results"] if r["variant"].endswith("_posthoc")],
        "paired": [typed(r) for r in raw["paired"]],
        "field": field,
        "field_summary": summary(  # measure path only; study-path rows are scored as H5
            [x for x in raw["field"] if x["path"] == "measure"], raw["field_guesses"]
        ),
        "interval_calibration": [typed(r) for r in raw["interval_calibration"]],
        "answers": [typed(r, FIELD_BOOL) for r in raw["answers"]],
    }
    OUT.write_text(json.dumps(data, indent=1), encoding="utf-8")
    print(f"wrote {OUT} ({len(data['results'])} results rows, {len(field)} field rows)")
    if write_readme(README, data):
        print(f"wrote the results block in {README}")


if __name__ == "__main__":
    main()
