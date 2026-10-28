"""SAM 3.1 stream parsing. The committed fixture is synthetic (QuantiPhy-derived masks stay out
of the public repo); the second test checks the real cached Phase 0 smoke response when present.
"""

import json

import pytest
from meta_sam_parser._mask_codec import _encode_raster

from caliper import config
from caliper.meta_client import DiskCache, file_sha256, request_key
from caliper.segment import parse_raw


def _line(frame: int, obj: int, x1: int, y1: int, bits: list[int], w: int, h: int, c: float):
    # Same shape as a real sam-3.1 line: inclusive box corners, mask data=<height>,<width>,<payload>
    payload = _encode_raster(bits, w, h)
    return (
        f"<{frame}f>{obj}<|box;x1={x1};y1={y1};x2={x1 + w - 1};y2={y1 + h - 1};w=100;h=50;c={c}|>"
        f"<|mask;x=0;y=0;c={c};data={h},{w},{payload}|>"
    )


def test_parse_raw_merges_box_and_mask_per_frame_and_object():
    # 4x2 mask with the left two columns filled: area 4, centroid at (x1 + 1, y1 + 1)
    left_half = [1, 1, 0, 0, 1, 1, 0, 0]
    raw = "\n".join(
        [
            _line(5, 3, 10, 20, left_half, 4, 2, 0.5),
            _line(2, 0, 0, 0, [1] * 8, 4, 2, 0.9),  # out of order: frame marker decides
        ]
    )
    detections, diagnostics = parse_raw(raw)
    assert diagnostics == []
    assert [(d.frame, d.object_id) for d in detections] == [(2, "0"), (5, "3")]
    d = detections[1]
    assert d.box == (10, 20, 14, 22)  # half-open
    assert d.confidence == 0.5
    assert d.area_px == 4
    assert d.centroid_px == pytest.approx((11.0, 21.0))


def test_parse_raw_on_cached_smoke_response():
    video = config.NORMALIZED_DIR / "79c035962361884f.mp4"  # internet_0001, normalized
    if not video.exists():
        pytest.skip("Phase 0 smoke cache not present")
    payload = {
        "model": config.SAM_MODEL,
        "video_sha256": file_sha256(video),
        "phrase": "black car",
        "metadata": {"include_confidence": "true"},
    }
    record = DiskCache().get(request_key({"kind": "sam", **payload}))
    if record is None:
        pytest.skip("Phase 0 smoke cache not present")
    detections, diagnostics = parse_raw(record["response"]["raw_output"])
    assert diagnostics == []
    assert len({d.frame for d in detections}) == 30
    assert all(d.confidence is not None and 0 <= d.confidence <= 1 for d in detections)
    assert all(d.area_px and d.area_px > 0 for d in detections)
    json.dumps([d.model_dump() for d in detections])  # serializable for run JSON
