"""Overlay data for the UI (ARCHITECTURE section 11): outlines, centroids and fit series.

Pure: takes tracks and optional full-frame mask rasters, returns plain dicts for run JSON.
Outlines come from mask rasters (synthetic masks or segment.mask_rasters, the same code path)
via cv2 contours simplified to at most MAX_POINTS; without a raster the track box is used.
"""

from __future__ import annotations

import cv2
import numpy as np

from caliper import engine
from caliper.engine import Abstain, Series
from caliper.models import Track, TrackFrame

MAX_POINTS = 200  # ARCHITECTURE section 11
MAX_FRAMES = 150  # Phase 5: outlines sent for at most this many frames per run (payload size)


def _simplify(contour: np.ndarray) -> np.ndarray:
    """Douglas-Peucker with a growing tolerance until the outline has at most MAX_POINTS."""
    pts, eps = contour, 0.5
    while len(pts) > MAX_POINTS:
        pts = cv2.approxPolyDP(contour, eps, True)
        eps *= 1.5
    return pts.reshape(-1, 2)


def _path(points: np.ndarray) -> str:
    head, *rest = (f"{x:.1f} {y:.1f}" for x, y in points)
    return "M" + head + "".join(f"L{p}" for p in rest) + "Z"


def outline_path(raster: np.ndarray) -> str | None:
    """SVG path of the largest outer contour of a binary mask, or None for an empty mask."""
    contours, _ = cv2.findContours(
        (raster > 0).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    if not contours:
        return None
    return _path(_simplify(max(contours, key=cv2.contourArea)))


def box_path(f: TrackFrame) -> str:
    left, top, right, bottom = f.box
    return _path(np.array([(left, top), (right, top), (right, bottom), (left, bottom)]))


def _object(f: TrackFrame, raster: np.ndarray | None) -> dict:
    path = outline_path(raster) if raster is not None else None
    return {"path": path or box_path(f), "centroid": list(f.centroid_px)}


def frames_overlay(
    target: Track,
    reference: Track | None,
    target_masks: dict[int, np.ndarray] | None = None,
    reference_masks: dict[int, np.ndarray] | None = None,
    only: set[int] | None = None,
) -> list[dict]:
    """One entry per frame where the target or the reference was detected (within `only`)."""
    tm, rm = target_masks or {}, reference_masks or {}
    by_t = {f.frame: f for f in target.frames}
    by_r = {f.frame: f for f in reference.frames} if reference is not None else {}
    out = []
    frames = set(by_t) | set(by_r)
    for frame in sorted(frames if only is None else frames & only):
        t, r = by_t.get(frame), by_r.get(frame)
        out.append({
            "frame": frame,
            "target": _object(t, tm.get(frame)) if t else None,
            "reference": _object(r, rm.get(frame)) if r else None,
        })  # fmt: skip
    return out


def fit_series(target: Track, scale_m_per_px: float, axis: str = "path") -> dict[str, list]:
    """Position along the motion and its local-quadratic fit (metres), plus speed over time.

    Position is the centroid projected on the main direction of motion (path), or on x / y.
    """
    s = Series.from_track(target)
    if len(s) < 2:
        return {"fit": [], "speed": []}
    half = engine.fit_half_window(target.fps)
    fit = engine.smoothed(s, half)
    if axis == "horizontal":
        direction = np.array([1.0, 0.0])
    elif axis == "vertical":
        direction = np.array([0.0, 1.0])
    else:
        d = s.pos[-1] - s.pos[0]
        n = float(np.hypot(*d))
        direction = d / n if n > 0 else np.array([1.0, 0.0])
    origin = s.pos[0]
    pos_m = (s.pos - origin) @ direction * scale_m_per_px
    fit_m = (fit - origin) @ direction * scale_m_per_px
    speed = []
    for t0 in s.t:
        try:
            v = engine.speed_px(s, float(t0), axis, half) * scale_m_per_px
        except Abstain:
            continue
        speed.append({"t_s": round(float(t0), 4), "speed_m_s": round(v, 5)})
    fit_rows = [
        {"t_s": round(float(t), 4), "pos_m": round(float(p), 5), "fit_m": round(float(q), 5)}
        for t, p, q in zip(s.t, pos_m, fit_m, strict=True)
    ]
    return {"fit": fit_rows, "speed": speed}


def sample_frames(target: Track, reference: Track | None, limit: int = MAX_FRAMES) -> set[int]:
    """At most `limit` evenly spaced detected frames; the UI holds each outline until the next."""
    frames = sorted({f.frame for f in target.frames}
                    | ({f.frame for f in reference.frames} if reference else set()))  # fmt: skip
    if len(frames) <= limit:
        return set(frames)
    idx = np.linspace(0, len(frames) - 1, limit).round().astype(int)
    return {frames[i] for i in idx}


def build(
    target: Track,
    reference: Track | None,
    scale_m_per_px: float | None,
    axis: str = "path",
    target_masks: dict[int, np.ndarray] | None = None,
    reference_masks: dict[int, np.ndarray] | None = None,
    only: set[int] | None = None,
) -> dict:
    """The `overlay` block of a run JSON."""
    empty: dict[str, list] = {"fit": [], "speed": []}
    series = fit_series(target, scale_m_per_px, axis) if scale_m_per_px else empty
    return {
        "fps": target.fps,
        "width": target.width,
        "height": target.height,
        "frames": frames_overlay(target, reference, target_masks, reference_masks, only),
        **series,
    }
