"""Whole-object frames for a target that is its own reference (Set A fallback, no video, no API).

A synthetic car crosses the picture: it enters at the left edge, is fully in view for a while,
and leaves at the right edge. Frames where the frame cuts the car off must not set the scale.
"""

import pytest

from caliper import config, engine, pipeline
from caliper.engine import Abstain
from caliper.models import MeasurementSpec, Track, TrackFrame

FPS, W, H = 30.0, 1280, 720
CAR_M = 3.995


def car_track(car_px: float, px_per_frame: float = 20.0, n: int = 140) -> Track:
    """Box of a car car_px long moving right; cut off by the picture edges like a real mask."""
    frames = []
    for i in range(n):
        front = px_per_frame * i  # the car's front starts at the left edge
        left, right = max(0.0, front - car_px), min(float(W), front)
        if right - left < 1:
            continue
        frames.append(TrackFrame(
            frame=i, t_s=i / FPS, box=(left, 400.0, right, 600.0), confidence=0.9,
            area_px=int((right - left) * 200), centroid_px=((left + right) / 2, 500.0),
            extent_px={"horizontal": right - left, "vertical": 200.0,
                       "longest": max(right - left, 200.0), "shortest": min(right - left, 200.0),
                       "disc": 0.0},
        ))  # fmt: skip
    return Track(phrase="car", object_ordinal=0, frames=frames, fps=FPS, width=W, height=H)


def spec(**kw) -> MeasurementSpec:
    base = dict(
        target_phrase="car", reference_phrase=None, reference_kind="given_prior",
        reference_statistic="extent", reference_axis="horizontal", reference_value_si=CAR_M,
        reference_source="prior", quantity="speed", statistic="average", axis="horizontal",
        timestamp_s=None, time_range_s=None, output_unit="m/s", depth_info=None,
        plausible_range_si=(0, 60),
    )  # fmt: skip
    return MeasurementSpec(**{**base, **kw})


def test_keeps_only_frames_with_the_whole_box_inside():
    t = car_track(300.0)
    whole = engine.whole_object_frames(t)
    m = config.EDGE_MARGIN_PX
    assert whole.frames and len(whole.frames) < len(t.frames)
    for f in whole.frames:
        assert f.box[0] > m and f.box[2] < W - m and f.box[1] > m and f.box[3] < H - m
    assert {f.extent_px["horizontal"] for f in whole.frames} == {300.0}


def test_whole_object_frames_recover_the_true_speed():
    t = car_track(300.0)  # 20 px/frame = 600 px/s; 300 px = 3.995 m, so 7.99 m/s
    whole, sp = pipeline._whole_object(t, spec(), {})
    assert sp.time_range_s == (whole.frames[0].t_s, whole.frames[-1].t_s)
    m = engine.measure(sp, whole, None, boot=50)
    assert m.value_si == pytest.approx(600 * CAR_M / 300, rel=0.01)


def test_cut_off_frames_would_bias_the_scale():
    """A car as long as most of the picture (like Set A): cut-off boxes are most frames, so
    without the filter the median length shrinks and the speed is overstated."""
    t = car_track(1000.0)
    whole = engine.whole_object_frames(t)
    assert len(whole.frames) >= config.FIT_MIN_POINTS
    assert engine.extent_px(engine.Series.from_track(t), "horizontal") < 0.8 * 1000.0
    assert engine.extent_px(engine.Series.from_track(whole), "horizontal") == 1000.0


def test_car_that_never_fits_is_refused():
    t = car_track(1400.0)  # longer than the picture is wide
    artifacts: dict = {}
    with pytest.raises(Abstain, match="never fully inside the picture"):
        pipeline._whole_object(t, spec(), artifacts)
    assert artifacts["whole_object_frames"]["kept"] == 0


def test_too_few_whole_frames_is_refused():
    t = car_track(1200.0)  # fully in view for only a few frames
    n = len(engine.whole_object_frames(t).frames)
    assert 0 < n < config.FIT_MIN_POINTS
    with pytest.raises(Abstain, match="never fully inside"):
        pipeline._whole_object(t, spec(), {})


def test_given_time_range_and_instantaneous_specs_are_kept():
    t = car_track(300.0)
    _, sp = pipeline._whole_object(t, spec(time_range_s=(1.0, 2.0)), {})
    assert sp.time_range_s == (1.0, 2.0)
    _, sp = pipeline._whole_object(t, spec(statistic="instantaneous", timestamp_s=1.5), {})
    assert sp.time_range_s is None
