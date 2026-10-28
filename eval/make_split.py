"""Write eval/split.csv: dev/holdout by video (EVAL_PROTOCOL section 2). Frozen once written.

Rule: dev = videos with int(sha256(video_id), 16) % 2 == 0. If dev is outside 10 to 14 of 24
videos, fall back to a fixed seeded shuffle of the sorted video_ids and say so. The shuffle is
stratified by video dimension (2D / 3D, second character of video_type) so both splits carry
both kinds of question; first half of each stratum is dev.
"""

from __future__ import annotations

import csv
import hashlib
import random
import sys
from pathlib import Path

from caliper import config

OUT = Path(__file__).resolve().parent / "split.csv"


def hash_split(video_ids: list[str]) -> dict[str, str]:
    return {
        v: "dev" if int(hashlib.sha256(v.encode()).hexdigest(), 16) % 2 == 0 else "holdout"
        for v in video_ids
    }


def stratified_seeded_split(dims: dict[str, str], seed: int) -> dict[str, str]:
    split: dict[str, str] = {}
    for dim in sorted(set(dims.values())):
        order = sorted(v for v, d in dims.items() if d == dim)
        random.Random(seed).shuffle(order)
        half = len(order) // 2
        split.update({v: "dev" if i < half else "holdout" for i, v in enumerate(order)})
    return split


def video_dims(rows: list[dict[str, str]]) -> dict[str, str]:
    dims: dict[str, set[str]] = {}
    for row in rows:
        dims.setdefault(row["video_id"], set()).add(row["video_type"][1])
    mixed = [v for v, d in dims.items() if len(d) != 1]
    if mixed:
        sys.exit(f"videos with mixed 2D/3D rows: {mixed}")
    return {v: d.pop() for v, d in dims.items()}


def main() -> None:
    with open(config.QUANTIPHY_DIR / "validation_dataset.csv", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    dims = video_dims(rows)
    video_ids = sorted(dims)

    split = hash_split(video_ids)
    n_dev = sum(s == "dev" for s in split.values())
    method = "sha256_mod2"
    if not config.SPLIT_HASH_MIN_DEV <= n_dev <= config.SPLIT_HASH_MAX_DEV:
        print(f"sha256 split gives {n_dev} dev of {len(video_ids)}; using stratified shuffle")
        split = stratified_seeded_split(dims, config.SPLIT_SEED)
        method = f"seeded_shuffle_by_dim_{config.SPLIT_SEED}"

    rows = [(v, split[v], method) for v in video_ids]
    if OUT.exists():
        with open(OUT, encoding="utf-8", newline="") as fh:
            existing = [tuple(r) for r in csv.reader(fh)][1:]
        if existing != rows:
            sys.exit(f"{OUT} exists and differs; the split is frozen. Not overwriting.")
        print(f"{OUT} unchanged")
        return
    with open(OUT, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["video_id", "split", "method"])
        w.writerows(rows)
    n_dev = sum(s == "dev" for _, s, _ in rows)
    print(f"wrote {OUT}: {n_dev} dev, {len(rows) - n_dev} holdout ({method})")


if __name__ == "__main__":
    main()
