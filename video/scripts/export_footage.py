"""Full-frame footage of our own field clips for the demo video, with the same blur as the site.

Usage (from the repo root, $0: every SAM mask and box comes from the disk cache):
  backend/.venv/Scripts/python.exe video/scripts/export_footage.py C07 A14 A08

Writes video/public/footage/<clip>.mp4 (H.264, 30 fps, one source frame per output frame) and
<clip>.json (how output frames map to source frames, so overlays line up).

Blur: the rules of scripts/make_field_runs.py, unchanged (C07: the phone case's drawing; A14: the
shop-front band, the rider and both plates; A08: the driver's band and both plates, the whole car
while the frame edge cuts it off). When the raw phone file is sharper than the normalized copy SAM
saw and its frames line up with it one to one, the raw file is used and the same blur rectangles
are scaled to it; otherwise the normalized copy is used as is.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

# No network: a cache miss must fail, never spend (AGENTS rule 5).
os.environ["META_API_BASE_URL"] = "http://127.0.0.1:9/v1"

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "backend"))

import cv2  # noqa: E402
import make_field_runs as mfr  # noqa: E402
import numpy as np  # noqa: E402
from caliper import config, segment  # noqa: E402
from caliper.normalize import probe  # noqa: E402

OUT = ROOT / "video" / "public" / "footage"
FPS = 30
RAW = {"C07": "C_07.MOV", "A14": "PXL_20261103_120028917.mp4", "A08": "A_08.MOV"}
# Output size: the long side of the frame we keep (room for slow camera pushes at 1920 x 1080).
LONG_SIDE = {"C07": 1080, "A14": 2560, "A08": 2560}
ORDER = {"C07": "pingpong", "A14": "forward", "A08": "forward"}


def frames(path: Path):
    cap = cv2.VideoCapture(str(path))
    while True:
        ok, f = cap.read()
        if not ok:
            break
        yield f
    cap.release()


def thumbs(path: Path, size: tuple[int, int]) -> list[np.ndarray]:
    return [cv2.cvtColor(cv2.resize(f, size, interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)
            .astype(np.float32) for f in frames(path)]  # fmt: skip


def raw_lines_up(raw: Path, norm: Path) -> bool:
    """Raw frame k must match normalized frame k better than k-1 and k+1 on every sampled frame."""
    a, b = thumbs(raw, (192, 108)), thumbs(norm, (192, 108))
    if len(a) != len(b):
        print(f"  raw has {len(a)} frames, normalized {len(b)}: using normalized")
        return False
    worst = 0
    for k in range(1, len(a) - 1, max(1, len(a) // 24)):
        d = {o: float(np.mean(np.abs(a[k] - b[k + o]))) for o in (-1, 0, 1)}
        if min(d, key=d.get) != 0 and d[0] > 0.5 + min(d.values()):
            print(f"  frame {k}: raw matches normalized {min(d, key=d.get):+d}: using normalized")
            return False
        worst = max(worst, d[0])
    print(f"  raw lines up with normalized (worst mean difference {worst:.2f} grey levels)")
    return True


class Rects:
    """Records make_field_runs.blur() rectangles instead of blurring, to scale them later."""

    def __init__(self) -> None:
        self.items: list[tuple[float, float, float, float]] = []

    def __call__(self, frame: np.ndarray, x0: float, y0: float, x1: float, y1: float) -> None:
        self.items.append((x0, y0, x1, y1))


def blur_scaled(frame: np.ndarray, rect: tuple[float, float, float, float], s: float) -> None:
    """make_field_runs.blur() on a frame s times larger: same rectangle, sigma 18 x s."""
    h, w = frame.shape[:2]
    x0, y0, x1, y1 = (v * s for v in rect)
    a, b = max(0, int(x0)), min(w, int(np.ceil(x1)))
    c, d = max(0, int(y0)), min(h, int(np.ceil(y1)))
    if b > a and d > c:
        frame[c:d, a:b] = cv2.GaussianBlur(frame[c:d, a:b], (0, 0), 18 * s)


def blur_for(cid: str, norm: Path, n: int):
    """The site's blur for this clip, as apply(frame, k, scale)."""
    if cid == "C07":
        case = mfr.case_blur(norm, "white phone", n)  # a pixel mask at the normalized size

        def apply_c07(frame: np.ndarray, k: int, s: float) -> None:
            if s != 1.0:
                raise RuntimeError("C07's case mask needs the normalized frame size")
            case(frame, k)

        return apply_c07
    phrase = mfr.SCOOTER_PHRASE.get(cid, "gray car")
    boxes = mfr.car_boxes(norm, n, phrase)
    rule = mfr.scooter_blur(boxes) if cid in mfr.SCOOTER_PHRASE else mfr.car_blur(boxes)
    width = int(probe(norm)["width"])

    def apply_boxes(frame: np.ndarray, k: int, s: float) -> None:
        rects = Rects()
        saved, mfr.blur = mfr.blur, rects
        try:
            # car_blur checks the frame edge against frame.shape: give it the normalized width.
            rule(np.empty((1, width, 3), np.uint8), k)
        finally:
            mfr.blur = saved
        for r in rects.items:
            blur_scaled(frame, r, s)

    return apply_boxes


def order(n: int, kind: str) -> list[int]:
    return list(range(n)) + (list(range(n - 2, 0, -1)) if kind == "pingpong" else [])


