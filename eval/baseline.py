"""$ muse_spark_alone: Muse Spark 1.3 alone with the official QuantiPhy zero-shot prompt.

Runs the patched upstream script (eval/baseline_patch.diff) unchanged in its prompt, method and
parsing, scores dev / holdout / full with the official evaluator, and writes the
muse_spark_alone rows of eval/results.csv. All calls go through the disk cache: reruns cost $0.

  python eval/baseline.py --pilot 1   # one question, then print the projected full-run cost
  python eval/baseline.py             # all 158 questions (spends credits; ask first)
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

import pandas as pd
from caliper import config
from caliper.meta_client import muse_cost_usd
from caliper.normalize import probe

EVAL = Path(__file__).resolve().parent
QP = EVAL / "quantiphy"
UPSTREAM = QP / "model_run_example"
DATASET = config.QUANTIPHY_DIR / "validation_dataset.csv"
VIDEOS_BY_ID = config.QUANTIPHY_DIR / "videos_by_id"
WORK = config.CACHE_DIR / "baseline"
VARIANT = "muse_spark_alone"
CEILING_USD = 30.0  # human's hard ceiling for the full 158-question run (2026-10-28)
STOP_USD = 25.0  # human: kill the run if cached Muse chat spend passes this (2026-10-28)
RESULTS_COLUMNS = [
    "variant", "split", "mra_average", "mra_S2", "mra_D2", "mra_S3", "mra_D3",
    "abstain_rate", "n", "cost_usd", "run_date", "source",
]  # fmt: skip


def link_videos() -> dict[str, Path]:
    """Expose every video under its dataset id; one source file name has a leading space."""
    VIDEOS_BY_ID.mkdir(parents=True, exist_ok=True)
    out = {}
    for src in (config.QUANTIPHY_DIR / "validation_videos").glob("*.mp4"):
        dst = VIDEOS_BY_ID / src.name.strip()
        if not dst.exists():
            os.link(src, dst)
        out[dst.stem] = dst
    return out


def chat_usage() -> tuple[dict[str, int], int]:
    """Summed usage and count of cached muse chat records (in Phase 0 these are the baseline)."""
    total = {"input_tokens": 0, "output_tokens": 0}
    n = 0
    for p in (config.CACHE_DIR / "api").glob("*/*.json"):
        rec = json.loads(p.read_text(encoding="utf-8"))
        if rec["kind"] == "chat" and rec["model"] == config.MUSE_MODEL:
            n += 1
            for k in total:
                total[k] += rec["usage"][k]
    return total, n


def run_upstream(questions: pd.DataFrame, tag: str) -> pd.DataFrame:
    WORK.mkdir(parents=True, exist_ok=True)
    csv_file = WORK / f"questions_{tag}.csv"
    questions.to_csv(csv_file, index=False)
    out_dir = WORK / f"upstream_{tag}"
    env = {
        **os.environ,
        # The upstream script reads OPENAI_API_KEY; set it for the child process only.
        "OPENAI_API_KEY": os.environ["MODEL_API_KEY"],
        "QP_PROVIDER": "muse",
        "QP_CSV_FILE": str(csv_file),
        "QP_VIDEO_DIR": str(VIDEOS_BY_ID),
        "QP_OUTPUT_DIR": str(out_dir),
        "QP_VIDEO_WORKERS": "4",
        "PYTHONIOENCODING": "utf-8",
    }
    # Menu answers: method 1 (zero-shot), version 3 (original), Enter for the default provider.
    proc = subprocess.Popen(
        [sys.executable, "run_API_results.py"],
        cwd=UPSTREAM, env=env, stdin=subprocess.PIPE, text=True, encoding="utf-8",
    )  # fmt: skip
    assert proc.stdin is not None
    proc.stdin.write("1\n3\n\n")
    proc.stdin.close()
    while proc.poll() is None:
        try:
            proc.wait(timeout=20)
        except subprocess.TimeoutExpired:
            spent = muse_cost_usd(chat_usage()[0])
            if spent > STOP_USD:
                proc.kill()
                sys.exit(f"STOP: cached Muse spend ${spent:.2f} passed ${STOP_USD:.0f}; run killed")
    if proc.returncode != 0:
        sys.exit(f"upstream script failed with exit code {proc.returncode}")
    outputs = sorted((out_dir / "tables").glob("muse-spark-1.3_zero_shot_v3_results_2*.csv"))
    if not outputs:
        sys.exit(f"no upstream results CSV in {out_dir / 'tables'}")
    return pd.read_csv(outputs[-1])


def score(pred: pd.DataFrame, split: str) -> dict[str, float]:
    """Run the official evaluator on one split's rows; require every row to match the GT file."""
    in_dir, out_dir = WORK / f"score_{split}" / "in", WORK / f"score_{split}" / "out"
    in_dir.mkdir(parents=True, exist_ok=True)
    pred.to_csv(in_dir / f"{VARIANT}.csv", index=False)
    proc = subprocess.run(
        [sys.executable, "evaluator.py", str(in_dir), str(out_dir), "--gt_file", str(DATASET)],
        cwd=QP, capture_output=True, text=True, check=True, encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},  # it prints a check mark; cp1252 fails
    )  # fmt: skip
    expected = f"Matched {len(pred)}/{len(pred)}"
    if expected not in proc.stdout:
        sys.exit(f"scorer did not print '{expected}' for {split}:\n{proc.stdout}")
    print(f"{split}: {expected}")
    return pd.read_csv(out_dir / "all_model_results.csv").iloc[0].to_dict()


