"""$ Phase 0 tracking check: SAM 3.1 on 20 QuantiPhy clips, overlays for a human verdict.

Clips: the first 10 video_ids (sorted) in each split. Phrase: one text-only Muse Spark call per
clip on its first question asks for the target as a short noun phrase. One SAM concept request
per clip. Writes eval/phase0_overlays/<video_id>.mp4 (gitignored: derived from QuantiPhy videos)
and eval/phase0_tracking.csv with my_verdict left empty. Every call is cached; reruns cost $0.

  python eval/phase0_tracking.py --estimate   # frame count and SAM cost, no API calls
  python eval/phase0_tracking.py              # spends about $0.45 on the first run
"""

from __future__ import annotations

import argparse
import csv
import logging
import subprocess
import sys
from pathlib import Path

import cv2
import pandas as pd
from baseline import DATASET, EVAL, link_videos
from caliper import config
from caliper.meta_client import muse_cost_usd, responses_create
from caliper.normalize import normalize, probe
from caliper.segment import Segmentation, sam_cost_usd, segment

PER_SPLIT = 10
OVERLAYS = EVAL / "phase0_overlays"
TRACKING_CSV = EVAL / "phase0_tracking.csv"
CORRECTED_CSV = EVAL / "phase0_tracking_corrected.csv"
# Clips where the first-question phrase found nothing; the moving object their questions ask
# about, chosen by hand from the question text (human request, 2026-10-28).
CORRECTED_PHRASES = {
    "simulation_0089": "bird",  # was "big bird" (relative size, q139)
    "internet_0005": "woman in yellow",  # was "black road signs"; the walker of the prior, q2166
    "internet_0013": "white car",  # was "straight through lane"; q2203
}
CEILING_USD = 0.60  # SAM plus phrase calls; plan estimate was about $0.45
COLUMNS = [
    "video_id", "split", "phrase", "frames", "frames_returned", "objects_max",
    "mean_confidence", "overlay", "my_verdict",
]  # fmt: skip
COLORS = [(0, 220, 255), (255, 120, 0), (80, 255, 80), (255, 0, 200), (0, 120, 255)]  # BGR

PHRASE_PROMPT = (
    "A question about a short video: {question}\n"
    "Given information: {prior}\n"
    "Name the one object whose size or motion the question asks about, as a short noun phrase "
    "(1 to 4 words) usable as a segmentation prompt, e.g. 'left tennis ball' or 'white car'. "
    "Reply with the phrase only."
)


def clips() -> pd.DataFrame:
    """First question (by row id) of the first PER_SPLIT videos per split."""
    ds = pd.read_csv(DATASET)
    split = pd.read_csv(EVAL / "split.csv")
    chosen = split.sort_values("video_id").groupby("split").head(PER_SPLIT)
    first = ds.sort_values("Unnamed: 0").groupby("video_id").head(1)
    return chosen.merge(first, on="video_id").sort_values(["split", "video_id"])


def target_phrase(question: str, prior: str) -> tuple[str, float]:
    rec = responses_create(
        {
            "model": config.MUSE_MODEL,
            "input": PHRASE_PROMPT.format(question=question, prior=prior),
            "max_output_tokens": config.MUSE_MAX_OUTPUT_TOKENS,
        }
    )
    text = "".join(
        part.get("text", "")
        for item in rec["response"].get("output", [])
        for part in item.get("content") or []
    )
    phrase = text.strip().strip("'\".").lower()
    if not phrase or len(phrase.split()) > 6:
        sys.exit(f"unusable phrase {text!r} for question {question!r}")
    return phrase, muse_cost_usd(rec["usage"])


