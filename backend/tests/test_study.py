"""Street speed study on synthetic tracks with known crossing times (no video, no API)."""

import numpy as np
import pytest

from caliper import config, study
from caliper.models import Track, TrackFrame, VehicleReading

FPS = 30.0
GATE_A = ((300.0, 100.0), (300.0, 600.0))  # vertical lines across the road, 600 px apart
GATE_B = ((900.0, 100.0), (900.0, 600.0))
DIST_M = 10.0  # so 60 px per metre


def _track(px_per_frame=10.0, n=130, x0=0.0, width=80.0, grow=0.0, drop=(), area_jump_at=None):
    frames = []
    for i in range(n):
        if i in drop:
            continue
        w = width + grow * i
        left = x0 + px_per_frame * i - (w - width) / 2
        area = w * 40 * (2.5 if area_jump_at is not None and i >= area_jump_at else 1.0)
        frames.append(TrackFrame(
            frame=i, t_s=i / FPS, box=(left, 360.0, left + w, 400.0), confidence=0.9,
            area_px=int(area), centroid_px=(left + w / 2, 380.0),
            extent_px={"horizontal": w, "vertical": 40.0, "longest": w, "shortest": 40.0,
                       "disc": 50.0},
        ))  # fmt: skip
    return Track(phrase="car", object_ordinal=0, frames=frames, fps=FPS, width=1280, height=720)


def _read(track):
    return study.vehicle_reading(track, GATE_A, GATE_B, DIST_M, "v0", "car")


def test_constant_speed_gives_known_speed_and_crossing_times():
    r = _read(_track(px_per_frame=10.0))  # 300 px/s = 5 m/s = 18 km/h
    assert r.status == "measured"
    assert r.speed_kmh == pytest.approx(18.0, rel=1e-9)
    # Leading (right) edge starts at x=80: reaches 300 after 22 frames, 900 after 82 frames
    assert r.t_gate_a_s == pytest.approx(22 / FPS)
    assert r.t_gate_b_s == pytest.approx(82 / FPS)
    lo, hi = r.interval_90_kmh
    assert lo < 18.0 < hi
    assert hi - lo < 1.0  # half-frame timing, 1 px and 5 cm on a 2 s crossing


def test_sub_frame_crossing_is_interpolated():
    r = _read(_track(px_per_frame=7.0, n=200))  # crossings fall between frames
    assert r.status == "measured"
    assert r.speed_kmh == pytest.approx(7.0 * FPS / 60.0 * 3.6, rel=1e-9)


def test_moving_left_uses_the_left_edge():
    frames = _track(px_per_frame=10.0).frames
    mirrored = [f.model_copy(update={
        "box": (1280 - f.box[2], f.box[1], 1280 - f.box[0], f.box[3]),
        "centroid_px": (1280 - f.centroid_px[0], f.centroid_px[1])}) for f in frames]  # fmt: skip
    t = Track(phrase="car", object_ordinal=0, frames=mirrored, fps=FPS, width=1280, height=720)
    r = study.vehicle_reading(t, GATE_B, GATE_A, DIST_M, "v0", "car")
    assert r.status == "measured"
    assert r.speed_kmh == pytest.approx(18.0, rel=1e-9)


def test_hidden_at_a_gate_gives_no_reading():
    r = _read(_track(drop=range(78, 86)))  # no mask for 8 frames around gate B (frame 82)
    assert r.status == "no_reading" and r.reason == "hidden at gate B"


def test_identity_switch_gives_no_reading():
    r = _read(_track(area_jump_at=50))
    assert r.status == "no_reading" and "identity" in r.reason


def test_estimates_that_disagree_give_no_reading():
    r = _read(_track(grow=3.0))  # box grows: front edge runs ahead of the centroid
    assert r.status == "no_reading" and "disagree" in r.reason


def test_implausible_speed_gives_no_reading():
    r = _read(_track(px_per_frame=80.0, n=20))  # 2400 px/s = 40 m/s = 144 km/h: allowed
    assert r.status == "measured"
    r = _read(_track(px_per_frame=100.0, n=20))  # 180 km/h
    assert r.status == "no_reading" and "implausible" in r.reason


def test_not_crossing_both_gates_gives_no_reading():
    r = _read(_track(n=60))  # stops before gate B
    assert r.status == "no_reading" and r.reason == "does not cross both gates"


def test_too_few_frames_and_not_moving():
    assert _read(_track(n=3)).reason == "seen on too few frames"
    assert _read(_track(px_per_frame=0.0)).reason == "not moving"


def test_summary_median_p85_share_and_interval():
    speeds = [20, 25, 30, 35, 40, 45, 50, 55, 60, 65]
    rs = [VehicleReading(vehicle_id=f"v{i}", vehicle_class="car", status="measured", speed_kmh=s,
                         interval_90_kmh=(s - 1, s + 1), t_gate_a_s=0, t_gate_b_s=1, reason=None)
          for i, s in enumerate(speeds)]  # fmt: skip
    rs.append(VehicleReading(vehicle_id="x", vehicle_class="bus", status="no_reading",
                             speed_kmh=None, interval_90_kmh=None, t_gate_a_s=None,
                             t_gate_b_s=None, reason="hidden at gate A"))  # fmt: skip
    s = study.summarize(rs, "run", DIST_M, 60.0, speed_limit_kmh=40.0)
    assert (s.vehicles_seen, s.vehicles_measured) == (11, 10)
    assert s.median_kmh == pytest.approx(42.5)
    assert s.p85_kmh == pytest.approx(float(np.percentile(speeds, 85)))
    assert s.share_over_limit == pytest.approx(0.5)
    lo, hi = s.p85_interval_90_kmh
    assert lo <= s.p85_kmh <= hi
    assert study.summarize(rs[-1:], "run", DIST_M, 60.0).p85_kmh is None


def test_parameters_come_from_config():
    assert config.STUDY_MAX_KMH == 150.0 and config.STUDY_AGREE_TOL == 0.10
