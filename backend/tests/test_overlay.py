"""Overlay outlines and fit series on synthetic masks (no video, no API)."""

import cv2
import numpy as np

from caliper import overlay
from caliper.models import Track, TrackFrame
from caliper.segment import mask_geometry

FPS, W, H = 30.0, 320, 180


def frame(i: int, raster: np.ndarray) -> TrackFrame:
    area, centroid, extent = mask_geometry(raster, 0, 0)
    ys, xs = np.nonzero(raster)
    box = (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)
    return TrackFrame(frame=i, t_s=i / FPS, box=box, confidence=0.9, area_px=area,
                      centroid_px=centroid, extent_px=extent)  # fmt: skip


def moving_disc(n: int = 30, speed_px_s: float = 90.0) -> tuple[Track, dict[int, np.ndarray]]:
    masks, frames = {}, []
    for i in range(n):
        img = np.zeros((H, W), np.uint8)
        cv2.circle(img, (int(40 + speed_px_s * i / FPS), 90), 12, 1, -1)
        masks[i] = img
        frames.append(frame(i, img))
    return Track(phrase="disc", object_ordinal=0, frames=frames, fps=FPS, width=W, height=H), masks


def test_outline_is_closed_path_within_point_budget():
    img = np.zeros((400, 400), np.uint8)
    cv2.circle(img, (200, 200), 150, 1, -1)
    path = overlay.outline_path(img)
    assert path.startswith("M") and path.endswith("Z")
    assert path.count("L") + 1 <= overlay.MAX_POINTS


def test_empty_mask_falls_back_to_box():
    track, _ = moving_disc(3)
    out = overlay.frames_overlay(track, None, {0: np.zeros((H, W), np.uint8)})
    assert out[0]["target"]["path"] == overlay.box_path(track.frames[0])
    assert out[0]["reference"] is None


def test_fit_series_recovers_constant_speed():
    track, masks = moving_disc()
    scale = 0.01  # m per px
    o = overlay.build(track, None, scale, "path", masks)
    assert len(o["frames"]) == 30 and o["width"] == W
    speeds = [r["speed_m_s"] for r in o["speed"]]
    assert speeds and np.allclose(speeds, 0.9, rtol=0.03)
    assert o["fit"][0]["pos_m"] == 0.0


def test_no_scale_gives_no_series():
    track, _ = moving_disc(5)
    o = overlay.build(track, None, None)
    assert o["fit"] == [] and o["speed"] == []
