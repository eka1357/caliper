"""Street speed study on one video: SAM per vehicle class, then the gate method (study.py).

Shared by the HTTP API (POST /api/study) and the MCP server (`study` tool); eval/study_runs.py
uses the same overlay. Network (SAM, cached on disk) and file I/O happen here; the math stays in
the frozen study.py. Gates arrive in the pixels of the frame the user drew them on and are scaled
to the normalized video (at most 1280 px on the long side for portrait, 1280 wide otherwise).
"""

from __future__ import annotations

from pathlib import Path

from caliper import segment
from caliper import study as study_math
from caliper.models import StudySummary, Track, VehicleReading
from caliper.normalize import normalize, probe

# ARCHITECTURE section 4: one SAM concept request per vehicle class.
VEHICLE_CLASSES = ["car", "motorcycle", "auto rickshaw", "bus"]

Point = tuple[float, float]
Gate = tuple[Point, Point]


def scale_gate(gate: Gate, sx: float, sy: float) -> Gate:
    (x0, y0), (x1, y1) = gate
    return ((x0 * sx, y0 * sy), (x1 * sx, y1 * sy))


def box_path(box: tuple[float, float, float, float]) -> str:
    left, top, right, bottom = box
    return (f"M{left:.1f} {top:.1f}L{right:.1f} {top:.1f}L{right:.1f} {bottom:.1f}"
            f"L{left:.1f} {bottom:.1f}Z")  # fmt: skip


def overlay_for(tracks: list[Track], readings: list[VehicleReading], gate_a: Gate, gate_b: Gate,
                fps: float, w: int, h: int) -> dict:  # fmt: skip
    """Per vehicle, its box at each gate crossing (label anchor above it), plus the gates."""
    vehicles = []
    for t, r in zip(tracks, readings, strict=True):
        by_frame = {f.frame: f for f in t.frames}
        crossings = []
        for ts in (r.t_gate_a_s, r.t_gate_b_s):
            if ts is None or not t.frames:
                continue
            target = round(ts * fps)
            f = by_frame.get(target) or min(t.frames, key=lambda x: abs(x.frame - target))
            crossings.append({"frame": f.frame, "path": box_path(f.box),
                              "anchor": [f.box[0], max(12.0, f.box[1] - 8)]})  # fmt: skip
        vehicles.append({"vehicle_id": r.vehicle_id, "crossings": crossings})
    return {"fps": fps, "width": w, "height": h,
            "gate_a": [list(gate_a[0]), list(gate_a[1])],
            "gate_b": [list(gate_b[0]), list(gate_b[1])], "vehicles": vehicles}  # fmt: skip


def run_study(
    path: Path,
    gate_a: Gate,
    gate_b: Gate,
    distance_m: float,
    run_id: str,
    vehicle_classes: list[str] | None = None,
    speed_limit_kmh: float | None = None,
    frame_size: tuple[float, float] | None = None,
) -> tuple[StudySummary, dict]:
    """Normalize, track each vehicle class with SAM (one request per class, cached), time every
    track between the gates. Returns the summary and the overlay for the UI."""
    if distance_m <= 0:
        raise ValueError("distance_m must be positive")
    video = normalize(Path(path))
    info = probe(video)
    fps, n = float(info["fps"]), int(info["frames"])
    width, height = int(info["width"]), int(info["height"])
    if frame_size is not None:  # gates drawn on the uploaded clip's own frame
        sx, sy = width / frame_size[0], height / frame_size[1]
        gate_a, gate_b = scale_gate(gate_a, sx, sy), scale_gate(gate_b, sx, sy)
    tracks: list[Track] = []
    readings: list[VehicleReading] = []
    for cls in vehicle_classes or VEHICLE_CLASSES:
        seg = segment.segment(video, cls)
        for t in segment.tracks_from_segmentation(seg, fps, width, height):
            vid = f"{cls.replace(' ', '-')}-{t.object_ordinal}"
            tracks.append(t)
            readings.append(study_math.vehicle_reading(t, gate_a, gate_b, distance_m, vid, cls))
    summary = study_math.summarize(readings, run_id, distance_m, n / fps, speed_limit_kmh)
    return summary, overlay_for(tracks, readings, gate_a, gate_b, fps, width, height)
