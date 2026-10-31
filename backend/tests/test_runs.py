"""Cached-run store: write, list, load, upsert, limits (tmp dir, no network)."""

import cv2
import numpy as np
import pytest

from caliper import runs
from caliper.models import MeasurementSpec, Result


def result(run_id: str = "r1", status: str = "measured") -> Result:
    spec = MeasurementSpec(
        target_phrase="disc", reference_phrase="square", reference_kind="size",
        reference_value_si=0.5, reference_source="test", quantity="speed",
        statistic="instantaneous", timestamp_s=1.0, output_unit="m/s", depth_info=None,
        plausible_range_si=(0, 10),
    )  # fmt: skip
    return Result(run_id=run_id, status=status, value=1.0, unit="m/s", interval_90=(0.9, 1.1),
                  quantity="speed", spec=spec, scale_m_per_px=0.01, method="m", checks=[],
                  audit=None, abstain_reason=None, artifacts={}, backend="meta_api",
                  cost_usd=0.0, timings_ms={})  # fmt: skip


def meta(**kw) -> runs.RunMeta:
    base = dict(title="t", question="q", source="placeholder_synthetic", placeholder=True)
    base.update(kw)
    return runs.RunMeta(**base)


def tiny_clip(path):
    out = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 10, (64, 48))
    for _ in range(3):
        out.write(np.full((48, 64, 3), 80, np.uint8))
    out.release()
    return path


def test_round_trip_with_clip_and_poster(tmp_path):
    root = tmp_path / "runs"
    runs.save_cached_run("r1", "measure", result(), {"frames": []}, meta(),
                         tiny_clip(tmp_path / "c.mp4"), root)  # fmt: skip
    run = runs.load_run("r1", root)
    assert run.schema_version == 1 and run.meta.placeholder
    assert (root / "r1" / "clip.mp4").exists() and (root / "r1" / "poster.jpg").exists()
    assert [e.run_id for e in runs.list_runs(root)] == ["r1"]


def test_upsert_and_real_runs_listed_first(tmp_path):
    runs.save_cached_run("b", "measure", result("b"), {}, meta(), root=tmp_path)
    runs.save_cached_run("a", "measure", result("a"), {}, meta(source="field", placeholder=False),
                         root=tmp_path)  # fmt: skip
    runs.save_cached_run("b", "measure", result("b", "abstained"), {}, meta(), root=tmp_path)
    entries = runs.list_runs(tmp_path)
    assert [e.run_id for e in entries] == ["a", "b"]
    assert entries[1].status == "abstained"
    assert runs.load_run("a", tmp_path).meta.clip is None


def test_rejects_bad_ids_and_missing_runs(tmp_path):
    with pytest.raises(runs.RunNotFound):
        runs.load_run("../secrets", tmp_path)
    with pytest.raises(runs.RunNotFound):
        runs.load_run("nope", tmp_path)


def test_rejects_large_clip(tmp_path):
    big = tmp_path / "big.mp4"
    big.write_bytes(b"0" * (runs.MAX_CLIP_BYTES + 1))
    with pytest.raises(ValueError, match="3 MB"):
        runs.save_cached_run("r", "measure", result(), {}, meta(), big, tmp_path / "runs")
