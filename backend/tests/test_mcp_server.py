"""MCP tools on cached field runs ($0): the API base URL points at a dead port, so a cache miss
fails the test instead of spending. Skipped when the field clips or the cache are not on disk."""

from __future__ import annotations

import asyncio
import json
import time

import pytest

from caliper import config, mcp_server, meta_client
from caliper.caps import Caps, CapSettings, SpendLedger
from caliper.models import Result, StudySummary

C07 = config.FIELD_DIR / "C_07.MOV"
A04 = config.FIELD_DIR / "A_04.MOV"
C07_RUN = config.CACHE_DIR / "field_runs" / "C07.json"


@pytest.fixture
def offline(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "META_API_BASE_URL", "http://127.0.0.1:9/v1")
    monkeypatch.setenv("MODEL_API_KEY", "offline-test")
    monkeypatch.setattr(meta_client, "_client", None)
    settings = CapSettings(enabled=True, max_clip_s=600, max_study_s=600, per_run_usd=5,
                           per_study_usd=5, daily_usd=50)  # fmt: skip
    ledger = SpendLedger(tmp_path / "spend")
    mcp_server.set_caps(Caps(settings, ledger))
    yield ledger
    mcp_server.set_caps(None)
    meta_client._client = None


def test_tools_are_listed_with_schemas():
    tools = {t.name: t for t in asyncio.run(mcp_server.server.list_tools())}
    assert set(tools) == {"measure", "study"}
    assert set(tools["measure"].input_schema["required"]) == {"video_path", "question"}
    assert set(tools["study"].input_schema["required"]) == {"video_path", "gates", "distance_m"}
    assert tools["measure"].output_schema is not None  # structured output from Result


@pytest.mark.skipif(not (C07.exists() and C07_RUN.exists()), reason="field clip C07 not on disk")
def test_measure_replays_cached_c07(offline):
    rec = json.loads(C07_RUN.read_text(encoding="utf-8"))
    res = mcp_server.measure(str(C07), "What is the length of the phone in cm?", rec["prior"])
    assert isinstance(res, Result)
    assert res.status == rec["result"]["status"] == "measured"
    assert res.value == pytest.approx(rec["result"]["value"], rel=1e-9)
    assert res.unit == rec["result"]["unit"]
    assert offline.total(time.time()) == 0.0  # every call was a cache hit: nothing settled


@pytest.mark.skipif(not A04.exists(), reason="field clip A04 not on disk")
def test_study_on_cached_a04_segmentation(offline):
    gates = mcp_server.StudyGates(
        gate_a={"a": (400.0, 0.0), "b": (400.0, 720.0)},
        gate_b={"a": (880.0, 0.0), "b": (880.0, 720.0)},
    )
    s = mcp_server.study(str(A04), gates, 10.0, vehicle_classes=["gray car"])
    assert isinstance(s, StudySummary)
    assert s.gate_distance_m == 10.0
    assert s.vehicles_seen == len(s.readings) >= 1
    for r in s.readings:
        assert (r.status == "measured") == (r.speed_kmh is not None)
        assert r.status == "measured" or r.reason


def test_study_refuses_a_non_positive_distance(tmp_path):
    gates = mcp_server.StudyGates(
        gate_a={"a": (0, 0), "b": (0, 1)}, gate_b={"a": (1, 0), "b": (1, 1)}
    )
    with pytest.raises(ValueError, match="distance_m"):
        mcp_server.study(str(tmp_path / "x.mp4"), gates, 0.0)
