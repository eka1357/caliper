"""Data contracts (ARCHITECTURE section 3). pydantic v2 at every boundary."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

Quantity = Literal["size", "speed", "acceleration"]  # MVP
# separation: distance between two objects at a time; orbit_diameter: twice the median distance
# from a centre object (added 2026-10-28 for QuantiPhy dev 2D, see DECISIONS.md)
Statistic = Literal["instantaneous", "average", "extent", "separation", "orbit_diameter"]
# How to pick one instance when a phrase matches several objects (segment.select_instance).
# center_rank:k = k-th closest to the frame centre by median centroid distance (1 = closest).
Instance = str  # "auto" | left | right | middle | top | bottom | largest | smallest | center_rank:k
# disc: diameter of the circle with the mask's area; shortest/longest: principal-axis extents
Axis = Literal["path", "horizontal", "vertical", "longest", "shortest", "disc"]
TimeAnchor = Literal["timestamp", "first", "last"]


class Prior(BaseModel):
    kind: Literal["size", "speed", "given_depth"]
    object_phrase: str  # what the prior describes, e.g. "lane width"
    value: float
    unit: str  # SI after conversion: m, m/s


class MeasurementSpec(BaseModel):
    target_phrase: str  # SAM concept prompt, short noun phrase
    target_alt_phrases: list[str] = []
    target_instance: Instance = "auto"
    second_phrase: str | None = None  # separation / orbit_diameter: the other object
    second_instance: Instance = "auto"
    reference_phrase: str | None  # None when the prior describes the target itself
    reference_alt_phrases: list[str] = []  # tried with SAM only when the main phrase finds nothing
    reference_instance: Instance = "auto"
    reference_kind: Literal["size", "speed", "acceleration", "given_prior", "known_object"]
    reference_statistic: Literal["extent", "average_speed", "acceleration"] = "extent"
    reference_axis: Axis = "longest"
    reference_value_si: float | None
    reference_source: str  # "question prior", or "world knowledge: INR 10 coin is 27 mm"
    quantity: Quantity
    statistic: Statistic
    axis: Axis = "path"
    timestamp_s: float | None
    time_anchor: TimeAnchor = "timestamp"
    time_range_s: tuple[float, float] | None = None  # average over a window of the clip
    output_unit: str  # unit the question asks for
    depth_info: dict | None  # QuantiPhy 3D field, passed through untouched
    plausible_range_si: tuple[float, float]  # sanity bounds proposed by the model
    notes: str = ""


class TrackFrame(BaseModel):
    frame: int
    t_s: float
    box: tuple[float, float, float, float]  # left, top, right, bottom (half-open)
    confidence: float | None
    area_px: int
    centroid_px: tuple[float, float]
    extent_px: dict[str, float]  # horizontal, vertical, longest, shortest, disc


class Track(BaseModel):
    phrase: str
    object_ordinal: int
    frames: list[TrackFrame]
    fps: float
    width: int
    height: int


class Check(BaseModel):
    name: str
    passed: bool
    value: float | None
    threshold: str
    detail: str


class AuditVerdict(BaseModel):
    target_is_right_object: bool
    reference_is_right_object: bool
    reference_same_plane: Literal["yes", "no", "unclear"]
    occlusion_or_identity_switch: bool
    approve: bool  # false means veto
    reason: str  # one sentence shown to the user on veto


class Result(BaseModel):
    run_id: str
    status: Literal["measured", "abstained"]
    value: float | None
    unit: str
    interval_90: tuple[float, float] | None
    quantity: Quantity
    spec: MeasurementSpec
    scale_m_per_px: float | None
    method: str  # e.g. "centroid, local quadratic, window 0.30 s"
    checks: list[Check]
    audit: AuditVerdict | None
    abstain_reason: str | None
    artifacts: dict  # overlay frames, fit series, URLs
    backend: Literal["meta_api", "muse_spark_open"]
    cost_usd: float
    timings_ms: dict
