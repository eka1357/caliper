"""Placeholder cached runs from synthetic clips, until our field clips exist. Costs $0.

Usage: backend/.venv/Scripts/python.exe scripts/make_placeholder_runs.py

Clips are drawn with OpenCV (as in backend/tests/test_engine.py); masks come from the drawing,
not SAM; specs are written here, not by Muse Spark. The engine and the checks run for real.
The audit verdict on the veto run is scripted (no model call) and says so in meta.notes.
Every run is saved with source="placeholder_synthetic" and placeholder=True. Never QuantiPhy.
Deterministic: rerunning rebuilds identical results (only meta.created_utc changes).
"""

from __future__ import annotations

import logging
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from caliper import engine, overlay, runs  # noqa: E402
from caliper.checks import CheckInputs, first_failure, run_checks  # noqa: E402
from caliper.models import AuditVerdict, MeasurementSpec, Result, Track, TrackFrame  # noqa: E402
from caliper.normalize import normalize  # noqa: E402
from caliper.pipeline import abstained  # noqa: E402
from caliper.segment import mask_geometry  # noqa: E402

log = logging.getLogger("placeholders")

FPS, W, H, N = 30.0, 640, 360, 75  # 2.5 s
BG = (15, 12, 10)  # BGR, close to the page background
BALL, OTHER, BOX = (60, 140, 235), (170, 170, 170), (225, 225, 225)
NOTE = "Placeholder: synthetic test clip drawn with OpenCV; masks from the drawing, spec typed."

Painter = Callable[[np.ndarray, dict[str, np.ndarray], float], None]


def draw_clip(paint: Painter, path: Path) -> dict[str, dict[int, np.ndarray]]:
    """Render N frames to path; return full-frame masks per object name per frame."""
    out = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
    masks: dict[str, dict[int, np.ndarray]] = {}
    for i in range(N):
        img = np.full((H, W, 3), BG, np.uint8)
        layers: dict[str, np.ndarray] = {}
        paint(img, layers, i / FPS)
        for name, m in layers.items():
            masks.setdefault(name, {})[i] = m
        out.write(img)
    out.release()
    return masks


def ball(img, layers, name, x, y, r, color):
    m = np.zeros((H, W), np.uint8)
    cv2.circle(m, (round(x), round(y)), r, 1, -1)
    img[m > 0] = color
    layers[name] = m


def box(img, layers, x0, y0, side):
    m = np.zeros((H, W), np.uint8)
    m[y0 : y0 + side, x0 : x0 + side] = 1
    img[m > 0] = BOX
    layers["white box"] = m


def track(name: str, masks: dict[int, np.ndarray]) -> Track:
    frames = []
    for i, m in sorted(masks.items()):
        area, centroid, extent = mask_geometry(m, 0, 0)
        if not area:
            continue
        ys, xs = np.nonzero(m)
        bbox = (float(xs.min()), float(ys.min()), float(xs.max() + 1), float(ys.max() + 1))
        frames.append(TrackFrame(frame=i, t_s=i / FPS, box=bbox, confidence=1.0, area_px=area,
                                 centroid_px=centroid, extent_px=extent))  # fmt: skip
    return Track(phrase=name, object_ordinal=0, frames=frames, fps=FPS, width=W, height=H)


def spec(target: str, box_m: float) -> MeasurementSpec:
    return MeasurementSpec(
        target_phrase=target, reference_phrase="white box", reference_kind="size",
        reference_statistic="extent", reference_axis="horizontal", reference_value_si=box_m,
        reference_source="question prior", quantity="speed", statistic="instantaneous",
        axis="path", timestamp_s=1.0, output_unit="m/s", depth_info=None,
        plausible_range_si=(0.1, 20.0),
    )  # fmt: skip


