"""Engine on synthetic clips drawn with opencv: known speeds, accelerations and sizes.

Masks come from thresholding the drawn frames (no SAM) and go through the same
segment.mask_geometry used for SAM masks. Every quantity must be recovered within 2%.
"""

import cv2
import numpy as np
import pytest

from caliper import config, engine
from caliper.engine import Abstain
from caliper.models import MeasurementSpec, Track, TrackFrame
from caliper.segment import mask_geometry

FPS, W, H = 30.0, 640, 360
TARGET, REF = 255, 128  # gray levels: one object per level
SQUARE_PX, SQUARE_M = 40, 0.5  # reference square: 40 px drawn, 0.5 m in the "world"
S = SQUARE_M / SQUARE_PX  # truth: metres per pixel


def disc(img, x, y, r, level=TARGET):
    cv2.circle(img, (round(x * 16), round(y * 16)), round(r * 16), level, -1, cv2.LINE_8, 4)


def square(img, x0=560, y0=20, level=REF):
    cv2.rectangle(img, (x0, y0), (x0 + SQUARE_PX - 1, y0 + SQUARE_PX - 1), level, -1)


def track(frames: list[np.ndarray], level: int, keep=None) -> Track:
    out = []
    for i, img in enumerate(frames):
        if keep is not None and i not in keep:
            continue
        area, centroid, extent = mask_geometry((img == level).astype(np.uint8), 0, 0)
        if area:
            out.append(
                TrackFrame(frame=i, t_s=i / FPS, box=(0, 0, 1, 1), confidence=0.9,
                           area_px=area, centroid_px=centroid, extent_px=extent)
            )  # fmt: skip
    return Track(phrase="x", object_ordinal=0, frames=out, fps=FPS, width=W, height=H)


def clip(n: int, paint) -> list[np.ndarray]:
    frames = []
    for i in range(n):
        img = np.zeros((H, W), np.uint8)
        paint(img, i / FPS)
        square(img)
        frames.append(img)
    return frames


def spec(**kw) -> MeasurementSpec:
    base = dict(
        target_phrase="disc", reference_phrase="square", reference_kind="size",
        reference_statistic="extent", reference_axis="horizontal", reference_value_si=SQUARE_M,
        reference_source="test", quantity="speed", statistic="instantaneous", axis="path",
        timestamp_s=1.0, output_unit="m/s", depth_info=None, plausible_range_si=(0, 100),
    )  # fmt: skip
    base.update(kw)
    return MeasurementSpec(**base)


def close(got: float, want: float, tol: float = 0.02) -> bool:
    return abs(got - want) <= tol * abs(want)


@pytest.fixture(scope="module")
def constant_speed():
    return clip(60, lambda img, t: disc(img, 60 + 120 * t, 180, 10))  # 120 px/s


@pytest.fixture(scope="module")
def accelerating():
    return clip(60, lambda img, t: disc(img, 60 + 40 * t + 0.5 * 200 * t**2, 180, 10))


def test_constant_speed_instantaneous_and_average(constant_speed):
    tgt, ref = track(constant_speed, TARGET), track(constant_speed, REF)
    inst = engine.measure(spec(), tgt, ref, boot=100)
    avg = engine.measure(spec(statistic="average", timestamp_s=None), tgt, ref, boot=100)
    assert close(inst.value_si, 120 * S) and close(avg.value_si, 120 * S)
    assert inst.interval_si[0] <= inst.value_si <= inst.interval_si[1]


def test_constant_acceleration(accelerating):
    tgt, ref = track(accelerating, TARGET), track(accelerating, REF)
    v = engine.measure(spec(), tgt, ref, boot=50)
    a = engine.measure(spec(quantity="acceleration", output_unit="m/s^2"), tgt, ref, boot=50)
    assert close(v.value_si, (40 + 200 * 1.0) * S)
    assert close(a.value_si, 200 * S)


def test_bar_length_next_to_reference_square():
    def paint(img, t):
        c, half_len, half_w = np.array([300.0, 200.0]), 100.0, 5.0
        u = np.array([np.cos(np.pi / 6), np.sin(np.pi / 6)])
        v = np.array([-u[1], u[0]])
        pts = [
            c + sx * half_len * u + sy * half_w * v
            for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))
        ]
        cv2.fillPoly(img, [np.round(np.array(pts) * 16).astype(np.int32)], TARGET, cv2.LINE_8, 4)

    frames = clip(20, paint)
    m = engine.measure(
        spec(quantity="size", statistic="extent", axis="longest", timestamp_s=None,
             output_unit="m"),
        track(frames, TARGET), track(frames, REF), boot=50,
    )  # fmt: skip
    assert close(m.value_si, 200 * S)  # 200 px drawn; rasterization adds about 1 px