def outlines(rec: dict, norm: Path, n: int, w: int, h: int) -> list[dict]:
    """SAM's outline of the run's own target on every frame, from the cached masks ($0), with the
    frame edges it touches. For runs that refused before an overlay was saved (A08)."""
    result = rec["result"]
    phrase = (result["artifacts"].get("phrases_used") or {}).get("target")
    track = mfr.selected_track(norm, phrase, (result.get("spec") or {}).get("target_instance"))
    if track is None:
        raise RuntimeError(f"no cached track for {phrase!r}")
    masks = segment.mask_rasters(norm, phrase, str(track.object_ordinal), list(range(n)), w, h)
    if not masks:
        raise RuntimeError(f"masks for {phrase!r} are not cached")
    out = []
    for k in sorted(masks):
        m = (masks[k] > 0).astype(np.uint8)
        cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cs = [c for c in cs if cv2.contourArea(c) >= 200]
        if not cs:
            continue
        rings = [cv2.approxPolyDP(c, 1.2, True).reshape(-1, 2) for c in cs]
        path = "".join("M" + "L".join(f"{x:.0f} {y:.0f}" for x, y in r) + "Z" for r in rings)
        ys, xs = np.nonzero(m)
        edges = {
            "left": xs.min() <= 1,
            "right": xs.max() >= w - 2,
            "top": ys.min() <= 1,
            "bottom": ys.max() >= h - 2,
        }
        touches = [side for side, hit in edges.items() if hit]
        out.append({"frame": k, "path": path, "touches": touches})
    print(f"  {len(out)} outlines of {phrase!r} (track {track.object_ordinal})")
    return out


def export(cid: str) -> None:
    rec = json.loads((config.CACHE_DIR / "field_runs" / f"{cid}.json").read_text(encoding="utf-8"))
    norm = config.NORMALIZED_DIR / rec["video"]
    info = probe(norm)
    n, w, h = int(info["frames"]), int(info["width"]), int(info["height"])
    print(f"{cid}: normalized {w}x{h}, {n} frames at {float(info['fps']):.2f} fps")
    raw = config.FIELD_DIR / RAW[cid]
    use_raw = raw.exists() and raw_lines_up(raw, norm)
    src = raw if use_raw else norm
    cap = cv2.VideoCapture(str(src))
    sw, sh = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    if sw < sh and w > h:  # rotation metadata applied by OpenCV on read; probe reports coded size
        sw, sh = sh, sw
    scale = sw / w
    if abs(sh / h - scale) > 1e-3:
        raise RuntimeError(f"{cid}: raw {sw}x{sh} is not a multiple of normalized {w}x{h}")
    apply = blur_for(cid, norm, n)
    if cid == "C07" and scale != 1.0:
        src, scale = norm, 1.0
    long_side = min(LONG_SIDE[cid], max(sw, sh))
    out_w = long_side if sw >= sh else round(long_side * sw / sh / 2) * 2
    out_h = round(long_side * sh / sw / 2) * 2 if sw >= sh else long_side

    # Blur every source frame once, keep it as a high-quality JPEG in memory, then write the
    # requested order (C07 plays forward then back, so the near-still shot loops without a jump).
    kept: list[bytes] = []
    for k, frame in enumerate(frames(src)):
        apply(frame, k, scale)
        if (frame.shape[1], frame.shape[0]) != (out_w, out_h):
            frame = cv2.resize(frame, (out_w, out_h), interpolation=cv2.INTER_AREA)
        kept.append(cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 97])[1].tobytes())
    if len(kept) != n:
        raise RuntimeError(f"{cid}: read {len(kept)} frames, expected {n}")
    seq = order(n, ORDER[cid])
    OUT.mkdir(parents=True, exist_ok=True)
    dest = OUT / f"{cid.lower()}.mp4"
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-v", "error", "-f", "image2pipe", "-c:v", "mjpeg",
         "-framerate", str(FPS), "-i", "-", "-an", "-c:v", "libx264", "-preset", "slow",
         "-crf", "18", "-pix_fmt", "yuv420p", "-g", str(FPS), "-movflags", "+faststart",
         str(dest)],
        stdin=subprocess.PIPE,
    )  # fmt: skip
    assert ff.stdin is not None
    for k in seq:
        ff.stdin.write(kept[k])
    ff.stdin.close()
    if ff.wait() != 0:
        raise RuntimeError(f"ffmpeg failed for {cid}")
    meta = {
        "clip": cid,
        "file": f"footage/{dest.name}",
        "fps": FPS,
        "width": out_w,
        "height": out_h,
        "source": "raw" if use_raw and src == raw else "normalized",
        "source_frames": n,
        "source_fps": float(info["fps"]),
        "overlay_width": w,
        "overlay_height": h,
        "order": ORDER[cid],
        "frames": len(seq),
    }
    if cid == "A08":
        meta["outlines"] = outlines(rec, norm, n, w, h)
    (OUT / f"{cid.lower()}.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    size = f"{out_w}x{out_h}"
    print(f"  wrote {dest.relative_to(ROOT)}: {size}, {len(seq)} frames, from {meta['source']}")


if __name__ == "__main__":
    for clip in sys.argv[1:] or ["C07", "A14", "A08"]:
        export(clip.upper())
