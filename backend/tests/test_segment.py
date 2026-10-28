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


def _track(ordinal: int, xy: tuple[float, float], frames: list[int], area=100, conf=0.8):
    from caliper.models import Track, TrackFrame

    ext = {"horizontal": 10.0, "vertical": 10.0, "longest": 10.0, "shortest": 10.0, "disc": 10.0}
    fs = [
        TrackFrame(
            frame=f,
            t_s=f / 30,
            box=(0, 0, 1, 1),
            confidence=conf,
            area_px=area,
            centroid_px=xy,
            extent_px=ext,
        )  # fmt: skip
        for f in frames
    ]
    return Track(phrase="p", object_ordinal=ordinal, frames=fs, fps=30, width=640, height=360)


def test_select_instance_by_position_and_size():
    from caliper.segment import select_instance

    a = _track(0, (100, 50), list(range(30)), area=400)
    b = _track(1, (320, 300), list(range(30)), area=100)
    c = _track(2, (500, 180), list(range(30)), area=900)
    tracks = [a, b, c]
    assert select_instance(tracks, "left", 30)[0] is a
    assert select_instance(tracks, "right", 30)[0] is c
    assert select_instance(tracks, "middle", 30)[0] is b
    assert select_instance(tracks, "top", 30)[0] is a
    assert select_instance(tracks, "bottom", 30)[0] is b
    assert select_instance(tracks, "largest", 30)[0] is c
    assert select_instance(tracks, "smallest", 30)[0] is b
    assert select_instance(tracks, "center_rank:1", 30)[0] is b
    assert select_instance(tracks, "center_rank:3", 30)[0] is a


def test_select_instance_auto_longest_run_then_confidence():
    from caliper.segment import select_instance

    gappy = _track(0, (0, 0), [0, 1, 2, 4, 5, 6, 8, 9, 10, 12], conf=0.99)  # 10 frames, run 3
    steady = _track(1, (0, 0), list(range(5, 15)), conf=0.5)  # 10 frames, run 10
    chosen, rule = select_instance([gappy, steady], "auto", 15)
    assert chosen is steady and "longest continuous" in rule
    tie_low = _track(2, (0, 0), list(range(10)), conf=0.6)
    tie_high = _track(3, (0, 0), list(range(10)), conf=0.9)
    assert select_instance([tie_low, tie_high], "auto", 10)[0] is tie_high


def test_select_instance_drops_short_candidates():
    from caliper.segment import select_instance

    flicker = _track(0, (10, 10), [3, 4], area=5000)  # 2 of 30 frames
    real = _track(1, (600, 10), list(range(30)), area=100)
    chosen, rule = select_instance([flicker, real], "largest", 30)
    assert chosen is real and "1 short candidates dropped" in rule
    with pytest.raises(ValueError):
        select_instance([real], "sideways", 30)