def test_dropped_frames_fit_only_detected_frames(constant_speed):
    keep = {i for i in range(60) if i % 3}  # every third frame missing (33%)
    tgt = track(constant_speed, TARGET, keep=keep)
    m = engine.measure(spec(), tgt, track(constant_speed, REF), boot=50)
    assert close(m.value_si, 120 * S)
    series = engine.Series.from_track(tgt)
    half = engine.fit_half_window(FPS)
    _, _, n = engine.local_quadratic(series, 1.0, half)
    detected_in_window = sum(abs(f / FPS - 1.0) <= half + 1e-9 for f in keep)
    assert n == detected_in_window  # nothing interpolated


def test_too_few_detections_in_window_abstains(constant_speed):
    keep = set(range(0, 20)) | set(range(40, 60))  # nothing near t = 1.0 s
    tgt = track(constant_speed, TARGET, keep=keep)
    with pytest.raises(Abstain, match="too few detections"):
        engine.measure(spec(), tgt, track(constant_speed, REF), boot=10)


def test_size_uses_area_stable_frames_only():
    # 70% of frames show the 40 px disc, 30% a 70 px blob (the object changes, as captured_0034as)
    frames = clip(40, lambda img, t: disc(img, 200, 180, 20 if t * FPS < 28 else 35))
    sp = spec(quantity="size", statistic="extent", axis="disc", timestamp_s=None, output_unit="m")
    m = engine.measure(sp, track(frames, TARGET), track(frames, REF), boot=50)
    drawn_px = 2 * np.sqrt((frames[0] == TARGET).sum() / np.pi)  # the 40 px disc as drawn
    assert close(m.value_si, drawn_px * S)


def test_unstable_area_abstains():
    frames = clip(40, lambda img, t: disc(img, 200, 180, 10 if int(t * FPS) % 2 else 30))
    sp = spec(quantity="size", statistic="extent", axis="disc", timestamp_s=None, output_unit="m")
    with pytest.raises(Abstain, match="mask area unstable"):
        engine.measure(sp, track(frames, TARGET), track(frames, REF), boot=10)


def test_separation_and_orbit_diameter():
    centre, other = 64, 192

    def paint(img, t):
        disc(img, 200, 180, 8, TARGET)
        disc(img, 400, 180, 8, centre)
        ang = 2 * np.pi * 0.5 * t
        disc(img, 400 + 80 * np.cos(ang), 180 + 80 * np.sin(ang), 6, other)

    frames = clip(30, paint)
    ref = track(frames, REF)
    sep = engine.measure(
        spec(quantity="size", statistic="separation", time_anchor="first", timestamp_s=None,
             output_unit="m"),
        track(frames, TARGET), ref, track(frames, centre), boot=50,
    )  # fmt: skip
    orbit = engine.measure(
        spec(quantity="size", statistic="orbit_diameter", timestamp_s=None, output_unit="m"),
        track(frames, other), ref, track(frames, centre), boot=50,
    )  # fmt: skip
    assert close(sep.value_si, 200 * S)
    assert close(orbit.value_si, 160 * S)


def test_gravity_prior_sets_scale_from_target_itself():
    # Ball in free fall at 300 px/s^2; prior g = 9.8 m/s^2 -> 9.8 / 300 m per px; 30 px ball
    frames = clip(30, lambda img, t: disc(img, 100 + 150 * t, 60 + 50 * t + 150 * t**2, 15))
    sp = spec(
        reference_phrase=None, reference_kind="acceleration", reference_statistic="acceleration",
        reference_axis="vertical", reference_value_si=9.8, quantity="size", statistic="extent",
        axis="disc", timestamp_s=None, output_unit="m",
    )  # fmt: skip
    m = engine.measure(sp, track(frames, TARGET), None, boot=50)
    assert close(m.scale_m_per_px, 9.8 / 300)
    # truth for size: the drawn disc's own pixels (opencv draws radius 15 about 31 px across)
    drawn_px = 2 * np.sqrt((frames[0] == TARGET).sum() / np.pi)
    assert close(m.value_si, drawn_px * 9.8 / 300)


def test_leading_edge_is_ahead_of_centroid(constant_speed):
    s = engine.Series.from_track(track(constant_speed, TARGET))
    edge = engine.leading_edge(s)
    assert np.allclose(edge - s.pos[:, 0], 10.5, atol=0.6)


def test_to_unit():
    assert engine.to_unit(1.5, "cm/s") == pytest.approx(150)
    assert engine.to_unit(2.5, "cm/s^2") == pytest.approx(250)
    assert engine.to_unit(0.0572, "mm") == pytest.approx(57.2)
    assert engine.to_unit(10, "km/h") == pytest.approx(36)


def test_config_window_matches_architecture():
    assert engine.fit_half_window(30) == pytest.approx(max(9 / 30, 0.30) / 2)
    assert config.BOOTSTRAP_B == 500
