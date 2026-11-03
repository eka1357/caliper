"""API: caps refuse before the pipeline runs, cache hits are free, cached runs are served.

The pipeline, guess and ffprobe are replaced with fakes: no network, no video decoding.
"""

import json
import time
import uuid

import pytest
from fastapi.testclient import TestClient

from caliper import api, config, runs
from caliper.caps import Caps, CapSettings, SpendLedger
from caliper.meta_client import muse_cost_usd
from tests.test_runs import meta, result

USAGE = {"input_tokens": 10_000, "output_tokens": 2_000}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "API_RUNS_DIR", tmp_path / "api_runs")
    monkeypatch.setattr(config, "RUNS_DIR", tmp_path / "runs")
    monkeypatch.setattr(config, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(api, "probe", lambda path: {"fps": 30.0, "frames": 90})
    settings = CapSettings(enabled=True, max_clip_s=15, max_study_s=60, per_ip_per_hour=1,
                           per_run_usd=0.5, per_study_usd=1.5, daily_usd=5.0)  # fmt: skip
    api.app.state.caps = Caps(settings, SpendLedger(tmp_path / "spend"))
    runs.save_cached_run("placeholder-measured", "measure", result("placeholder-measured"), {},
                         meta(), root=tmp_path / "runs")  # fmt: skip
    calls = []
    new_records: list[dict] = [{"kind": "responses", "usage": USAGE}]  # API calls the run makes

    def fake_measure(path, question, prior, **kw):
        calls.append(kw)
        for rec in new_records:  # what meta_client would write on a cache miss
            d = config.CACHE_DIR / "api" / "ab"
            d.mkdir(parents=True, exist_ok=True)
            (d / f"{uuid.uuid4().hex}.json").write_text(json.dumps(rec), encoding="utf-8")
        r = result(kw["run_id"])
        r.cost_usd = 0.07
        r.artifacts["overlay"] = {"frames": [], "fit": [], "speed": []}
        return r

    monkeypatch.setattr(api.pipeline, "measure", fake_measure)
    with TestClient(api.app) as c:
        c.calls = calls
        c.new_records = new_records
        c.ledger = SpendLedger(tmp_path / "spend")
        yield c


def post(c, question="How fast is the ball in m/s?", data=b"video-bytes"):
    return c.post("/api/measure", data={"question": question},
                  files={"video": ("clip.mp4", data, "video/mp4")})  # fmt: skip


def test_health_and_cached_runs(client):
    h = client.get("/api/health").json()
    assert h["ok"] and h["live_runs_enabled"] and h["caps"]["per_run_cap_usd"] == 0.5
    listed = client.get("/api/runs").json()
    assert [r["run_id"] for r in listed] == ["placeholder-measured"]
    run = client.get("/api/runs/placeholder-measured").json()
    assert run["meta"]["placeholder"] is True
    assert client.get("/api/runs/missing").status_code == 404


def test_live_measure_uses_live_bootstrap_and_run_shape(client):
    r = post(client)
    assert r.status_code == 200
    body = r.json()
    assert body["kind"] == "measure" and body["meta"]["source"] == "live"
    assert "overlay" not in body["result"]["artifacts"] and body["overlay"]["frames"] == []
    assert client.calls[0]["bootstrap_b"] == config.LIVE_BOOTSTRAP_B
    assert client.calls[0]["with_overlay"] is True
    assert SpendLedger(config.API_RUNS_DIR.parent / "spend").total(time.time()) > 0


def test_ledger_counts_only_api_calls_made(client):
    """A Muse call and a SAM request made by the run are settled at their real cost; a run whose
    calls all came from the disk cache settles $0 even though result.cost_usd (from-scratch
    cost, 0.07 here) is not zero."""
    client.new_records[:] = [{"kind": "responses", "usage": USAGE}, {"kind": "sam"}]
    assert post(client).status_code == 200
    made = muse_cost_usd(USAGE) + 90 * config.SAM_USD_PER_FRAME  # fake probe: 90 frames
    assert client.ledger.total(time.time()) == pytest.approx(made)


def test_disk_cache_hits_settle_zero(client):
    client.new_records.clear()  # every API call answered from data/cache: nothing new written
    assert post(client).status_code == 200
    assert len(client.calls) == 1
    assert client.ledger.total(time.time()) == 0.0


def test_cache_hit_is_free_and_not_rate_limited(client):
    assert post(client).status_code == 200
    assert post(client).status_code == 200  # same clip and question: cache, no cap counted
    assert len(client.calls) == 1
    r = post(client, data=b"other-clip")  # new clip: the per-IP limit of 1 applies
    assert r.status_code == 429 and r.json()["code"] == "ip_rate"
    assert r.json()["cached_runs"][0]["run_id"] == "placeholder-measured"
    assert len(client.calls) == 1


def test_caps_refuse_before_pipeline(client, monkeypatch):
    monkeypatch.setattr(api, "probe", lambda path: {"fps": 30.0, "frames": 30 * 20})
    r = post(client)
    assert r.status_code == 429 and r.json()["code"] == "clip_too_long"
    assert client.calls == []


def test_live_disabled_is_503_with_cached_runs(client, tmp_path):
    api.app.state.caps = Caps(CapSettings(enabled=False), SpendLedger(tmp_path / "s2"))
    r = post(client)
    assert r.status_code == 503 and r.json()["cached_runs"]
    assert client.calls == []


def test_pipeline_failure_is_an_error_never_a_number(client, monkeypatch):
    def boom(*a, **kw):
        raise RuntimeError("sam down")

    monkeypatch.setattr(api.pipeline, "measure", boom)
    r = post(client)
    assert r.status_code == 500 and r.json() == {
        "code": "error",
        "message": "Something broke on our side.",
    }


def test_other_backend_and_study(client):
    r = client.post("/api/measure", data={"question": "How fast?", "backend": "x"},
                    files={"video": ("c.mp4", b"v", "video/mp4")})  # fmt: skip
    assert r.status_code == 400
    assert client.post("/api/study").status_code == 503
