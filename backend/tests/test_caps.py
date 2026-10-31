"""Live-run caps refuse before any API call; the ledger survives restarts (no network)."""

import pytest

from caliper import config
from caliper.caps import CapError, Caps, CapSettings, SpendLedger, estimate_cost


class Clock:
    def __init__(self, t: float = 1_793_000_000.0) -> None:
        self.t = t

    def __call__(self) -> float:
        return self.t


def caps(tmp_path, clock=None, **kw) -> Caps:
    base = dict(enabled=True, max_clip_s=15, max_study_s=60, per_ip_per_hour=2,
                per_run_usd=0.50, per_study_usd=1.50, daily_usd=1.00)  # fmt: skip
    base.update(kw)
    return Caps(CapSettings(**base), SpendLedger(tmp_path), clock or Clock())


def code(fn) -> str:
    with pytest.raises(CapError) as exc:
        fn()
    return exc.value.code


def test_estimate_matches_cost_model():
    # 90 frames x 2 concepts x $0.0002 + 2 Muse calls
    expected = 90 * 2 * config.SAM_USD_PER_FRAME + 2 * config.MUSE_CALL_ESTIMATE_USD
    assert estimate_cost("measure", 90) == pytest.approx(expected)
    assert estimate_cost("study", 1800) == pytest.approx(1800 * 3 * 0.0002 + 0.035)


def test_disabled_is_503(tmp_path):
    with pytest.raises(CapError) as exc:
        caps(tmp_path, enabled=False).admit("measure", "1.1.1.1", 3, 90)
    assert exc.value.status == 503 and exc.value.code == "live_disabled"


def test_clip_length_and_run_cost(tmp_path):
    c = caps(tmp_path)
    assert code(lambda: c.admit("measure", "ip", 16, 480)) == "clip_too_long"
    assert code(lambda: c.admit("measure", "ip", 14, 14 * 120)) == "run_cost_cap"
    c.admit("study", "ip", 40, 1200)  # 40 s study fits the 60 s and $1.50 limits


def test_ip_rate_window_slides(tmp_path):
    clock = Clock()
    c = caps(tmp_path, clock, daily_usd=100)
    c.admit("measure", "a", 3, 90)
    c.admit("measure", "a", 3, 90)
    assert code(lambda: c.admit("measure", "a", 3, 90)) == "ip_rate"
    c.admit("measure", "b", 3, 90)  # other IPs unaffected
    clock.t += 3600
    c.admit("measure", "a", 3, 90)


def test_daily_cap_counts_in_flight_and_ledger(tmp_path):
    clock = Clock()
    c = caps(tmp_path, clock, per_ip_per_hour=100, daily_usd=0.30)
    t1 = c.admit("measure", "a", 3, 90)  # ~0.106 reserved
    c.admit("measure", "a", 3, 90)  # ~0.212 reserved
    assert code(lambda: c.admit("measure", "a", 3, 90)) == "daily_cap"
    c.settle(t1, 0.02)  # actual cost was lower: frees room
    c.admit("measure", "a", 3, 90)
    restarted = caps(tmp_path, clock, per_ip_per_hour=100, daily_usd=0.30)
    assert restarted.ledger.total(clock.t) == pytest.approx(0.02)
    clock.t += 86400  # next UTC day starts at zero
    assert restarted.ledger.total(clock.t) == 0.0
