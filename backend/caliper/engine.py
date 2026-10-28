"""Pure math: scale, kinematics, intervals (ARCHITECTURE section 6). No I/O.

Every function works on the frames where the object was detected. Missing frames are never
interpolated into the data (Phase 0 finding 3); fits and path lengths use detected frames only.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from caliper import config
from caliper.models import MeasurementSpec, Track

AXES = ("horizontal", "vertical", "longest", "shortest", "disc")


class Abstain(Exception):
    """The data cannot support a number; the message is the reason shown to the user."""


@dataclass
class Series:
    """A track as arrays, sorted by time. ext maps axis name -> extent in pixels per frame."""

    t: np.ndarray
    pos: np.ndarray  # (n, 2) centroid x, y in pixels
    area: np.ndarray
    ext: dict[str, np.ndarray]
    frames: np.ndarray

    @classmethod
    def from_track(cls, track: Track) -> Series:
        fs = sorted(track.frames, key=lambda f: f.frame)
        return cls(
            t=np.array([f.t_s for f in fs], dtype=float),
            pos=np.array([f.centroid_px for f in fs], dtype=float).reshape(-1, 2),
            area=np.array([f.area_px for f in fs], dtype=float),
            ext={a: np.array([f.extent_px[a] for f in fs], dtype=float) for a in AXES},
            frames=np.array([f.frame for f in fs], dtype=int),
        )

    def take(self, idx: np.ndarray) -> Series:
        return Series(
            t=self.t[idx],
            pos=self.pos[idx],
            area=self.area[idx],
            ext={a: v[idx] for a, v in self.ext.items()},
            frames=self.frames[idx],
        )

    def jitter(self, dpx: float) -> Series:
        """Erode or dilate every extent by dpx (one draw per track: a systematic mask error)."""
        return Series(self.t, self.pos, self.area, {a: v + dpx for a, v in self.ext.items()},
                      self.frames)  # fmt: skip

    def __len__(self) -> int:
        return len(self.t)


def fit_half_window(fps: float) -> float:
    """Half of the fit window: window = max(FIT_WINDOW_MIN_FRAMES frames, FIT_WINDOW_MIN_S)."""
    return max(config.FIT_WINDOW_MIN_FRAMES / fps, config.FIT_WINDOW_MIN_S) / 2


def _component(vec: np.ndarray, axis: str) -> float:
    if axis == "horizontal":
        return float(abs(vec[0]))
    if axis == "vertical":
        return float(abs(vec[1]))
    return float(np.hypot(vec[0], vec[1]))


def local_quadratic(s: Series, t0: float, half: float) -> tuple[np.ndarray, np.ndarray, int]:
    """Least squares p(t) = a + b (t - t0) + c (t - t0)^2 on x and y over |t - t0| <= half.

    Returns (velocity b, acceleration 2c, points used), both in pixels per second (squared).
    """
    sel = np.abs(s.t - t0) <= half + 1e-9
    n = int(sel.sum())
    if n < config.FIT_MIN_POINTS or len(np.unique(s.t[sel])) < 3:
        raise Abstain(f"too few detections in fit window ({n} at t={t0:.2f} s)")
    tau = s.t[sel] - t0
    design = np.stack([np.ones_like(tau), tau, tau**2], axis=1)
    coef, *_ = np.linalg.lstsq(design, s.pos[sel], rcond=None)
    return coef[1], 2 * coef[2], n


def speed_px(s: Series, t0: float, axis: str, half: float) -> float:
    vel, _, _ = local_quadratic(s, t0, half)
    return _component(vel, axis)


def acceleration_px(s: Series, t0: float, axis: str, half: float) -> float:
    """Magnitude of the fitted acceleration (path), or one component (horizontal / vertical)."""
    _, acc, _ = local_quadratic(s, t0, half)
    return _component(acc, axis)


def global_acceleration_px(s: Series, axis: str) -> float:
    """Quadratic over the whole track, e.g. a ball in free fall used as a gravity reference."""
    if len(s) < config.FIT_MIN_POINTS or len(np.unique(s.t)) < 3:
        raise Abstain(f"too few detections for an acceleration reference ({len(s)})")
    tau = s.t - s.t.mean()
    design = np.stack([np.ones_like(tau), tau, tau**2], axis=1)
    coef, *_ = np.linalg.lstsq(design, s.pos, rcond=None)
    return _component(2 * coef[2], axis)


def smoothed(s: Series, half: float) -> np.ndarray:
    """Each detected position replaced by the local quadratic's value there (no new points)."""
    out = s.pos.copy()
    for i, t0 in enumerate(s.t):
        sel = np.abs(s.t - t0) <= half + 1e-9
        if sel.sum() >= config.FIT_MIN_POINTS and len(np.unique(s.t[sel])) >= 3:
            tau = s.t[sel] - t0
            design = np.stack([np.ones_like(tau), tau, tau**2], axis=1)
            coef, *_ = np.linalg.lstsq(design, s.pos[sel], rcond=None)
            out[i] = coef[0]
    return out


