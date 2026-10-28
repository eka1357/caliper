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

log = logging.getLogger(__name__)


class Detection(BaseModel):
    """One object in one frame, in source-video pixel coordinates."""

    frame: int
    object_id: str
    box: tuple[float, float, float, float]  # left, top, right, bottom (half-open)
    confidence: float | None
    area_px: int | None  # mask pixel count; None when the line had no mask
    centroid_px: tuple[float, float] | None


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


def _mask_stats(rec: SegmentationMaskRecord) -> tuple[int, tuple[float, float] | None]:
    """Pixel count and centroid of a box-local mask, mapped into frame coordinates."""
    m = rec.mask
    raster = np.frombuffer(decode_mask_to_raster(m), dtype=np.uint8).reshape(m.height, m.width)
    ys, xs = np.nonzero(raster)
    if xs.size == 0:
        return 0, None
    b = rec.bounds
    sx = (b.right - b.left) / m.width
    sy = (b.bottom - b.top) / m.height
    cx = b.left + (xs.mean() + 0.5) * sx
    cy = b.top + (ys.mean() + 0.5) * sy
    return int(round(xs.size * sx * sy)), (float(cx), float(cy))


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
            slot["area_px"], slot["centroid_px"] = _mask_stats(rec)
    detections = [
        Detection(
            frame=frame,
            object_id=oid,
            box=v["box"],
            confidence=v.get("confidence"),
            area_px=v.get("area_px"),
            centroid_px=v.get("centroid_px"),
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
