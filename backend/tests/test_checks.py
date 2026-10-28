"""Each check passes on a clean synthetic case and fails on a broken one (no video, no API)."""

import numpy as np
import pytest

from caliper import checks, config
from caliper.engine import AXES, Series
from caliper.models import MeasurementSpec

FPS, N = 30.0, 60


def series(pos=None, area=None, ext=20.0, frames=None) -> Series:
    frames = np.arange(N) if frames is None else np.asarray(frames)
    n = len(frames)
    pos = np.stack([100 + 3 * frames, np.full(n, 200.0)], axis=1) if pos is None else pos
    area = np.full(n, 400.0) if area is None else np.asarray(area, float)
    e = np.broadcast_to(np.asarray(ext, float), (n,)).astype(float)
    return Series(t=frames / FPS, pos=np.asarray(pos, float), area=area,
                  ext={a: e.copy() for a in AXES}, frames=frames)  # fmt: skip


def spec(**kw) -> MeasurementSpec:
    base = dict(target_phrase="ball", reference_phrase="box", reference_kind="size",
                reference_statistic="extent", reference_axis="longest", reference_value_si=0.5,
                reference_source="test", quantity="speed", statistic="instantaneous",
                axis="path", timestamp_s=1.0, output_unit="m/s", depth_info=None,
                plausible_range_si=(0.1, 10.0))  # fmt: skip
    base.update(kw)
    return MeasurementSpec(**base)


def inputs(**kw) -> checks.CheckInputs:
    base = dict(spec=spec(), target=series(), reference=series(ext=40.0), value_si=2.25,
                interval_si=(2.0, 2.5), scale_m_per_px=0.0125, frame_width=640, clip_frames=N,
                fps=FPS)  # fmt: skip
    base.update(kw)
    return checks.CheckInputs(**base)


def test_all_checks_pass_on_a_clean_case():
    failed = [c.name for c in checks.run_checks(inputs()) if not c.passed]
    assert failed == []


def test_physical_bounds():
    assert not checks.physical_bounds(inputs(value_si=50.0)).passed  # outside spec range
    assert not checks.physical_bounds(
        inputs(spec=spec(plausible_range_si=(0, 500)), value_si=200.0)
    ).passed  # hard limit 120 m/s
    assert checks.physical_bounds(inputs()).passed


def test_scene_scale():
    assert not checks.scene_scale(inputs(scale_m_per_px=1.5e-5)).passed  # frame 1 cm wide
    assert checks.scene_scale(inputs()).passed


def test_reference_too_small():
    assert not checks.reference_too_small(inputs(reference=series(ext=3.0))).passed
    still = series(pos=np.tile([300.0, 200.0], (N, 1)), ext=40.0)
    sp = spec(reference_kind="speed", reference_statistic="average_speed")
    assert not checks.reference_too_small(inputs(spec=sp, reference=still)).passed
    assert checks.reference_too_small(inputs()).passed


def test_gravity_reference_needs_a_parabola():
    sp = spec(reference_kind="acceleration", reference_statistic="acceleration",
              reference_axis="vertical", reference_phrase=None)  # fmt: skip
    t = np.arange(N) / FPS
    falling = series(pos=np.stack([100 + 50 * t, 50 + 20 * t + 150 * t**2], axis=1))
    standing = series(pos=np.stack([np.full(N, 300.0), 200 + np.sin(9 * t)], axis=1))
    assert checks.gravity_reference(inputs(spec=sp, target=falling, reference=None)).passed
    assert not checks.gravity_reference(inputs(spec=sp, target=standing, reference=None)).passed


def test_estimates_agree():
    ext = np.r_[np.full(N // 2, 40.0), np.full(N // 2, 60.0)]  # reference grows 50%
    assert not checks.estimates_agree(inputs(reference=series(ext=ext))).passed
    assert checks.estimates_agree(inputs()).passed


def test_same_plane_perspective():
    rows = np.linspace(50, 450, N)
    ref = series(pos=np.stack([np.full(N, 300.0), rows], axis=1), ext=30 + 0.1 * rows)
    tgt_far = series(pos=np.stack([np.full(N, 100.0), np.full(N, 60.0)], axis=1))
    assert not checks.same_plane(inputs(reference=ref, target=tgt_far)).passed
    flat = series(pos=np.stack([np.full(N, 300.0), rows], axis=1), ext=40.0)
    assert checks.same_plane(inputs(reference=flat, target=tgt_far)).passed


def test_depth_change():
    growing = series(area=np.linspace(400, 1600, N))  # linear size doubles
    sp = spec(statistic="average", timestamp_s=None)
    assert not checks.depth_change(inputs(spec=sp, target=growing)).passed
    assert checks.depth_change(inputs(spec=sp, target=growing, use_depth=True)).passed


def test_target_found_and_reference_found():
    sparse = series(frames=np.arange(0, N, 4))  # 25% of frames
    sp = spec(statistic="average", timestamp_s=None)
    assert not checks.target_found(inputs(spec=sp, target=sparse)).passed
    assert not checks.reference_found(inputs(reference=series(frames=np.arange(5)))).passed
    assert checks.reference_found(inputs(reference=None)).passed


def test_track_continuity():
    gap = series(frames=np.r_[np.arange(0, 28), np.arange(33, N)])  # 4 missing at t = 1 s
    assert not checks.track_continuity(inputs(target=gap)).passed
    assert checks.track_continuity(inputs()).passed


def test_mask_stability():
    wobbly = series(area=np.where(np.arange(N) % 2, 200.0, 800.0))
    assert not checks.mask_stability(inputs(target=wobbly)).passed
    assert checks.mask_stability(inputs()).passed


def test_interval_width():
    assert not checks.interval_width(inputs(interval_si=(0.5, 4.5))).passed
    assert not checks.interval_width(inputs(interval_si=None)).passed
    assert checks.interval_width(inputs()).passed


def test_first_failure_message_names_target():
    failed = checks.run_checks(inputs(value_si=50.0))
    assert checks.first_failure(failed, "red ball") == checks.MESSAGES["physical_bounds"]
    assert config.MAX_GAP_FRAMES == 3


@pytest.mark.parametrize("name", list(checks.MESSAGES))
def test_every_check_has_a_message(name):
    assert checks.MESSAGES[name]
