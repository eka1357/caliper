"""Cached demo runs from real field runs (Phase 4 step 4). Costs $0: everything is read from cache.

Usage: backend/.venv/Scripts/python.exe scripts/make_field_runs.py

For each chosen clip: the Result and Muse Spark alone's answer from
data/cache/field_runs/<clip>.json (eval/field.py), the instrument reading from
data/field/truth.csv, and a demo copy of the normalized clip, downscaled to 854 px on the long
side and under 3 MB. Faces and number
plates are blurred before encoding:
  A08  the whole car while the frame edge cuts it off (seen at an angle, plates anywhere), else
       the window band (the driver) and both ends at bumper height (plates); boxes from the
       cached SAM "gray car" response;
  B03  the top-right corner where the back of a head appears at the edge (no face visible).
C01, C07 and D03 show no faces or plates. The placeholder runs are removed.
"""

from __future__ import annotations

import csv
import json
import logging
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from caliper import config, runs, segment  # noqa: E402
from caliper.normalize import probe  # noqa: E402

log = logging.getLogger("field_runs")
FIELD_RUNS = config.CACHE_DIR / "field_runs"
TRUTH = config.FIELD_DIR / "truth.csv"
LONG_SIDE = 854
CRF = 28
Box = tuple[float, float, float, float]

# run_id, clip, title, notes (no numbers: every number is read from the run JSON)
CHOSEN = [
    ("field-c07", "C07", "Phone next to a coin",
     "Field clip C07, truth by tape measure. Reference: an INR 10 coin passed as the prior."),
    ("field-c01", "C01", "Tablet next to a coin (a miss we show)",
     "Field clip C01, truth by tape measure. The question asks for the width; the spec measured "
     "the short side, while the tape value is the long side. Shown as recorded."),
    ("field-d03", "D03", "Ceiling fan, no reference in view",
     "Field clip D03 from Set D: nothing of known size is in view and no size is given."),
    ("field-b03", "B03", "Ball dropped in front of a paper sheet",
     "Field clip B03 from Set B (gravity). The back of a head at the top-right edge is blurred."),
    ("field-a08", "A08", "Car passing, the car as its own ruler",
     "Field clip A08 from Set A, truth from a GPS app. The car's length is the prior. The "
     "driver's window band and both ends of the car (plates) are blurred."),
]  # fmt: skip


def car_boxes(video: Path, n: int) -> list[list[Box]]:
    """Every cached SAM 'gray car' box per frame (cache hit, no API call)."""
    info = probe(video)
    seg = segment.segment(video, "gray car")
    tracks = segment.tracks_from_segmentation(seg, float(info["fps"]), int(info["width"]),
                                              int(info["height"]))  # fmt: skip
    out: list[list[Box]] = [[] for _ in range(n)]
    for t in tracks:
        for f in t.frames:
            if f.frame < n:
                out[f.frame].append(f.box)
    return out


def blur(frame: np.ndarray, x0: float, y0: float, x1: float, y1: float) -> None:
    h, w = frame.shape[:2]
    a, b = max(0, int(x0)), min(w, int(np.ceil(x1)))
    c, d = max(0, int(y0)), min(h, int(np.ceil(y1)))
    if b > a and d > c:
        frame[c:d, a:b] = cv2.GaussianBlur(frame[c:d, a:b], (0, 0), 18)


def car_blur(boxes: list[list[Box]]) -> Callable[[np.ndarray, int], None]:
    """While the car is cut off by the left or right edge it is seen at an angle and a plate can
    sit anywhere in its box, so the whole box is blurred. Fully in view (side on): the window
    band (the driver) and both ends at bumper height. Boxes are padded by 5% each way."""

    def apply(frame: np.ndarray, k: int) -> None:
        w = frame.shape[1]
        for left, top, right, bottom in boxes[k] if k < len(boxes) else []:
            px, py = 0.05 * (right - left), 0.05 * (bottom - top)
            left, top, right, bottom = left - px, top - py, right + px, bottom + py
            bw, bh = right - left, bottom - top
            if left <= 2 or right >= w - 2:
                blur(frame, left, top, right, bottom)
                continue
            blur(frame, left, top, right, top + 0.45 * bh)  # windows: the driver
            for x0 in (left, right - 0.25 * bw):  # front and rear: plates at bumper height
                blur(frame, x0, top + 0.40 * bh, x0 + 0.25 * bw, bottom)

    return apply


def corner_blur(x0: float, y0: float, x1: float, y1: float) -> Callable[[np.ndarray, int], None]:
    return lambda frame, k: blur(frame, x0, y0, x1, y1)


def export(video: Path, dest: Path, apply: Callable[[np.ndarray, int], None] | None) -> None:
    """Blur on full-resolution frames, then downscale and encode H.264 with faststart."""
    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS)
    w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    scale = f"scale={LONG_SIDE}:-2" if w >= h else f"scale=-2:{LONG_SIDE}"
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{w}x{h}",
         "-r", f"{fps}", "-i", "-", "-an", "-vf", scale, "-c:v", "libx264", "-preset", "slow",
         "-crf", str(CRF), "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(dest)],
        stdin=subprocess.PIPE,
    )  # fmt: skip
    assert ff.stdin is not None
    k = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if apply is not None:
            apply(frame, k)
        ff.stdin.write(frame.tobytes())
        k += 1
    ff.stdin.close()
    ff.wait()
    cap.release()
    if ff.returncode != 0:
        raise RuntimeError(f"ffmpeg failed for {video.name}")


def instrument(row: dict[str, str]) -> dict | None:
    if not row["true_value"]:
        return None
    return {"value": float(row["true_value"]), "unit": row["unit"],
            "instrument": row["instrument"]}  # fmt: skip


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    with open(TRUTH, encoding="utf-8", newline="") as fh:
        truth = {r["clip_id"]: r for r in csv.DictReader(fh)}
    for old in config.RUNS_DIR.glob("placeholder-*"):
        shutil.rmtree(old)
    index = config.RUNS_DIR / "index.json"
    if index.exists():
        keep = [e for e in json.loads(index.read_text(encoding="utf-8")) if not e["placeholder"]]
        index.write_text(json.dumps(keep, indent=1), encoding="utf-8")
    for run_id, cid, title, notes in CHOSEN:
        rec = json.loads((FIELD_RUNS / f"{cid}.json").read_text(encoding="utf-8"))
        result = rec["result"]
        video = config.NORMALIZED_DIR / rec["video"]
        info = probe(video)
        n, fps = int(info["frames"]), float(info["fps"])
        overlay = result["artifacts"].pop("overlay", None) or {
            "fps": fps, "width": int(info["width"]), "height": int(info["height"])}  # fmt: skip
        apply = {"A08": lambda: car_blur(car_boxes(video, n)),
                 "B03": lambda: corner_blur(300, 0, 380, 220)}.get(cid, lambda: None)()  # fmt: skip
        with tempfile.TemporaryDirectory() as tmp:
            clip = Path(tmp) / "clip.mp4"
            export(video, clip, apply)
            meta = runs.RunMeta(title=title, question=truth[cid]["question"], source="field",
                                placeholder=False, notes=notes,
                                instrument=instrument(truth[cid]))  # fmt: skip
            guess = {k: rec["guess"].get(k) for k in ("text", "parsed_value")}
            runs.save_cached_run(run_id, "measure", result, overlay, meta, clip, guess=guess)
            log.info("%s: %s, clip %d bytes", run_id, result["status"], clip.stat().st_size)


if __name__ == "__main__":
    main()