def write_overlay(video: Path, seg: Segmentation, label: str, out: Path) -> None:
    """Boxes, centroids and confidences drawn on every frame, re-encoded to H.264."""
    by_frame: dict[int, list] = {}
    for d in seg.detections:
        by_frame.setdefault(d.frame, []).append(d)
    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS)
    w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    tmp = out.with_suffix(".tmp.avi")
    writer = cv2.VideoWriter(str(tmp), cv2.VideoWriter_fourcc(*"MJPG"), fps, (w, h))
    n = 0
    while True:
        ok, img = cap.read()
        if not ok:
            break
        dets = by_frame.get(n, [])
        for d in dets:
            color = COLORS[int(d.object_id) % len(COLORS)] if d.object_id.isdigit() else COLORS[0]
            x1, y1, x2, y2 = (int(round(v)) for v in d.box)
            cv2.rectangle(img, (x1, y1), (x2 - 1, y2 - 1), color, 2)
            if d.centroid_px:
                cv2.circle(img, (int(d.centroid_px[0]), int(d.centroid_px[1])), 3, color, -1)
            conf = f" c={d.confidence:.2f}" if d.confidence is not None else ""
            cv2.putText(
                img, f"#{d.object_id}{conf}", (x1, max(12, y1 - 4)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA,
            )  # fmt: skip
        status = f"frame {n}  objects {len(dets)}" if dets else f"frame {n}  NO DETECTION"
        for text, y in ((label, 18), (status, 38)):
            cv2.putText(img, text, (8, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 3, cv2.LINE_AA)
            cv2.putText(
                img, text, (8, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA
            )
        writer.write(img)
        n += 1
    cap.release()
    writer.release()
    subprocess.run(
        [
            "ffmpeg", "-y", "-v", "error", "-i", str(tmp), "-c:v", "libx264", "-crf", "20",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out),
        ],
        check=True,
    )  # fmt: skip
    tmp.unlink()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--estimate", action="store_true", help="print frames and cost, no API calls")
    ap.add_argument("--corrected", action="store_true", help="rerun CORRECTED_PHRASES clips only")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    videos = link_videos()
    rows = clips()
    if args.corrected:
        rows = rows[rows.video_id.isin(CORRECTED_PHRASES)]
    frames = {v: int(probe(videos[v])["frames"]) for v in rows.video_id}
    sam_est = sam_cost_usd(sum(frames.values()))
    print(
        f"clips: {len(rows)} ({rows.split.value_counts().to_dict()}) frames={sum(frames.values())}"
    )
    print(f"estimate: SAM cost_usd={sam_est:.4f} (cache misses only are billed)")
    if args.estimate:
        return
    if sam_est > CEILING_USD:
        sys.exit(f"STOP: SAM estimate ${sam_est:.2f} is above ${CEILING_USD:.2f}")

    corrected = args.corrected
    out_csv = CORRECTED_CSV if corrected else TRACKING_CSV
    verdicts = {}  # a rerun keeps verdicts already filled in by hand
    if out_csv.exists():
        with open(out_csv, encoding="utf-8", newline="") as fh:
            verdicts = {row["video_id"]: row["my_verdict"] for row in csv.DictReader(fh)}
    OVERLAYS.mkdir(parents=True, exist_ok=True)
    out_rows, spent = [], 0.0
    for r in rows.itertuples():
        if corrected:
            phrase, cost = CORRECTED_PHRASES[r.video_id], 0.0
        else:
            phrase, cost = target_phrase(r.question, r.ground_truth_prior)
        video = normalize(videos[r.video_id])
        seg = segment(video, phrase)
        spent += cost + (0.0 if seg.cache_hit else sam_cost_usd(frames[r.video_id]))
        overlay = OVERLAYS / f"{r.video_id}{'__corrected' if corrected else ''}.mp4"
        write_overlay(video, seg, f"{r.video_id}: '{phrase}'", overlay)
        per_frame = seg.objects_per_frame()
        confs = [d.confidence for d in seg.detections if d.confidence is not None]
        out_rows.append(
            {
                "video_id": r.video_id,
                "split": r.split,
                "phrase": phrase,
                "frames": frames[r.video_id],
                "frames_returned": seg.frames_returned,
                "objects_max": max(per_frame.values(), default=0),
                "mean_confidence": round(sum(confs) / len(confs), 3) if confs else "",
                "overlay": overlay.relative_to(EVAL.parent).as_posix(),
                "my_verdict": verdicts.get(r.video_id, ""),
            }
        )
        print(
            f"{r.video_id}: phrase={phrase!r} frames={frames[r.video_id]} "
            f"returned={seg.frames_returned} objects_max={out_rows[-1]['objects_max']} "
            f"cache_hit={seg.cache_hit} diagnostics={len(seg.diagnostics)}"
        )
    with open(out_csv, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(out_rows)
    print(f"wrote {len(out_rows)} rows to {out_csv}; spent this run ~${spent:.4f}")


if __name__ == "__main__":
    main()