def pilot(dataset: pd.DataFrame, videos: dict[str, Path], n: int) -> None:
    """Run n questions from one typical video and project the full run's cost from them."""
    info = {v: probe(p) for v, p in videos.items()}
    frames = {v: int(i["frames"]) for v, i in info.items()}
    total_frames = int(sum(frames[v] for v in dataset["video_id"]))
    mean_frames = total_frames / len(dataset)
    # Typical video: 854x480 (most clips), frame count closest to the mean per question.
    typical = [v for v, i in info.items() if (i["width"], i["height"]) == (854, 480)]
    video = min(sorted(typical), key=lambda v: abs(frames[v] - mean_frames))
    rows = dataset[dataset["video_id"] == video].head(n)

    before, n_before = chat_usage()
    run_upstream(rows, f"pilot{n}")
    after, n_after = chat_usage()
    used = {k: after[k] - before[k] for k in after}
    calls = n_after - n_before
    if calls == 0:
        print("pilot: all calls were cache hits; usage below is from the whole cache")
        used, calls = after, n_after
    pilot_frames = frames[video] * len(rows)
    per_frame_in = used["input_tokens"] / pilot_frames
    out_per_call = used["output_tokens"] / calls
    proj = {
        "input_tokens": round(per_frame_in * total_frames),
        "output_tokens": round(out_per_call * len(dataset)),
    }
    cost = muse_cost_usd(proj)
    print(f"pilot: video={video} questions={len(rows)} api_calls={calls} frames={pilot_frames}")
    print(f"pilot: usage={used} cost_usd={muse_cost_usd(used):.4f}")
    print(f"pilot: input tokens per frame (incl. prompt text) = {per_frame_in:.1f}")
    print(f"projection: {total_frames} frame-images over {len(dataset)} questions -> {proj}")
    print(f"projection: cost_usd={cost:.2f} with no retries")
    print("projection: each unparseable answer adds up to 4 retries at the same cost")
    if cost > CEILING_USD:
        print(f"STOP: projection ${cost:.2f} is above the ${CEILING_USD:.0f} ceiling")


def full(dataset: pd.DataFrame) -> None:
    upstream = run_upstream(dataset, "full")
    parsed = {(r.video_id, r.question): r.parsed_value for r in upstream.itertuples()}
    pred = dataset.copy()
    pred["parsed_value"] = [
        parsed.get((v, q)) for v, q in zip(pred.video_id, pred.question, strict=True)
    ]
    blank = int(pred["parsed_value"].isna().sum())
    pred.to_csv(QP / "model_outputs" / f"{VARIANT}.csv", index=False)

    split = pd.read_csv(EVAL / "split.csv").set_index("video_id")["split"]
    usage, _ = chat_usage()
    total_cost = muse_cost_usd(usage)
    rows = []
    for name in ("dev", "holdout", "full"):
        part = pred if name == "full" else pred[pred.video_id.map(split) == name]
        m = score(part, name)
        rows.append(
            {
                "variant": VARIANT,
                "split": name,
                **{k: m.get(k) for k in ("mra_average", "mra_S2", "mra_D2", "mra_S3", "mra_D3")},
                "abstain_rate": m.get("invalid_percentage", 0) / 100,
                "n": len(part),
                "cost_usd": round(total_cost * len(part) / len(pred), 4),
                "run_date": date.today().isoformat(),
                "source": "eval/baseline.py (official zero-shot v3 prompt, evaluator.py)",
            }
        )
    write_results(rows)
    print(f"blank parsed_value: {blank}/{len(pred)}; total cost_usd={total_cost:.2f}")


def write_results(rows: list[dict]) -> None:
    path = EVAL / "results.csv"
    keep = []
    if path.exists():
        with open(path, encoding="utf-8", newline="") as fh:
            keep = [r for r in csv.DictReader(fh) if r["variant"] != VARIANT]
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=RESULTS_COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(keep + rows)
    print(f"wrote {len(rows)} {VARIANT} rows to {path}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", type=int, default=0, help="run N questions and print a projection")
    args = ap.parse_args()
    dataset = pd.read_csv(DATASET)
    videos = link_videos()
    missing = set(dataset.video_id) - set(videos)
    if missing:
        sys.exit(f"videos missing: {sorted(missing)}")
    if args.pilot:
        pilot(dataset, videos, args.pilot)
    else:
        full(dataset)


if __name__ == "__main__":
    main()