def in_range(s: Series, t_range: tuple[float, float] | None) -> Series:
    if t_range is None:
        return s
    lo, hi = t_range
    return s.take(np.flatnonzero((s.t >= lo - 1e-9) & (s.t <= hi + 1e-9)))


def average_speed_px(s: Series, t_range: tuple[float, float] | None, axis: str, half: float):
    """Path length of the smoothed track over elapsed time, inside t_range if given."""
    part = in_range(s, t_range)
    if len(part) < config.FIT_MIN_POINTS:
        raise Abstain(f"too few detections for an average speed ({len(part)})")
    p = smoothed(part, half)
    d = np.diff(p, axis=0)
    if axis == "horizontal":
        steps = np.abs(d[:, 0])
    elif axis == "vertical":
        steps = np.abs(d[:, 1])
    else:
        steps = np.hypot(d[:, 0], d[:, 1])
    elapsed = part.t[-1] - part.t[0]
    if elapsed <= 0:
        raise Abstain("no elapsed time between detections")
    return float(steps.sum() / elapsed)


def stable(s: Series) -> Series:
    """Frames whose mask area is within AREA_STABLE_BAND of the median (Phase 0 finding 4)."""
    med = np.median(s.area)
    keep = np.flatnonzero(np.abs(s.area - med) <= config.AREA_STABLE_BAND * med)
    if len(keep) < config.AREA_STABLE_MIN_FRAMES:
        raise Abstain(f"mask area unstable ({len(keep)} of {len(s)} frames near the median)")
    return s.take(keep)


def extent_px(s: Series, axis: str) -> float:
    """Median extent along an axis over the area-stable frames."""
    return float(np.median(stable(s).ext["longest" if axis == "path" else axis]))


def _common(a: Series, b: Series) -> tuple[np.ndarray, np.ndarray]:
    common, ia, ib = np.intersect1d(a.frames, b.frames, return_indices=True)
    if len(common) == 0:
        raise Abstain("the two objects are never detected in the same frame")
    return ia, ib


def separation_px(a: Series, b: Series, spec: MeasurementSpec) -> float:
    ia, ib = _common(a, b)
    if spec.time_anchor == "first":
        k = 0
    elif spec.time_anchor == "last":
        k = len(ia) - 1
    else:
        if spec.timestamp_s is None:
            raise Abstain("separation needs a timestamp")
        k = int(np.argmin(np.abs(a.t[ia] - spec.timestamp_s)))
        if abs(a.t[ia][k] - spec.timestamp_s) > config.SEPARATION_MAX_GAP_S:
            raise Abstain(f"both objects not detected near t={spec.timestamp_s:.2f} s")
    return _component(a.pos[ia[k]] - b.pos[ib[k]], spec.axis)


def orbit_diameter_px(target: Series, centre: Series) -> float:
    ia, ib = _common(target, centre)
    r = np.hypot(*(target.pos[ia] - centre.pos[ib]).T)
    return float(2 * np.median(r))


def leading_edge(s: Series) -> np.ndarray:
    """Position of the leading edge along the principal direction of motion (secondary track).

    Direction: first principal axis of the centroid track, signed by the net displacement.
    Edge = centroid projection + half the box extent along that direction.
    """
    centred = s.pos - s.pos.mean(axis=0)
    _, _, vt = np.linalg.svd(centred, full_matrices=False)
    u = vt[0]
    if np.dot(s.pos[-1] - s.pos[0], u) < 0:
        u = -u
    half = (abs(u[0]) * s.ext["horizontal"] + abs(u[1]) * s.ext["vertical"]) / 2
    return s.pos @ u + half


