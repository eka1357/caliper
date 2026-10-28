"""Checks and abstention reasons (ARCHITECTURE section 7). Pure: no I/O, no model calls.

Each check returns a Check; the pipeline abstains with the user message of the first failing
check. Every threshold lives in config.py with its source. Checks that do not apply to a
question pass with detail "not applicable".
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from caliper import config, engine
from caliper.engine import Abstain, Series
from caliper.models import Check, MeasurementSpec

MESSAGES = {
    "physical_bounds": "The measurement is physically implausible.",
    "scene_scale": "The scale makes the scene an impossible size; the reference is probably wrong.",
    "reference_too_small": "The reference is too small in the picture to set the scale.",
    "gravity_reference": "Nothing in view is clearly in free fall, so gravity can't set the scale.",
    "estimates_agree": "Two ways of measuring disagree; the number isn't reliable.",
    "same_plane": "The scale changes across the picture (perspective), so one ruler doesn't fit.",
    "depth_change": "The {target} moves towards or away from the camera.",
    "target_found": "I can't find the {target} in enough frames.",
    "reference_found": "Nothing in view has a known size. Add a coin or tell me one real size.",
    "track_continuity": "The {target} is hidden for part of the motion.",
    "mask_stability": "The outline of the {target} is unstable.",
    "interval_width": "The uncertainty is too large to be useful.",
}

HARD_LIMITS_SI = {"size": (1e-3, 1e3), "speed": (0.0, 120.0), "acceleration": (0.0, 50.0)}


@dataclass
class CheckInputs:
    spec: MeasurementSpec
    target: Series
    reference: Series | None  # None: the prior describes the target itself
    value_si: float
    interval_si: tuple[float, float] | None
    scale_m_per_px: float
    frame_width: int
    clip_frames: int
    fps: float
    use_depth: bool = False  # 3D questions with depth_info handle depth explicitly


def _check(name: str, passed: bool, value: float | None, threshold: str, detail: str = "") -> Check:
    return Check(name=name, passed=bool(passed), value=None if value is None else float(value),
                 threshold=threshold, detail=detail)  # fmt: skip


def _na(name: str, why: str = "not applicable") -> Check:
    return _check(name, True, None, "", why)


def window_frames(inp: CheckInputs) -> tuple[float, float]:
    """Time span the measurement uses: the fit window, the time range, or the whole clip."""
    spec = inp.spec
    if spec.statistic == "instantaneous" and spec.timestamp_s is not None:
        window = (
            engine.accel_half_window if spec.quantity == "acceleration" else engine.fit_half_window
        )
        half = window(inp.fps)
        return spec.timestamp_s - half, spec.timestamp_s + half
    if spec.statistic == "average" and spec.time_range_s is not None:
        return spec.time_range_s
    return 0.0, (inp.clip_frames - 1) / inp.fps


def physical_bounds(inp: CheckInputs) -> Check:
    lo, hi = inp.spec.plausible_range_si
    hlo, hhi = HARD_LIMITS_SI[inp.spec.quantity]
    ok = lo <= inp.value_si <= hi and hlo <= inp.value_si <= hhi
    return _check("physical_bounds", ok, inp.value_si,
                  f"spec range [{lo:g}, {hi:g}] and hard limits [{hlo:g}, {hhi:g}] SI")  # fmt: skip


def scene_scale(inp: CheckInputs) -> Check:
    width_m = inp.frame_width * inp.scale_m_per_px
    lo, hi = config.SCENE_WIDTH_M
    return _check("scene_scale", lo <= width_m <= hi, width_m,
                  f"frame width in metres within [{lo:g}, {hi:g}]")  # fmt: skip


def reference_too_small(inp: CheckInputs) -> Check:
    spec = inp.spec
    if spec.reference_kind == "acceleration":
        return _na("reference_too_small", "gravity reference: see gravity_reference")
    ref = inp.reference if inp.reference is not None else inp.target
    axis = "longest" if spec.reference_axis == "path" else spec.reference_axis
    size_px = float(np.median(ref.ext[axis]))
    if size_px < config.MIN_REFERENCE_PX:
        return _check("reference_too_small", False, size_px,
                      f"reference extent >= {config.MIN_REFERENCE_PX} px")  # fmt: skip
    if spec.reference_statistic == "average_speed":
        path = float(np.hypot(*np.diff(ref.pos, axis=0).T).sum()) if len(ref) > 1 else 0.0
        return _check("reference_too_small", path >= config.MIN_REFERENCE_PATH_PX, path,
                      f"reference path >= {config.MIN_REFERENCE_PATH_PX} px")  # fmt: skip
    return _check("reference_too_small", True, size_px,
                  f"reference extent >= {config.MIN_REFERENCE_PX} px")  # fmt: skip


def gravity_fit(s: Series) -> tuple[float, float, float]:
    """(downward acceleration px/s^2, R^2 of the quadratic on y, vertical range px)."""
    if len(s) < config.FIT_MIN_POINTS or len(np.unique(s.t)) < 3:
        return 0.0, 0.0, 0.0
    tau = s.t - s.t.mean()
    y = s.pos[:, 1]
    coef = np.polyfit(tau, y, 2)
    resid = y - np.polyval(coef, tau)
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1 - float((resid**2).sum()) / ss_tot if ss_tot > 0 else 0.0
    return float(2 * coef[0]), r2, float(np.ptp(y))


def gravity_reference(inp: CheckInputs) -> Check:
    if inp.spec.reference_kind != "acceleration":
        return _na("gravity_reference")
    ref = inp.reference if inp.reference is not None else inp.target
    a, r2, dy = gravity_fit(ref)
    ok = a > 0 and r2 >= config.GRAVITY_MIN_R2 and dy >= config.GRAVITY_MIN_DY_PX
    return _check("gravity_reference", ok, r2,
                  f"downward acceleration > 0, R^2 >= {config.GRAVITY_MIN_R2}, "
                  f"vertical range >= {config.GRAVITY_MIN_DY_PX} px",
                  f"a_y={a:.1f} px/s^2, R^2={r2:.3f}, dy={dy:.1f} px")  # fmt: skip


def estimates_agree(inp: CheckInputs) -> Check:
    """Scale from the first vs second half of the reference's frames (and two axes for discs)."""
    spec = inp.spec
    if spec.reference_kind == "acceleration":
        return _na("estimates_agree", "gravity reference: one global fit")
    ref = inp.reference if inp.reference is not None else inp.target
    half = engine.fit_half_window(inp.fps)
    order = np.argsort(ref.t)
    n = len(order)
    scales = []
    try:
        for idx in (order[: n // 2], order[n // 2 :]):
            scales.append(engine.scale_m_per_px(spec, ref.take(np.sort(idx)), half))
        if spec.reference_statistic == "extent" and spec.reference_axis == "disc":
            alt = spec.model_copy(update={"reference_axis": "longest"})
            scales.append(engine.scale_m_per_px(alt, ref, half))
    except Abstain as exc:
        return _check("estimates_agree", False, None, "", f"a half could not be measured: {exc}")
    spread = (max(scales) - min(scales)) / float(np.mean(scales))
    return _check("estimates_agree", spread <= config.SCALE_AGREE_TOL, spread,
                  f"scale spread <= {config.SCALE_AGREE_TOL:.0%}",
                  "scales " + ", ".join(f"{x:.4g}" for x in scales))  # fmt: skip


def same_plane(inp: CheckInputs) -> Check:
    """Reference apparent size against image row; the implied scale change at the target's row."""
    if inp.reference is None:
        return _na("same_plane", "reference is the target")
    ref, axis = inp.reference, inp.spec.reference_axis
    axis = "longest" if axis == "path" else axis
    rows = ref.pos[:, 1]
    if np.ptp(rows) < config.PERSPECTIVE_MIN_ROWS_PX or inp.spec.reference_kind != "size":
        return _na("same_plane", "reference does not span enough rows to measure perspective")
    slope, icpt = np.polyfit(rows, ref.ext[axis], 1)
    at_ref = icpt + slope * float(np.median(rows))
    at_tgt = icpt + slope * float(np.median(inp.target.pos[:, 1]))
    change = abs(at_tgt / at_ref - 1) if at_ref > 0 else np.inf
    return _check("same_plane", change <= config.PERSPECTIVE_TOL, change,
                  f"implied scale change <= {config.PERSPECTIVE_TOL:.0%}")  # fmt: skip


def depth_change(inp: CheckInputs) -> Check:
    if inp.use_depth:
        return _na("depth_change", "depth_info gives the distance")
    lo, hi = window_frames(inp)
    sel = (inp.target.t >= lo - 1e-9) & (inp.target.t <= hi + 1e-9)
    if sel.sum() < config.FIT_MIN_POINTS:
        return _na("depth_change", "too few frames to judge")
    size = np.sqrt(inp.target.area[sel])
    k = max(1, len(size) // 4)  # median of the first and last quarter, robust to flicker
    first, last = float(np.median(size[:k])), float(np.median(size[-k:]))
    change = abs(last / first - 1) if first > 0 else np.inf
    return _check("depth_change", change <= config.DEPTH_CHANGE_TOL, change,
                  f"apparent size change <= {config.DEPTH_CHANGE_TOL:.0%}")  # fmt: skip


def target_found(inp: CheckInputs) -> Check:
    lo, hi = window_frames(inp)
    expected = int(np.floor(hi * inp.fps + 1e-9) - np.ceil(max(lo, 0) * inp.fps - 1e-9) + 1)
    expected = max(1, min(expected, inp.clip_frames))
    seen = int(((inp.target.t >= lo - 1e-9) & (inp.target.t <= hi + 1e-9)).sum())
    share = seen / expected
    return _check("target_found", share >= config.TARGET_FOUND_SHARE, share,
                  f"target in >= {config.TARGET_FOUND_SHARE:.0%} of frames used")  # fmt: skip


def reference_found(inp: CheckInputs) -> Check:
    if inp.reference is None:
        return _na("reference_found", "the prior describes the target")
    share = len(inp.reference) / inp.clip_frames
    return _check("reference_found", share >= config.REFERENCE_FOUND_SHARE, share,
                  f"reference in >= {config.REFERENCE_FOUND_SHARE:.0%} of frames")  # fmt: skip


def track_continuity(inp: CheckInputs) -> Check:
    if inp.spec.statistic != "instantaneous":
        return _na("track_continuity")
    lo, hi = window_frames(inp)
    frames = inp.target.frames[(inp.target.t >= lo - 1e-9) & (inp.target.t <= hi + 1e-9)]
    gap = int(np.diff(np.sort(frames)).max() - 1) if len(frames) > 1 else inp.clip_frames
    return _check("track_continuity", gap <= config.MAX_GAP_FRAMES, gap,
                  f"gap <= {config.MAX_GAP_FRAMES} frames in the fit window")  # fmt: skip


def mask_stability(inp: CheckInputs) -> Check:
    lo, hi = window_frames(inp)
    a = inp.target.area[(inp.target.t >= lo - 1e-9) & (inp.target.t <= hi + 1e-9)]
    if len(a) < 2:
        return _na("mask_stability", "too few frames to judge")
    cv = float(np.std(a) / np.mean(a))
    return _check("mask_stability", cv <= config.MASK_CV_MAX, cv,
                  f"area coefficient of variation <= {config.MASK_CV_MAX}")  # fmt: skip


def interval_width(inp: CheckInputs) -> Check:
    if inp.interval_si is None:
        return _check("interval_width", False, None, "", "no bootstrap interval")
    half = (inp.interval_si[1] - inp.interval_si[0]) / 2
    rel = half / abs(inp.value_si) if inp.value_si else np.inf
    return _check("interval_width", rel <= config.INTERVAL_HALF_MAX, rel,
                  f"90% half-width <= {config.INTERVAL_HALF_MAX:.0%} of the value")  # fmt: skip


CHECKS = [physical_bounds, scene_scale, reference_too_small, gravity_reference, estimates_agree,
          same_plane, depth_change, target_found, reference_found, track_continuity,
          mask_stability, interval_width]  # fmt: skip


def run_checks(inp: CheckInputs, disabled: frozenset[str] = frozenset()) -> list[Check]:
    return [c(inp) for c in CHECKS if c.__name__ not in disabled]


def first_failure(checks: list[Check], target_phrase: str) -> str | None:
    for c in checks:
        if not c.passed:
            return MESSAGES[c.name].format(target=target_phrase)
    return None
