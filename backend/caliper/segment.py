"""SAM 3.1 concept requests, stream parsing with meta-sam-parser, and the disk cache.

One concept per request (AGENTS.md section 3). The raw streamed text is cached, keyed by
sha256(video) + phrase + model + metadata (ARCHITECTURE section 5), and parsed offline,
so a rerun never calls the API.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from meta_sam_parser import (
    CompletedOutcome,
    SegmentationBoxRecord,
    SegmentationMaskRecord,
    decode_mask_to_raster,
    video_segmentation_format,
)
from pydantic import BaseModel

from caliper import config
from caliper.meta_client import DiskCache, cached_call, file_sha256, get_client, upload_file
from caliper.models import Track, TrackFrame

log = logging.getLogger(__name__)


class Detection(BaseModel):
    """One object in one frame, in source-video pixel coordinates."""

    frame: int
    object_id: str
    box: tuple[float, float, float, float]  # left, top, right, bottom (half-open)
    confidence: float | None
    area_px: int | None  # mask pixel count; None when the line had no mask
    centroid_px: tuple[float, float] | None
    extent_px: dict[str, float] | None = None  # see mask_geometry


class Segmentation(BaseModel):
    phrase: str
    model: str
    detections: list[Detection]
    diagnostics: list[str]
    frames_returned: int
    latency_ms: float
    cache_hit: bool

    def objects_per_frame(self) -> dict[int, int]:
        counts: dict[int, set[str]] = defaultdict(set)
        for d in self.detections:
            counts[d.frame].add(d.object_id)
        return {f: len(ids) for f, ids in sorted(counts.items())}


def _request_sam(file_id: str, phrase: str, metadata: dict[str, str]) -> tuple[Any, dict[str, int]]:
    stream = get_client().responses.create(
        model=config.SAM_MODEL,
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": phrase},
                    {"type": "input_video", "file_id": file_id},
                ],
            }
        ],
        metadata=metadata,
        stream=True,
    )
    parts: list[str] = []
    status = "incomplete"
    for event in stream:
        etype = getattr(event, "type", "")
        if etype == "response.output_text.delta":
            parts.append(event.delta)
        elif etype == "response.completed":
            status = "completed"
        elif etype in ("response.failed", "error"):
            raise RuntimeError(f"SAM stream failed: {event}")
    return {"raw_output": "".join(parts), "status": status}, {"input_tokens": 0, "output_tokens": 0}


def mask_geometry(
    raster: np.ndarray, left: float, top: float, sx: float = 1.0, sy: float = 1.0
) -> tuple[int, tuple[float, float] | None, dict[str, float] | None]:
    """Area, centroid and extents of a binary mask placed at (left, top) with pixel size sx, sy.

    Extents in frame pixels: horizontal, vertical, longest and shortest (along the principal
    axes of the mask pixels), and disc (diameter of the circle with the same area).
    """
    ys, xs = np.nonzero(raster)
    if xs.size == 0:
        return 0, None, None
    px = left + (xs + 0.5) * sx
    py = top + (ys + 0.5) * sy
    area = xs.size * sx * sy
    extent = {
        "horizontal": float(np.ptp(px) + sx),
        "vertical": float(np.ptp(py) + sy),
        "disc": float(2 * np.sqrt(area / np.pi)),
    }
    pts = np.stack([px - px.mean(), py - py.mean()], axis=1)
    if xs.size >= 3:
        _, _, vt = np.linalg.svd(pts, full_matrices=False)
        proj = pts @ vt.T
        spans = np.ptp(proj, axis=0) + (sx + sy) / 2
        extent["longest"], extent["shortest"] = float(spans.max()), float(spans.min())
    else:
        extent["longest"] = max(extent["horizontal"], extent["vertical"])
        extent["shortest"] = min(extent["horizontal"], extent["vertical"])
    return int(round(area)), (float(px.mean()), float(py.mean())), extent


def _mask_stats(
    rec: SegmentationMaskRecord,
) -> tuple[int, tuple[float, float] | None, dict[str, float] | None]:
    """Pixel count, centroid and extents of a box-local mask, mapped into frame coordinates."""
    m = rec.mask
    raster = np.frombuffer(decode_mask_to_raster(m), dtype=np.uint8).reshape(m.height, m.width)
    b = rec.bounds
    return mask_geometry(
        raster, b.left, b.top, (b.right - b.left) / m.width, (b.bottom - b.top) / m.height
    )


def parse_raw(raw: str) -> tuple[list[Detection], list[str]]:
    """Parse cached SAM stream text into detections. Reads the frame marker on every record."""
    parser = video_segmentation_format().create_parser()
    parser.push(raw, emit=False)
    result = parser.finish(CompletedOutcome()).result
    merged: dict[tuple[int, str], dict[str, Any]] = {}
    for rec in result.records:
        if not isinstance(rec, SegmentationBoxRecord | SegmentationMaskRecord) or rec.frame is None:
            continue
        slot = merged.setdefault((rec.frame.frame_index, rec.object_id), {})
        if rec.confidence is not None:
            slot["confidence"] = rec.confidence
        if isinstance(rec, SegmentationBoxRecord):
            slot["box"] = (rec.left, rec.top, rec.right, rec.bottom)
        else:
            b = rec.bounds
            slot.setdefault("box", (b.left, b.top, b.right, b.bottom))
            slot["area_px"], slot["centroid_px"], slot["extent_px"] = _mask_stats(rec)
    detections = [
        Detection(
            frame=frame,
            object_id=oid,
            box=v["box"],
            confidence=v.get("confidence"),
            area_px=v.get("area_px"),
            centroid_px=v.get("centroid_px"),
            extent_px=v.get("extent_px"),
        )
        for (frame, oid), v in sorted(merged.items())
    ]
    diagnostics = [f"{d.severity} {d.code} line {d.line}: {d.message}" for d in result.diagnostics]
    return detections, diagnostics


def segment(
    video: Path, phrase: str, include_confidence: bool = True, cache: DiskCache | None = None
) -> Segmentation:
    """Track one concept in a (normalized) video. One SAM request, cached."""
    video = Path(video)
    metadata = {"include_confidence": "true" if include_confidence else "false"}
    payload = {
        "model": config.SAM_MODEL,
        "video_sha256": file_sha256(video),
        "phrase": phrase,
        "metadata": metadata,
    }

    def call() -> tuple[Any, dict[str, int]]:
        return _request_sam(upload_file(video, cache), phrase, metadata)

    record, hit = cached_call("sam", payload, call, cache)
    detections, diagnostics = parse_raw(record["response"]["raw_output"])
    return Segmentation(
        phrase=phrase,
        model=config.SAM_MODEL,
        detections=detections,
        diagnostics=diagnostics,
        frames_returned=len({d.frame for d in detections}),
        latency_ms=record["latency_ms"],
        cache_hit=hit,
    )


def sam_cost_usd(frames: int) -> float:
    """SAM 3.1 is billed per video frame (AGENTS.md section 3)."""
    return frames * config.SAM_USD_PER_FRAME


def tracks_from_segmentation(seg: Segmentation, fps: float, width: int, height: int) -> list[Track]:
    """One Track per SAM object ordinal, frames with a mask only. Time base is the probed fps."""
    by_obj: dict[str, list[TrackFrame]] = defaultdict(list)
    for d in seg.detections:
        if not d.area_px or d.centroid_px is None or d.extent_px is None:
            continue
        by_obj[d.object_id].append(
            TrackFrame(
                frame=d.frame,
                t_s=d.frame / fps,
                box=d.box,
                confidence=d.confidence,
                area_px=d.area_px,
                centroid_px=d.centroid_px,
                extent_px=d.extent_px,
            )
        )
    return [
        Track(
            phrase=seg.phrase,
            object_ordinal=int(oid),
            frames=frames,
            fps=fps,
            width=width,
            height=height,
        )  # fmt: skip
        for oid, frames in sorted(by_obj.items(), key=lambda kv: int(kv[0]))
    ]


def _longest_run(track: Track) -> int:
    frames = [f.frame for f in track.frames]
    best = run = 1 if frames else 0
    for a, b in zip(frames, frames[1:], strict=False):
        run = run + 1 if b == a + 1 else 1
        best = max(best, run)
    return best


def _auto_key(track: Track) -> tuple[int, float, float]:
    confs = [f.confidence for f in track.frames if f.confidence is not None]
    return (
        _longest_run(track),
        float(np.mean(confs)) if confs else 0.0,
        float(np.mean([f.area_px for f in track.frames])),
    )


def select_instance(tracks: list[Track], selector: str, n_frames: int) -> tuple[Track, str]:
    """Pick one instance deterministically; return it with a description of the rule used.

    Candidates seen on fewer than INSTANCE_MIN_FRAME_SHARE of the clip's frames are dropped
    first (unless that drops all of them). Then:
    - left/right/top/bottom: extreme median centroid x or y over the frames each is seen;
    - middle: median centroid x closest to the median of all candidates' median x;
    - largest/smallest: median mask area;
    - center_rank:k: k-th closest to the frame centre (median centroid distance), 1 = closest;
    - auto: longest continuous run of frames, ties by mean confidence, then mean area.
    """
    if not tracks:
        raise ValueError("no tracks to select from")
    min_frames = config.INSTANCE_MIN_FRAME_SHARE * n_frames
    pool = [t for t in tracks if len(t.frames) >= min_frames] or list(tracks)
    dropped = len(tracks) - len(pool)

    def med(t: Track, i: int) -> float:
        return float(np.median([f.centroid_px[i] for f in t.frames]))

    if selector in ("left", "right"):
        chosen = sorted(pool, key=lambda t: med(t, 0))[0 if selector == "left" else -1]
        rule = f"{selector}most median centroid x"
    elif selector in ("top", "bottom"):
        chosen = sorted(pool, key=lambda t: med(t, 1))[0 if selector == "top" else -1]
        rule = f"{selector}most median centroid y"
    elif selector == "middle":
        centre = float(np.median([med(t, 0) for t in pool]))
        chosen = min(pool, key=lambda t: abs(med(t, 0) - centre))
        rule = "median centroid x closest to the middle of the candidates"
    elif selector in ("largest", "smallest"):
        areas = sorted(pool, key=lambda t: float(np.median([f.area_px for f in t.frames])))
        chosen = areas[-1 if selector == "largest" else 0]
        rule = f"{selector} median mask area"
    elif selector.startswith("center_rank:"):
        k = int(selector.split(":", 1)[1])
        cx, cy = pool[0].width / 2, pool[0].height / 2
        ranked = sorted(pool, key=lambda t: np.hypot(med(t, 0) - cx, med(t, 1) - cy))
        if k > len(ranked):
            raise ValueError(f"{selector}: only {len(ranked)} candidates")
        chosen = ranked[k - 1]
        rule = f"rank {k} by median distance from the frame centre"
    elif selector == "auto":
        chosen = max(pool, key=_auto_key)
        rule = "longest continuous track, ties by mean confidence then mean area"
    else:
        raise ValueError(f"unknown instance selector {selector!r}")
    note = f"; {dropped} short candidates dropped" if dropped else ""
    return chosen, f"instance {chosen.object_ordinal} of {len(tracks)}: {rule}{note}"
