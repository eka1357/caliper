"""SAM 3.1 concept requests, stream parsing with meta-sam-parser, and the disk cache.

One concept per request (AGENTS.md section 3). The raw streamed text is cached, keyed by
sha256(video) + phrase + model + metadata (ARCHITECTURE section 5), and parsed offline,
so a rerun never calls the API.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from meta_sam_parser import (
    CompletedOutcome,
    SegmentationBoxRecord,
    SegmentationMaskRecord,
    decode_mask_to_raster,
    video_segmentation_format,
)
from meta_sam_parser import _segmentation as _parser_segmentation
from pydantic import BaseModel

from caliper import config
from caliper.meta_client import (
    DiskCache,
    cached_call,
    file_sha256,
    get_client,
    request_key,
    upload_file,
)
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
    raster = np.frombuffer(_decode_once(m), dtype=np.uint8).reshape(m.height, m.width)
    b = rec.bounds
    return mask_geometry(
        raster, b.left, b.top, (b.right - b.left) / m.width, (b.bottom - b.top) / m.height
    )


def parse_raw(raw: str) -> tuple[list[Detection], list[str]]:
    """Parse cached SAM stream text into detections. Reads the frame marker on every record.

    The lossless mask codec is pure Python and slow on large masks, so: each mask is decoded
    once (the parser's validation and the stats share it), streams above PARSE_PARALLEL_BYTES
    are parsed in parallel on whole-frame line groups, and the result is kept in a derived disk
    cache keyed by the raw text's sha256. Output is identical to a single serial parse.
    """
    cache_path = config.CACHE_DIR / "sam_parsed" / f"{_text_sha(raw)}.json"
    if cache_path.exists():
        doc = json.loads(cache_path.read_text(encoding="utf-8"))
        return [Detection(**d) for d in doc["detections"]], doc["diagnostics"]
    groups = _frame_line_groups(raw, PARSE_WORKERS) if len(raw) > PARSE_PARALLEL_BYTES else []
    if len(groups) > 1 and _frames_disjoint(groups):
        with ProcessPoolExecutor(max_workers=len(groups)) as pool:
            parts = list(pool.map(_parse_text, groups))
    else:  # small stream, or a frame split across groups (box prompts may come out of order)
        parts = [_parse_text((raw, 0))]
    detections = sorted((d for p in parts for d in p[0]), key=lambda d: (d.frame, d.object_id))
    diagnostics = [x for p in parts for x in p[1]]
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = cache_path.with_suffix(".tmp")
    tmp.write_text(
        json.dumps({"detections": [d.model_dump() for d in detections],
                    "diagnostics": diagnostics}),
        encoding="utf-8",
    )  # fmt: skip
    tmp.replace(cache_path)
    return detections, diagnostics


# Speed-only settings for parse_raw (no effect on any result).
PARSE_PARALLEL_BYTES = 300_000
PARSE_WORKERS = max(1, min(8, (os.cpu_count() or 2) - 1))
_FRAME_MARK = re.compile(r"^\s*<(\d+)f>")
_DECODED: dict[tuple[str, int, int, str], bytes] = {}


def _decode_once(mask: Any) -> bytes:
    """decode_mask_to_raster with a per-parse memo: the parser validates every mask by decoding
    it, and _mask_stats needs the same raster, so each payload is decoded once."""
    key = (mask.encoding, mask.width, mask.height, mask.payload)
    hit = _DECODED.get(key)
    if hit is None:
        hit = _DECODED[key] = decode_mask_to_raster(mask)
    return hit


# The parser's validation calls this module-level name; point it at the memo (same function,
# same errors, decoded once). Covered by test_parallel_parse_matches_serial.
_parser_segmentation.decode_mask_to_raster = _decode_once


def _text_sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _frame_line_groups(raw: str, n: int) -> list[tuple[str, int]]:
    """Split the stream into about n contiguous groups of lines, never splitting one frame's
    lines across groups. Returns (text, line offset) pairs."""
    lines = raw.splitlines(keepends=True)
    if n <= 1 or len(lines) < 2:
        return [(raw, 0)]
    target = len(raw) / n
    groups: list[tuple[str, int]] = []
    start, size, last_frame = 0, 0, None
    for i, line in enumerate(lines):
        m = _FRAME_MARK.match(line)
        frame = int(m.group(1)) if m else last_frame
        if size >= target and frame != last_frame and i > start:
            groups.append(("".join(lines[start:i]), start))
            start, size = i, 0
        size += len(line)
        last_frame = frame
    groups.append(("".join(lines[start:]), start))
    return groups


def _frames_disjoint(groups: list[tuple[str, int]]) -> bool:
    """True when no frame index appears in two groups, so per-group merging equals a full one."""
    seen: set[int] = set()
    for text, _ in groups:
        frames = {int(m.group(1)) for ln in text.splitlines() if (m := _FRAME_MARK.match(ln))}
        if frames & seen:
            return False
        seen |= frames
    return True


def _parse_text(part: tuple[str, int]) -> tuple[list[Detection], list[str]]:
    text, line_offset = part
    try:
        return _parse_serial(text, line_offset)
    finally:
        _DECODED.clear()


def _parse_serial(raw: str, line_offset: int = 0) -> tuple[list[Detection], list[str]]:
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
    diagnostics = [
        f"{d.severity} {d.code} line {d.line + line_offset if d.line is not None else d.line}: "
        f"{d.message}"
        for d in result.diagnostics
    ]
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

    Short candidates are dropped first (unless that drops all of them): for auto, those seen on
    fewer than INSTANCE_MIN_FRAME_SHARE of the clip's frames; for a comparative selector, those
    with fewer than FIT_MIN_POINTS frames, so a briefly seen second object still counts when the
    question names it by size or position (changed 2026-10-28 after dev: simulation_0089). Then:
    - left/right/top/bottom: extreme median centroid x or y over the frames each is seen;
    - middle: median centroid x closest to the median of all candidates' median x;
    - largest/smallest: median mask area;
    - center_rank:k: k-th closest to the frame centre (median centroid distance), 1 = closest;
    - auto: longest continuous run of frames, ties by mean confidence, then mean area.
    """
    if not tracks:
        raise ValueError("no tracks to select from")
    if selector == "auto":
        min_frames = config.INSTANCE_MIN_FRAME_SHARE * n_frames
    else:
        min_frames = config.FIT_MIN_POINTS
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


def same_object_conflict(
    target: Track, target_selector: str, others: list[tuple[Track | None, str, str]]
) -> str | None:
    """Reason to abstain when another role resolved to the target's own track although its
    selector differs (e.g. "largest" and "smallest" bird both landing on one bird)."""
    for other, selector, name in others:
        if other is target and selector != target_selector:
            return f"target and {name} resolved to the same object"
    return None


def mask_rasters(
    video: Path, phrase: str, object_id: str, frames: list[int], width: int, height: int,
    cache: DiskCache | None = None,
) -> dict[int, np.ndarray]:  # fmt: skip
    """Full-frame binary masks of one object on the given frames, from the cached SAM response.

    Cache only: returns {} when the segmentation is not cached (never calls the API).
    """
    payload = {
        "model": config.SAM_MODEL,
        "video_sha256": file_sha256(Path(video)),
        "phrase": phrase,
        "metadata": {"include_confidence": "true"},
    }
    record = (cache or DiskCache()).get(request_key({"kind": "sam", **payload}))
    if record is None:
        return {}
    wanted = set(frames)
    # Only the wanted frames' lines are parsed (each line carries its own frame marker), so the
    # slow mask codec runs on at most len(frames) lines instead of the whole stream.
    lines = [ln for ln in record["response"]["raw_output"].splitlines(keepends=True)
             if (m := _FRAME_MARK.match(ln)) is None or int(m.group(1)) in wanted]  # fmt: skip
    parser = video_segmentation_format().create_parser()
    parser.push("".join(lines), emit=False)
    out: dict[int, np.ndarray] = {}
    for rec in parser.finish(CompletedOutcome()).result.records:
        if not isinstance(rec, SegmentationMaskRecord) or rec.frame is None:
            continue
        f = rec.frame.frame_index
        if f not in wanted or rec.object_id != object_id:
            continue
        m, b = rec.mask, rec.bounds
        local = np.frombuffer(_decode_once(m), dtype=np.uint8).reshape(m.height, m.width)
        x0, y0 = int(round(b.left)), int(round(b.top))
        w, h = max(1, int(round(b.right - b.left))), max(1, int(round(b.bottom - b.top)))
        if (w, h) != (m.width, m.height):
            local = cv2.resize(local, (w, h), interpolation=cv2.INTER_NEAREST)
        full = np.zeros((height, width), np.uint8)
        x1, y1 = min(width, x0 + w), min(height, y0 + h)
        full[max(0, y0) : y1, max(0, x0) : x1] = local[max(0, -y0) : y1 - y0, max(0, -x0) : x1 - x0]
        out[f] = full
    _DECODED.clear()
    return out