def measure(run_id: str, sp: MeasurementSpec, tgt: Track, ref: Track,
            verdict: AuditVerdict | None) -> tuple[Result, float]:  # fmt: skip
    """engine + checks as in pipeline.measure, with a scripted audit verdict if given."""
    m = engine.measure(sp, tgt, ref)
    checks = run_checks(CheckInputs(
        spec=sp, target=engine.Series.from_track(tgt), reference=engine.Series.from_track(ref),
        value_si=m.value_si, interval_si=m.interval_si, scale_m_per_px=m.scale_m_per_px,
        frame_width=W, clip_frames=N, fps=FPS,
    ))  # fmt: skip
    value = engine.to_unit(m.value_si, sp.output_unit)
    artifacts = {"video": run_id, "fps": FPS, "unchecked_value": value,
                 "bootstrap_ok": m.bootstrap_ok}  # fmt: skip
    reason = first_failure(checks, sp.target_phrase)
    if reason:
        result = abstained(reason, run_id, sp, m.method, artifacts, 0.0, checks)
    elif verdict is not None and not verdict.approve:
        result = abstained(f"Evidence check: {verdict.reason}", run_id, sp, m.method, artifacts,
                           0.0, checks, verdict)  # fmt: skip
    else:
        result = Result(
            run_id=run_id, status="measured", value=value, unit=sp.output_unit,
            interval_90=m.interval_si, quantity=sp.quantity, spec=sp,
            scale_m_per_px=m.scale_m_per_px, method=m.method, checks=checks, audit=verdict,
            abstain_reason=None, artifacts=artifacts, backend="meta_api", cost_usd=0.0,
            timings_ms={},
        )  # fmt: skip
    return result, m.scale_m_per_px


def save(run_id: str, title: str, question: str, painter: Painter, target: str, box_m: float,
         verdict: AuditVerdict | None = None, extra_note: str = "") -> Result:  # fmt: skip
    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / f"{run_id}.mp4"
        masks = draw_clip(painter, raw)
        clip = normalize(raw)
    tgt, ref = track(target, masks[target]), track("white box", masks["white box"])
    result, scale = measure(run_id, spec(target, box_m), tgt, ref, verdict)
    ov = overlay.build(tgt, ref, scale, "path", masks[target], masks["white box"])
    notes = " ".join(filter(None, [NOTE, extra_note]))
    meta = runs.RunMeta(title=title, question=question, source="placeholder_synthetic",
                        placeholder=True, notes=notes)  # fmt: skip
    runs.save_cached_run(run_id, "measure", result, ov, meta, clip)
    log.info("%s: %s %s", run_id, result.status, result.value or result.abstain_reason)
    return result


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    px_per_m = 40 / 0.5  # the 40 px box is 0.5 m

    def measured(img, layers, t):  # ball at 1.2 m/s, 40 px box
        box(img, layers, 540, 40, 40)
        ball(img, layers, "orange ball", 60 + 1.2 * px_per_m * t, 250, 14, BALL)

    def tiny_ref(img, layers, t):  # box drawn at 6 px: under MIN_REFERENCE_PX
        box(img, layers, 580, 40, 6)
        ball(img, layers, "orange ball", 60 + 1.2 * px_per_m * t, 250, 14, BALL)

    def two_balls(img, layers, t):  # the grey ball is tracked; the question asks for the orange
        box(img, layers, 540, 40, 40)
        ball(img, layers, "orange ball", 80 + 0.6 * px_per_m * t, 300, 14, BALL)
        ball(img, layers, "grey ball", 60 + 1.6 * px_per_m * t, 200, 14, OTHER)

    q = "How fast is the orange ball at 1.0 s in m/s? The white box is 50 cm wide."
    save("placeholder-measured", "Rolling ball (placeholder)", q, measured, "orange ball", 0.5)
    q_small = "How fast is the orange ball at 1.0 s in m/s? The white box is 7.5 cm wide."
    save("placeholder-check-abstain", "Reference too small (placeholder)", q_small, tiny_ref,
         "orange ball", 0.075)  # fmt: skip
    veto = AuditVerdict(
        target_is_right_object=False, reference_is_right_object=True, reference_same_plane="yes",
        occlusion_or_identity_switch=False, approve=False,
        reason="The outline follows the grey ball, but the question asks about the orange ball.",
    )  # fmt: skip
    save("placeholder-audit-veto", "Wrong ball tracked (placeholder)", q, two_balls, "grey ball",
         0.5, veto, "Audit verdict scripted for the placeholder; no model call.")  # fmt: skip


if __name__ == "__main__":
    main()
