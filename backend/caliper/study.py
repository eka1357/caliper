"""Street speed study: gate method, per-vehicle intervals, summary (ARCHITECTURE section 9).

Pure math: no network, no file I/O. Input is one Track per vehicle (from SAM, one concept per
vehicle class), two gate lines drawn across the road on the first frame, and the tape-measured
distance between them. Every parameter is in config.STUDY_* and was fixed before any Set A run.

Per vehicle:
- bottom-front point of the box (the tyre on the leading side) and the centroid, per frame;
- crossing time at each gate by linear interpolation between the two frames that straddle it;
- speed = distance / (t_B - t_A) from the bottom-front point; the centroid gives the second
  estimate, and the two must agree within STUDY_AGREE_TOL;
- 90% interval by bootstrap over +-0.5 frame timing, +-1 px gate placement, the tape tolerance
  and the choice of point (bottom-front or centroid);
- no reading, with the reason, when the vehicle is hidden at a gate, its track identity changes
  between the gates, the estimates disagree, it does not cross both gates, or the speed is
  implausible.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from caliper import config
from caliper.models import StudySummary, Track, TrackFrame, VehicleReading

Point = tuple[float, float]
Gate = tuple[Point, Point]


@dataclass(frozen=True)
class Crossing:
    t_s: float  # interpolated crossing time
    i: int  # index of the frame just before the crossing
    gap_frames: int  # frame-number gap between the two straddling frames


def signed_distance(p: Point, gate: Gate) -> float:
    """Distance in px from p to the gate's line; the sign says which side."""
    (x1, y1), (x2, y2) = gate
    dx, dy = x2 - x1, y2 - y1
    norm = float(np.hypot(dx, dy))
    if norm == 0:
        raise ValueError("gate has zero length")
    return ((p[0] - x1) * dy - (p[1] - y1) * dx) / norm


def crossing(times: np.ndarray, frames: np.ndarray, dist: np.ndarray) -> Crossing | None:
    """First sign change of dist; time interpolated linearly between the straddling frames."""
    for i in range(len(dist) - 1):
        a, b = dist[i], dist[i + 1]
        if a == 0:
            return Crossing(float(times[i]), i, 0)
        if a * b < 0:
            t = times[i] + (times[i + 1] - times[i]) * a / (a - b)
            return Crossing(float(t), i, int(frames[i + 1] - frames[i]))
    return None


def lead_point(f: TrackFrame, direction: float) -> Point:
    """Bottom of the box on the side the vehicle moves towards: where the tyre meets the road."""
    left, _, right, bottom = f.box
    return (right if direction > 0 else left, bottom)


def _identity_switch(track: list[TrackFrame], i0: int, i1: int) -> bool:
    """Area jumps by more than STUDY_ID_SWITCH_AREA_RATIO, or one step is more than
    STUDY_ID_SWITCH_STEP_RATIO times the track's median step, between frames i0 and i1 + 1."""
    seg = track[i0 : i1 + 2]
    if len(seg) < 2:
        return False
    areas = np.array([f.area_px for f in seg], float)
    hi = np.maximum(areas[1:], areas[:-1])
    lo = np.maximum(np.minimum(areas[1:], areas[:-1]), 1.0)
    if np.any(hi / lo > config.STUDY_ID_SWITCH_AREA_RATIO):
        return True
    c = np.array([f.centroid_px for f in track], float)
    gaps = np.maximum(np.diff(np.array([f.frame for f in track], float)), 1.0)
    steps = np.hypot(*np.diff(c, axis=0).T) / gaps
    med = float(np.median(steps)) if len(steps) else 0.0
    local = steps[i0 : i1 + 1]
    return bool(med > 0 and np.any(local > config.STUDY_ID_SWITCH_STEP_RATIO * med))


def _no(
    vid: str, cls: str, reason: str, ta: float | None = None, tb: float | None = None
) -> VehicleReading:
    return VehicleReading(
        vehicle_id=vid, vehicle_class=cls, status="no_reading", speed_kmh=None,
        interval_90_kmh=None, t_gate_a_s=ta, t_gate_b_s=tb, reason=reason,
    )  # fmt: skip


