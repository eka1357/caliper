"""Street speed study on Set A (EVAL_PROTOCOL H5): the gate method in caliper/study.py against GPS.

For the refilmed Set A (markers on the car's side of the road). Set A as first filmed is not
scored: it breaks the same-plane rule (DECISIONS 2026-11-02).

Gates come from eval/study_gates.json (drawn on frame 0 and committed before any scoring). One
SAM 3.1 concept request ("car") per clip. Every car track becomes a vehicle reading; the test car
is fixed by a rule set before scoring: the measured reading whose track has the most frames
(if none is measured, the longest track's no-reading reason stands for the clip).

Writes eval/h5_results.csv (per clip, km/h), adds path=study rows to eval/field_results.csv, and
saves each clip as a study run (web/public/runs, kind="study") with a downscaled clip in which
the window band of every car box is blurred (drivers' faces; the side view shows no plates).

Usage: backend/.venv/Scripts/python.exe eval/study_runs.py [--max-spend 2.0] [--no-save]
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import statistics
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "eval"))
sys.path.insert(0, str(ROOT / "scripts"))

import make_field_runs as field_runs  # noqa: E402
from caliper import config, runs, segment, study  # noqa: E402
from caliper.models import Track  # noqa: E402
from caliper.normalize import normalize, probe  # noqa: E402
from caliper.study_live import overlay_for  # noqa: E402
from field import COLUMNS, FIELD, OUT, SpendMeter, merge_write  # noqa: E402

log = logging.getLogger("study")
GATES = ROOT / "eval" / "study_gates.json"
H5 = ROOT / "eval" / "h5_results.csv"
H5_COLUMNS = [
    "clip_id",
    "gps_kmh",
    "pred_kmh",
    "lo_kmh",
    "hi_kmh",
    "abs_error_kmh",
    "covered",
    "status",
    "reason",
    "vehicles_seen",
    "vehicles_measured",
    "test_track_frames",
]
CLIP_WIDTH = 854  # demo copy width; keeps 5 to 10 s clips well under 3 MB
WINDOW_BAND = 0.45  # top share of a car box blurred (side windows: drivers' faces)


def gps_kmh(row: dict[str, str]) -> float:
    return float(row["instrument"].split("reading ")[1].split()[0])


def pick_test_vehicle(tracks: list[Track], readings: list) -> tuple[int | None, int]:
    """Index of the test car: the measured reading with the longest track, else the longest."""
    measured = [i for i, r in enumerate(readings) if r.status == "measured"]
    pool = measured or list(range(len(readings)))
    if not pool:
        return None, 0
    i = max(pool, key=lambda k: len(tracks[k].frames))
    return i, len(tracks[i].frames)


def boxes_per_frame(tracks: list[Track], n: int) -> list[list[tuple[float, float, float, float]]]:
    """Car boxes on every frame; frames a track misses inside its span take the nearest box."""
    out: list[list] = [[] for _ in range(n)]
    for t in tracks:
        fs = sorted(t.frames, key=lambda f: f.frame)
        if not fs:
            continue
        idx = np.array([f.frame for f in fs])
        for k in range(fs[0].frame, min(n - 1, fs[-1].frame) + 1):
            out[k].append(fs[int(np.abs(idx - k).argmin())].box)
    return out


def export_blurred_clip(video: Path, tracks: list[Track], dest: Path) -> None:
    """Downscaled H.264 copy with the window band of every car box blurred."""
    cap = cv2.VideoCapture(str(video))
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    boxes = boxes_per_frame(tracks, n)
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{w}x{h}",
         "-r", f"{fps}", "-i", "-", "-an", "-vf", f"scale={CLIP_WIDTH}:-2", "-c:v", "libx264",
         "-preset", "slow", "-crf", "30", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
         str(dest)],
        stdin=subprocess.PIPE,
    )  # fmt: skip
    assert ff.stdin is not None
    for k in range(n):
        ok, frame = cap.read()
        if not ok:
            break
        for left, top, right, bottom in boxes[k]:
            x0, x1 = max(0, int(left)), min(w, int(right))
            y0 = max(0, int(top))
            y1 = min(h, int(top + WINDOW_BAND * (bottom - top)))
            if x1 > x0 and y1 > y0:
                frame[y0:y1, x0:x1] = cv2.GaussianBlur(frame[y0:y1, x0:x1], (0, 0), 25)
        ff.stdin.write(frame.tobytes())
    ff.stdin.close()
    ff.wait()
    cap.release()
    if ff.returncode != 0:
        raise RuntimeError(f"ffmpeg failed for {video.name}")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-spend", type=float, default=2.0)
    ap.add_argument("--no-save", action="store_true")
    args = ap.parse_args()

    gates = json.loads(GATES.read_text(encoding="utf-8"))["clips"]
    if not gates:
        log.warning("no gates in %s: nothing to score (gates are committed before scoring)", GATES)
        return
    with open(FIELD / "truth.csv", encoding="utf-8", newline="") as fh:
        rows = [r for r in csv.DictReader(fh) if r["clip_id"] in gates]
    meter = SpendMeter()
    h5_rows: list[dict] = []
    field_rows: list[dict] = []
    stopped = None
    for row in rows:
        cid = row["clip_id"]
        video = normalize(FIELD / row["file"])
        info = probe(video)
        frames, fps = int(info["frames"]), float(info["fps"])
        if meter.total + frames * config.SAM_USD_PER_FRAME > args.max_spend:
            stopped = f"stopped before {cid}: spent ${meter.total:.4f}"
            log.warning(stopped)
            break
        phrase = gates[cid].get("vehicle_phrase", "car")  # SAM concept, set with the gates
        seg = segment.segment(video, phrase)
        meter.settle(frames)
        width, height = int(info["width"]), int(info["height"])
        tracks = segment.tracks_from_segmentation(seg, fps, width, height)
        g = gates[cid]
        gate_a = tuple(map(tuple, g["gate_a"]))
        gate_b = tuple(map(tuple, g["gate_b"]))
        readings = [
            study.vehicle_reading(t, gate_a, gate_b, g["distance_m"],
                                  f"{cid}-v{t.object_ordinal}", phrase)
            for t in tracks
        ]  # fmt: skip
        summary = study.summarize(readings, f"study-{cid.lower()}", g["distance_m"], frames / fps)
        i, n_frames = pick_test_vehicle(tracks, readings)
        r = readings[i] if i is not None else None
        gps = gps_kmh(row)
        measured = r is not None and r.status == "measured"
        lo, hi = r.interval_90_kmh if measured else (None, None)
        reason = (r.reason or "") if r else "no car track"
        h5_rows.append({
            "clip_id": cid, "gps_kmh": gps, "pred_kmh": r.speed_kmh if measured else None,
            "lo_kmh": lo, "hi_kmh": hi,
            "abs_error_kmh": abs(r.speed_kmh - gps) if measured else None,
            "covered": (lo <= gps <= hi) if measured else None,
            "status": r.status if r else "no_reading", "reason": reason,
            "vehicles_seen": summary.vehicles_seen, "vehicles_measured": summary.vehicles_measured,
            "test_track_frames": n_frames,
        })  # fmt: skip
        truth_ms = float(row["true_value"])
        field_rows.append({
            "clip_id": cid, "set": row["set"], "path": "study", "truth": truth_ms,
            "pred": r.speed_kmh / 3.6 if measured else None,
            "lo": lo / 3.6 if measured else None, "hi": hi / 3.6 if measured else None,
            "rel_error": abs(r.speed_kmh / 3.6 - truth_ms) / truth_ms if measured else None,
            "covered": (lo / 3.6 <= truth_ms <= hi / 3.6) if measured else None,
            "status": "measured" if measured else "abstained",
            "reason": "" if measured else reason, "audit_approve": "", "unit": "m/s",
        })  # fmt: skip
        log.info("%s gps=%.0f pred=%s seen=%d measured=%d reason=%s spent_total=$%.4f", cid, gps,
                 f"{r.speed_kmh:.1f}" if measured else None, summary.vehicles_seen,
                 summary.vehicles_measured, reason, meter.total)  # fmt: skip
        if not args.no_save:
            with tempfile.TemporaryDirectory() as tmp:
                clip = Path(tmp) / "clip.mp4"
                poster = 0
                if row["set"] == "scooter":
                    # same blur as the scooter measure runs: shop-front band (faces, parked
                    # bikes' plates), rider band and both ends of every scooter box
                    boxes = boxes_per_frame(tracks, frames)
                    field_runs.export(video, clip, field_runs.scooter_blur(boxes))
                    poster = field_runs.inside_mid_frame(boxes, width)
                    what = f"one pass of our scooter between gate lines {g['distance_m']} m apart"
                    notes = ("Field clip from Set A (scooter), truth from a GPS app. Faces at the "
                             "shops, the rider and the number plates are blurred.")  # fmt: skip
                else:
                    export_blurred_clip(video, tracks, clip)
                    what = f"one car between gate lines {g['distance_m']} m apart"
                    notes = ("Field clip from Set A (one car, GPS speed known). The window band "
                             "of every car box is blurred.")  # fmt: skip
                ov = overlay_for(tracks, readings, gate_a, gate_b, fps, width, height)
                meta = runs.RunMeta(
                    title=f"Set A: {what} ({cid})",
                    question="Speed between the two gate lines", source="field",
                    placeholder=False, notes=notes,
                    created_utc=datetime.now(UTC).isoformat(timespec="seconds"),
                    clip="clip.mp4", poster="poster.jpg",
                    instrument={"value": gps, "unit": "km/h", "instrument": row["instrument"]},
                )  # fmt: skip
                runs.save_cached_run(f"study-{cid.lower()}", "study",
                                     summary.model_dump(mode="json"), ov, meta,
                                     clip=clip, poster_frame=poster)  # fmt: skip

    with open(H5, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=H5_COLUMNS, lineterminator="\n")
        w.writeheader()
        for x in h5_rows:
            w.writerow({k: ("" if x.get(k) is None else x.get(k)) for k in H5_COLUMNS})
    merge_write(OUT, COLUMNS, field_rows, ("clip_id", "path"))
    errs = [x["abs_error_kmh"] for x in h5_rows if x["abs_error_kmh"] is not None]
    cov = [x["covered"] for x in h5_rows if x["covered"] is not None]
    print(json.dumps({
        "real_spend_usd": round(meter.total, 4), "stopped": stopped, "clips": len(h5_rows),
        "measured": len(errs), "median_abs_error_kmh": statistics.median(errs) if errs else None,
        "covered": f"{sum(cov)} of {len(h5_rows)}",
    }, indent=1))  # fmt: skip


if __name__ == "__main__":
    main()
