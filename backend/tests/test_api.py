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
    assert client.post("/api/study").status_code == 422  # built now: missing fields are refused


# ---- POST /api/study (study_live.run_study replaced: no SAM, no video decoding) ----

GATES = {"gate_a": "[[200, 0], [200, 720]]", "gate_b": "[[1010, 0], [1010, 720]]"}


@pytest.fixture
def study_client(client, monkeypatch):
    from caliper.models import StudySummary, VehicleReading

    calls = []

    def fake_run_study(path, gate_a, gate_b, distance_m, run_id, classes, limit, frame_size):
        calls.append({"gates": (gate_a, gate_b), "distance": distance_m, "classes": classes,
                      "limit": limit, "frame_size": frame_size})  # fmt: skip
        d = config.CACHE_DIR / "api" / "cd"  # one SAM request made by this study
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{uuid.uuid4().hex}.json").write_text(json.dumps({"kind": "sam"}), encoding="utf-8")
        r = VehicleReading(vehicle_id="car-0", vehicle_class="car", status="measured",
                           speed_kmh=30.0, interval_90_kmh=(29.5, 30.5), t_gate_a_s=0.5,
                           t_gate_b_s=1.45, reason=None)  # fmt: skip
        s = StudySummary(run_id=run_id, gate_distance_m=distance_m, duration_s=3.0,
                         vehicles_seen=1, vehicles_measured=1, median_kmh=30.0, p85_kmh=30.0,
                         p85_interval_90_kmh=(29.5, 30.5), speed_limit_kmh=limit,
                         share_over_limit=None, readings=[r])  # fmt: skip
        return s, {"fps": 30.0, "width": 1280, "height": 720, "gate_a": [[200, 0], [200, 720]],
                   "gate_b": [[1010, 0], [1010, 720]], "vehicles": []}  # fmt: skip

    monkeypatch.setattr(api.study_live, "run_study", fake_run_study)
    client.study_calls = calls
    return client


def post_study(c, data=b"street-bytes", **extra):
    form = {**GATES, "gate_distance_m": "7.92", **extra}
    return c.post("/api/study", data=form, files={"video": ("street.mp4", data, "video/mp4")})


def test_live_study_returns_a_study_run_and_settles_only_calls_made(study_client):
    r = post_study(study_client, speed_limit_kmh="30", frame_width="3840", frame_height="2160")
    assert r.status_code == 200
    body = r.json()
    assert body["kind"] == "study" and body["meta"]["source"] == "live"
    assert body["result"]["vehicles_measured"] == 1 and body["result"]["speed_limit_kmh"] == 30
    call = study_client.study_calls[0]
    assert call["distance"] == 7.92 and call["frame_size"] == (3840.0, 2160.0)
    assert call["gates"] == (((200.0, 0.0), (200.0, 720.0)), ((1010.0, 0.0), (1010.0, 720.0)))
    assert call["classes"] == api.study_live.VEHICLE_CLASSES
    # one SAM request over the fake probe's 90 frames, nothing for cache hits
    assert study_client.ledger.total(time.time()) == pytest.approx(90 * config.SAM_USD_PER_FRAME)


def test_repeat_study_is_a_free_cache_hit(study_client):
    assert post_study(study_client).status_code == 200
    again = post_study(study_client)  # same clip, gates and distance: no cap counted (limit 1/h)
    assert again.status_code == 200 and len(study_client.study_calls) == 1
    other = post_study(study_client, data=b"other-street")
    assert other.status_code == 429 and other.json()["code"] == "ip_rate"


def test_recorded_study_run_is_served(study_client, tmp_path):
    from caliper.models import StudySummary

    s = StudySummary(run_id="study-a14", gate_distance_m=7.92, duration_s=2.3, vehicles_seen=0,
                     vehicles_measured=0, median_kmh=None, p85_kmh=None, p85_interval_90_kmh=None,
                     speed_limit_kmh=None, share_over_limit=None, readings=[])  # fmt: skip
    runs.save_cached_run("study-a14", "study", s.model_dump(mode="json"), {}, meta(),
                         root=tmp_path / "runs")  # fmt: skip
    listed = {r["run_id"]: r["kind"] for r in study_client.get("/api/runs").json()}
    assert listed["study-a14"] == "study"
    assert study_client.get("/api/runs/study-a14").json()["result"]["gate_distance_m"] == 7.92


def test_study_rejects_a_bad_gate_before_any_call(study_client):
    r = post_study(study_client, gate_a="[[1, 2]]")
    assert r.status_code == 400 and r.json()["code"] == "bad_gate"
    assert study_client.study_calls == []


def test_study_cost_cap_counts_every_vehicle_class(study_client, monkeypatch):
    monkeypatch.setattr(api, "probe", lambda path: {"fps": 120.0, "frames": 120 * 50})  # 50 s
    r = post_study(study_client)
    assert r.status_code == 429 and r.json()["code"] == "run_cost_cap"
    assert study_client.study_calls == []