def scale_m_per_px(spec: MeasurementSpec, ref: Series, half: float) -> float:
    if spec.reference_value_si is None:
        raise Abstain("no reference value")
    if spec.reference_kind == "size" or spec.reference_statistic == "extent":
        px = extent_px(ref, spec.reference_axis)
    elif spec.reference_statistic == "average_speed":
        px = average_speed_px(ref, None, "path", half)
    elif spec.reference_statistic == "acceleration":
        px = global_acceleration_px(ref, spec.reference_axis)
    else:
        raise Abstain(f"unsupported reference {spec.reference_kind}/{spec.reference_statistic}")
    if px <= 0:
        raise Abstain("reference measures zero pixels")
    return spec.reference_value_si / px


def measure_px(spec: MeasurementSpec, tgt: Series, second: Series | None, half: float) -> float:
    """The target quantity in pixel units: px, px/s or px/s^2."""
    st = spec.statistic
    if st == "instantaneous":
        if spec.timestamp_s is None:
            raise Abstain("instantaneous value needs a timestamp")
        if spec.quantity == "speed":
            return speed_px(tgt, spec.timestamp_s, spec.axis, half)
        return acceleration_px(tgt, spec.timestamp_s, spec.axis, half)
    if st == "average":
        return average_speed_px(tgt, spec.time_range_s, spec.axis, half)
    if st == "extent":
        return extent_px(tgt, spec.axis)
    if second is None:
        raise Abstain(f"{st} needs a second object")
    if st == "separation":
        return separation_px(tgt, second, spec)
    return orbit_diameter_px(tgt, second)


@dataclass
class Measurement:
    value_si: float
    interval_si: tuple[float, float] | None
    scale_m_per_px: float
    value_px: float
    method: str
    bootstrap_ok: int
    details: dict = field(default_factory=dict)


def measure(
    spec: MeasurementSpec,
    target: Track,
    reference: Track | None = None,
    second: Track | None = None,
    *,
    boot: int = config.BOOTSTRAP_B,
    seed: int = config.BOOTSTRAP_SEED,
) -> Measurement:
    """Point estimate from all detected frames, 90% interval by bootstrap (5th to 95th pct).

    reference None means the prior describes the target itself. Bootstrap: resample each
    track's frames with replacement and shift each track's extents by U(-JITTER_PX, JITTER_PX).
    """
    tgt = Series.from_track(target)
    ref = Series.from_track(reference) if reference is not None else tgt
    sec = Series.from_track(second) if second is not None else None
    half = fit_half_window(target.fps)

    def once(t: Series, r: Series, s2: Series | None) -> tuple[float, float, float]:
        scale = scale_m_per_px(spec, r, half)
        px = measure_px(spec, t, s2, half)
        return px * scale, scale, px

    value, scale, px = once(tgt, ref, sec)
    rng = np.random.default_rng(seed)

    def resample(s: Series) -> Series:
        idx = np.sort(rng.integers(0, len(s), len(s)))
        return s.take(idx).jitter(rng.uniform(-config.JITTER_PX, config.JITTER_PX))

    draws = []
    for _ in range(boot):
        t_b = resample(tgt)
        r_b = t_b if reference is None else resample(ref)
        s_b = resample(sec) if sec is not None else None
        try:
            draws.append(once(t_b, r_b, s_b)[0])
        except Abstain:
            continue
    interval = (
        (float(np.percentile(draws, 5)), float(np.percentile(draws, 95)))
        if len(draws) >= boot // 2
        else None
    )
    window = 2 * half
    method = (
        f"centroid; {spec.statistic} {spec.quantity} along {spec.axis}; "
        f"local quadratic window {window:.2f} s on detected frames only; "
        f"scale from {spec.reference_kind}/{spec.reference_statistic} ({spec.reference_axis}); "
        f"bootstrap B={boot}"
    )
    return Measurement(value, interval, scale, px, method, len(draws))


_LENGTH = {"m": 1.0, "cm": 0.01, "mm": 0.001, "km": 1000.0}
_TIME = {"s": 1.0, "h": 3600.0}


def to_unit(value_si: float, unit: str) -> float:
    """Convert an SI value (m, m/s, m/s^2) to m, cm, mm, km, x/s, km/h, x/s^2."""
    u = unit.replace(" ", "").replace("²", "^2")
    if u.endswith("/s^2"):
        return value_si / _LENGTH[u[:-4]]
    if "/" in u:
        length, time = u.split("/")
        return value_si / _LENGTH[length] * _TIME[time]
    return value_si / _LENGTH[u]
