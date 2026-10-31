"""Rewrite the `source` column of eval/quantiphy.py rows in eval/results.csv.

Earlier runs labelled every Caliper row "dev 2D only", including the 3D and all-category rows.
This recomputes each Caliper row's source with eval/quantiphy.source_for(variant, split). Only
the source column changes: every other cell is copied byte for byte, so no number moves.

Usage: backend/.venv/Scripts/python.exe scripts/fix_result_sources.py [--check]
$0, no API calls.
"""

from __future__ import annotations

import argparse
import csv
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "eval" / "results.csv"

# Same mapping as eval/quantiphy.py; imported from there so the two never drift.
sys.path.insert(0, str(ROOT / "eval"))
sys.path.insert(0, str(ROOT / "backend"))
from quantiphy import SOURCES, source_for  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="report changes, do not write")
    args = ap.parse_args()

    text = RESULTS.read_text(encoding="utf-8")
    rows = list(csv.reader(io.StringIO(text, newline="")))
    header, body = rows[0], rows[1:]
    iv, isp, isrc = header.index("variant"), header.index("split"), header.index("source")
    changed = 0
    for r in body:
        if r[iv] in SOURCES and r[isrc].startswith("eval/quantiphy.py"):
            new = source_for(r[iv], r[isp])
            if new != r[isrc]:
                print(f"{r[iv]},{r[isp]}: {r[isrc]!r} -> {new!r}")
                r[isrc] = new
                changed += 1
    print(f"{changed} source cells changed")
    if args.check or not changed:
        return
    out = io.StringIO(newline="")
    csv.writer(out, lineterminator="\n").writerows([header, *body])
    RESULTS.write_text(out.getvalue(), encoding="utf-8", newline="")


if __name__ == "__main__":
    main()