def vehicle_reading(
    track: Track, gate_a: Gate, gate_b: Gate, distance_m: float, vehicle_id: str,
    vehicle_class: str, seed: int = config.BOOTSTRAP_SEED,
) -> VehicleReading:  # fmt: skip
    frames = sorted(track.frames, key=lambda f: f.frame)
    if len(frames) < config.STUDY_MIN_FRAMES:
        return _no(vehicle_id, vehicle_class, "seen on too few frames")
    t = np.array([f.t_s for f in frames])
    fr = np.array([f.frame for f in frames])
    cx = np.array([f.centroid_px[0] for f in frames])
    direction = float(np.sign(cx[-1] - cx[0]))
    if direction == 0:
        return _no(vehicle_id, vehicle_class, "not moving")
    pts = {
        "lead": [lead_point(f, direction) for f in frames],
        "centroid": [f.centroid_px for f in frames],
    }
    dists = {
        k: (np.array([signed_distance(p, gate_a) for p in v]),
            np.array([signed_distance(p, gate_b) for p in v]))
        for k, v in pts.items()
    }  # fmt: skip

    est: dict[str, tuple[Crossing, Crossing]] = {}
    for k, (da, db) in dists.items():
        xa, xb = crossing(t, fr, da), crossing(t, fr, db)
        if xa is None or xb is None:
            if k == "lead":
                return _no(vehicle_id, vehicle_class, "does not cross both gates",
                           xa.t_s if xa else None, xb.t_s if xb else None)  # fmt: skip
            return _no(vehicle_id, vehicle_class, "the centroid does not cross both gates")
        est[k] = (xa, xb)
    ca, cb = est["lead"]
    if ca.gap_frames > config.STUDY_MAX_GAP_FRAMES + 1:
        return _no(vehicle_id, vehicle_class, "hidden at gate A", ca.t_s, cb.t_s)
    if cb.gap_frames > config.STUDY_MAX_GAP_FRAMES + 1:
        return _no(vehicle_id, vehicle_class, "hidden at gate B", ca.t_s, cb.t_s)
    if cb.t_s == ca.t_s:
        return _no(vehicle_id, vehicle_class, "crosses both gates at once", ca.t_s, cb.t_s)
    lo_i, hi_i = sorted((ca.i, cb.i))
    if _identity_switch(frames, lo_i, hi_i):
        return _no(vehicle_id, vehicle_class, "track identity changed between the gates",
                   ca.t_s, cb.t_s)  # fmt: skip

    v = {k: distance_m / abs(b.t_s - a.t_s) for k, (a, b) in est.items()}
    if abs(v["centroid"] - v["lead"]) / v["lead"] > config.STUDY_AGREE_TOL:
        return _no(vehicle_id, vehicle_class, "the two estimates disagree by more than 10%",
                   ca.t_s, cb.t_s)  # fmt: skip
    kmh = v["lead"] * 3.6
    if kmh > config.STUDY_MAX_KMH:
        why = f"implausible speed (over {config.STUDY_MAX_KMH:.0f} km/h)"
        return _no(vehicle_id, vehicle_class, why, ca.t_s, cb.t_s)

    rng = np.random.default_rng(seed)
    dt_frame = 1.0 / track.fps
    samples: list[float] = []
    for b in range(config.BOOTSTRAP_B):
        da, db = dists["lead" if b % 2 == 0 else "centroid"]
        ja, jb = rng.uniform(-config.STUDY_GATE_JITTER_PX, config.STUDY_GATE_JITTER_PX, 2)
        xa, xb = crossing(t, fr, da + ja), crossing(t, fr, db + jb)
        if xa is None or xb is None:
            continue
        ta = xa.t_s + rng.uniform(-1, 1) * config.STUDY_TIMING_JITTER_FRAMES * dt_frame
        tb = xb.t_s + rng.uniform(-1, 1) * config.STUDY_TIMING_JITTER_FRAMES * dt_frame
        d = distance_m + rng.uniform(-config.STUDY_TAPE_TOL_M, config.STUDY_TAPE_TOL_M)
        if tb != ta:
            samples.append(d / abs(tb - ta) * 3.6)
    lo, hi = np.percentile(samples, [5, 95]) if samples else (kmh, kmh)
    return VehicleReading(
        vehicle_id=vehicle_id, vehicle_class=vehicle_class, status="measured", speed_kmh=kmh,
        interval_90_kmh=(float(lo), float(hi)), t_gate_a_s=ca.t_s, t_gate_b_s=cb.t_s, reason=None,
    )  # fmt: skip


def summarize(
    readings: list[VehicleReading], run_id: str, gate_distance_m: float, duration_s: float,
    speed_limit_kmh: float | None = None, seed: int = config.BOOTSTRAP_SEED,
) -> StudySummary:  # fmt: skip
    """Counts, median, 85th percentile with a bootstrap interval over vehicles, share over limit."""
    speeds = np.array([r.speed_kmh for r in readings if r.status == "measured"], float)
    median = p85 = share = None
    p85_iv = None
    if speeds.size:
        median = float(np.median(speeds))
        p85 = float(np.percentile(speeds, 85))
        rng = np.random.default_rng(seed)
        boot = [np.percentile(rng.choice(speeds, speeds.size), 85)
                for _ in range(config.STUDY_P85_BOOTSTRAP_B)]  # fmt: skip
        p85_iv = (float(np.percentile(boot, 5)), float(np.percentile(boot, 95)))
        if speed_limit_kmh is not None:
            share = float(np.mean(speeds > speed_limit_kmh))
    return StudySummary(
        run_id=run_id, gate_distance_m=gate_distance_m, duration_s=duration_s,
        vehicles_seen=len(readings), vehicles_measured=int(speeds.size), median_kmh=median,
        p85_kmh=p85, p85_interval_90_kmh=p85_iv, speed_limit_kmh=speed_limit_kmh,
        share_over_limit=share, readings=readings,
    )  # fmt: skip
