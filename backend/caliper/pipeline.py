"""measure(video, question, prior=None) -> Result (ARCHITECTURE section 2).

normalize -> spec (Muse Spark call 1, unless a spec is passed in) -> segment (SAM 3.1, one
request per phrase; alternative phrases are tried with SAM only when a phrase finds nothing)
-> instance selection -> engine -> Result. Checks and the audit come in Phase 3.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from caliper import audit as audit_step
from caliper import config, engine
from caliper.backends import LanguageBackend
from caliper.checks import CheckInputs, first_failure, run_checks, window_frames
from caliper.engine import Abstain
from caliper.models import AuditVerdict, Check, MeasurementSpec, Result, Track
from caliper.normalize import normalize, probe
from caliper.segment import (
    sam_cost_usd,
    same_object_conflict,
    segment,
    select_instance,
    tracks_from_segmentation,
)
from caliper.spec import SpecError, write_spec

log = logging.getLogger(__name__)


class VideoContext:
    """A normalized video with its probed time base and its segmentations, one per phrase."""

    def __init__(self, src: Path, name: str = "", dataset_fps: float | None = None) -> None:
        self.name = name or Path(src).stem
        self.path = normalize(src)
        info = probe(self.path)
        self.fps, self.frames = float(info["fps"]), int(info["frames"])
        self.width, self.height = int(info["width"]), int(info["height"])
        self.fps_mismatch = None
        if dataset_fps is not None and abs(self.fps - dataset_fps) > config.FPS_MISMATCH_TOL:
            self.fps_mismatch = {"probed": self.fps, "dataset": dataset_fps}
            log.warning("%s: ffprobe fps %.4f, dataset fps %s", self.name, self.fps, dataset_fps)
        self._tracks: dict[str, list[Track]] = {}

    def tracks(self, phrase: str) -> list[Track]:
        if phrase not in self._tracks:
            seg = segment(self.path, phrase)
            self._tracks[phrase] = tracks_from_segmentation(seg, self.fps, self.width, self.height)
        return self._tracks[phrase]

    def pick(
        self, phrases: list[str], selector: str, tried: set[str] | None = None
    ) -> tuple[Track, str, str]:
        """First phrase (main, then alternatives) that finds anything; then select one instance.

        Returns (track, rule, phrase used); adds each phrase sent to SAM to `tried`.
        Alternatives cost SAM requests only, no model call.
        """
        for phrase in phrases:
            if tried is not None:
                tried.add(phrase)
            tracks = self.tracks(phrase)
            if tracks:
                try:
                    track, rule = select_instance(tracks, selector, self.frames)
                except ValueError as exc:  # e.g. center_rank:4 with fewer candidates found
                    raise Abstain(f"'{phrase}': {exc}") from exc
                return track, rule, phrase
        tried = ", ".join(f"'{p}'" for p in phrases)
        raise Abstain(f"SAM found no {tried}")


def _stub_spec() -> MeasurementSpec:
    return MeasurementSpec(
        target_phrase="", reference_phrase=None, reference_kind="given_prior",
        reference_value_si=None, reference_source="", quantity="size", statistic="extent",
        timestamp_s=None, output_unit="", depth_info=None, plausible_range_si=(0, 0),
    )  # fmt: skip


def abstained(
    reason: str, run_id: str, spec: MeasurementSpec | None = None, method: str = "",
    artifacts: dict | None = None, cost_usd: float = 0.0, checks: list[Check] | None = None,
    audit: AuditVerdict | None = None,
) -> Result:  # fmt: skip
    spec = spec or _stub_spec()
    return Result(
        run_id=run_id, status="abstained", value=None, unit=spec.output_unit, interval_90=None,
        quantity=spec.quantity, spec=spec, scale_m_per_px=None, method=method,
        checks=checks or [], audit=audit, abstain_reason=reason, artifacts=artifacts or {},
        backend="meta_api",
        cost_usd=cost_usd, timings_ms={},
    )  # fmt: skip


def measure(
    video: Path | VideoContext,
    question: str,
    prior: str | None = None,
    *,
    spec: MeasurementSpec | None = None,
    depth_info: dict | None = None,
    run_id: str = "",
    backend: LanguageBackend | None = None,
    audit: bool | None = None,
) -> Result:
    """One question on one video. Abstains (never guesses) when any step cannot support a number."""
    ctx = video if isinstance(video, VideoContext) else VideoContext(video)
    artifacts: dict[str, Any] = {
        "video": ctx.name,
        "fps": ctx.fps,
        "fps_mismatch": ctx.fps_mismatch,
    }
    muse_cost = 0.0
    if spec is None:
        try:
            spec, info = write_spec(ctx.path, question, prior, depth_info, backend)
        except SpecError as exc:
            return abstained(str(exc), run_id, method="spec writer", artifacts=artifacts)
        muse_cost = info["cost_usd"]
        artifacts["spec_call"] = {k: info[k] for k in ("usage", "cost_usd", "latency_ms")}
    tried: set[str] = set()

    def cost() -> float:
        """Cost of this question from scratch: the spec call plus every SAM phrase it tried."""
        artifacts["phrases_tried"] = sorted(tried)
        return muse_cost + sam_cost_usd(ctx.frames * len(tried))

    try:
        target, t_rule, t_phrase = ctx.pick([spec.target_phrase, *spec.target_alt_phrases],
                                            spec.target_instance, tried)  # fmt: skip
        second, s_rule, s_phrase = (
            ctx.pick([spec.second_phrase], spec.second_instance, tried)
            if spec.second_phrase
            else (None, "", None)
        )
        if spec.reference_phrase:
            reference, r_rule, r_phrase = ctx.pick(
                [spec.reference_phrase, *spec.reference_alt_phrases],
                spec.reference_instance,
                tried,
            )
        else:
            reference, r_rule, r_phrase = None, "reference = target", None
        artifacts["instances"] = {"target": t_rule, "second": s_rule, "reference": r_rule}
        artifacts["phrases_used"] = {"target": t_phrase, "second": s_phrase, "reference": r_phrase}
        conflict = same_object_conflict(
            target,
            spec.target_instance,
            [(second, spec.second_instance, "second object"),
             (reference, spec.reference_instance, "reference")],
        )  # fmt: skip
        if conflict:
            raise Abstain(conflict)
        artifacts["detected_frames"] = {
            "target": len(target.frames),
            "second": len(second.frames) if second else None,
            "reference": len(reference.frames) if reference else None,
            "clip": ctx.frames,
        }
        m = engine.measure(spec, target, reference, second)
    except Abstain as exc:
        return abstained(str(exc), run_id, spec, "engine", artifacts, cost())
    interval = (
        tuple(engine.to_unit(x, spec.output_unit) for x in m.interval_si) if m.interval_si else None
    )
    value = engine.to_unit(m.value_si, spec.output_unit)
    artifacts.update(value_px=m.value_px, bootstrap_ok=m.bootstrap_ok, unchecked_value=value,
                     unchecked_interval=interval)  # fmt: skip
    inputs = CheckInputs(
        spec=spec,
        target=engine.Series.from_track(target),
        reference=engine.Series.from_track(reference) if reference is not None else None,
        value_si=m.value_si,
        interval_si=m.interval_si,
        scale_m_per_px=m.scale_m_per_px,
        frame_width=ctx.width,
        clip_frames=ctx.frames,
        fps=ctx.fps,
        use_depth=spec.depth_info is not None,
    )
    checks = run_checks(inputs)
    reason = first_failure(checks, spec.target_phrase) if config.CHECKS_ENABLED else None
    if reason:
        return abstained(reason, run_id, spec, m.method, artifacts, cost(), checks)
    verdict = None
    if config.AUDIT_ENABLED if audit is None else audit:
        verdict, info = audit_step.audit(ctx.path, question, spec, target, reference,
                                         window_frames(inputs), backend)  # fmt: skip
        muse_cost += info["cost_usd"]
        artifacts["audit_call"] = {k: info.get(k) for k in ("usage", "cost_usd", "keyframes")}
        if not verdict.approve:
            return abstained(f"Evidence check: {verdict.reason}", run_id, spec, m.method,
                             artifacts, cost(), checks, verdict)  # fmt: skip
    return Result(
        run_id=run_id, status="measured", value=value,
        unit=spec.output_unit, interval_90=interval, quantity=spec.quantity, spec=spec,
        scale_m_per_px=m.scale_m_per_px, method=m.method, checks=checks, audit=verdict,
        abstain_reason=None, artifacts=artifacts, backend="meta_api", cost_usd=cost(),
        timings_ms={},
    )  # fmt: skip
