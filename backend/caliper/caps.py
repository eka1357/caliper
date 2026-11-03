"""Live-run caps (AGENTS rule 14, ARCHITECTURE section 10).

Every live request passes `Caps.admit` before any API call: live runs enabled, clip length,
per-IP runs per hour, the cost estimate against the per-run (or per-study) cap, and the day's
remaining budget (spend so far plus estimates of runs still in flight). After the run,
`Caps.settle` records the actual cost in the daily ledger: only the API calls the run made
(`spend_since`), so calls answered from the disk cache count $0. Cached runs never come here.
"""

from __future__ import annotations

import json
import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from caliper import config
from caliper.meta_client import muse_cost_usd

Kind = Literal["measure", "study", "guess"]


class CapError(Exception):
    """A live request refused before any API call. status 503: live runs off; 429: a cap."""

    def __init__(self, code: str, message: str, status: int = 429) -> None:
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


@dataclass(frozen=True)
class CapSettings:
    enabled: bool = config.LIVE_RUNS_ENABLED
    max_clip_s: float = config.LIVE_MAX_CLIP_SECONDS
    max_study_s: float = config.LIVE_MAX_STUDY_SECONDS
    per_ip_per_hour: int = config.LIVE_RUNS_PER_IP_PER_HOUR
    per_run_usd: float = config.PER_RUN_CAP_USD
    per_study_usd: float = config.PER_STUDY_CAP_USD
    daily_usd: float = config.DAILY_SPEND_CAP_USD

    def public(self) -> dict:
        return {
            "max_clip_seconds": self.max_clip_s,
            "max_study_seconds": self.max_study_s,
            "runs_per_ip_per_hour": self.per_ip_per_hour,
            "per_run_cap_usd": self.per_run_usd,
            "per_study_cap_usd": self.per_study_usd,
            "daily_spend_cap_usd": self.daily_usd,
        }


def estimate_cost(kind: Kind, frames: int, vehicle_classes: int = 3) -> float:
    """Upper-bound-ish estimate in USD before any call (ARCHITECTURE section 13)."""
    sam = config.SAM_USD_PER_FRAME * frames
    muse = config.MUSE_CALL_ESTIMATE_USD
    if kind == "guess":
        return muse
    if kind == "study":
        return sam * vehicle_classes + muse  # audit spot check on a vehicle sample
    return sam * config.LIVE_SAM_CONCEPTS + muse * config.MUSE_CALLS_PER_MEASURE


def api_cache_files() -> set[Path]:
    """Every API response record in the disk cache; snapshot it before a live run."""
    return set((config.CACHE_DIR / "api").glob("*/*.json"))


def spend_since(before: set[Path], frames: int) -> float:
    """Real spend of one run: the API records it added to the cache. A cache hit adds none, so it
    costs $0. Muse Spark calls at their token usage; each SAM request bills every frame."""
    cost = 0.0
    for p in api_cache_files() - before:
        rec = json.loads(p.read_text(encoding="utf-8"))
        if rec["kind"] == "responses":
            cost += muse_cost_usd(rec["usage"])
        elif rec["kind"] == "sam":
            cost += config.SAM_USD_PER_FRAME * frames
    return cost


class SpendLedger:
    """Actual live spend per UTC day, on disk so a restart does not reset the daily cap."""

    def __init__(self, folder: Path = config.SPEND_DIR) -> None:
        self.folder = folder

    def _path(self, now: float) -> Path:
        return self.folder / f"{datetime.fromtimestamp(now, UTC):%Y-%m-%d}.json"

    def total(self, now: float) -> float:
        path = self._path(now)
        if not path.exists():
            return 0.0
        return float(json.loads(path.read_text(encoding="utf-8"))["total_usd"])

    def add(self, usd: float, now: float) -> None:
        path = self._path(now)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {"total_usd": self.total(now) + usd, "runs": 0}
        if path.exists():
            data["runs"] = json.loads(path.read_text(encoding="utf-8")).get("runs", 0)
        data["runs"] += 1
        path.write_text(json.dumps(data), encoding="utf-8")


@dataclass
class Ticket:
    ip: str
    estimate_usd: float


class Caps:
    def __init__(
        self,
        settings: CapSettings | None = None,
        ledger: SpendLedger | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.settings = settings or CapSettings()
        self.ledger = ledger or SpendLedger()
        self.clock = clock
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._in_flight = 0.0
        self._lock = threading.Lock()

    def admit(self, kind: Kind, ip: str, duration_s: float, frames: int) -> Ticket:
        """Raise CapError if any cap refuses; otherwise reserve the estimate and count the run."""
        s, now = self.settings, self.clock()
        if not s.enabled:
            raise CapError("live_disabled", "Live runs are paused for now.", status=503)
        limit_s = s.max_study_s if kind == "study" else s.max_clip_s
        if duration_s > limit_s:
            raise CapError("clip_too_long", f"Clips can be at most {limit_s:g} s for live runs.")
        estimate = estimate_cost(kind, frames)
        cap = s.per_study_usd if kind == "study" else s.per_run_usd
        if estimate > cap:
            raise CapError("run_cost_cap", f"This clip would cost about ${estimate:.2f}, "
                                           f"above the ${cap:.2f} cap per run.")  # fmt: skip
        with self._lock:
            hits = self._hits[ip]
            while hits and now - hits[0] >= 3600:
                hits.popleft()
            if len(hits) >= s.per_ip_per_hour:
                raise CapError("ip_rate", f"At most {s.per_ip_per_hour} live runs per hour.")
            if self.ledger.total(now) + self._in_flight + estimate > s.daily_usd:
                raise CapError("daily_cap", "Today's live-run budget is used up.")
            hits.append(now)
            self._in_flight += estimate
        return Ticket(ip, estimate)

    def settle(self, ticket: Ticket, actual_usd: float) -> None:
        """Release the reservation and record what the run actually cost."""
        with self._lock:
            self._in_flight = max(0.0, self._in_flight - ticket.estimate_usd)
            if actual_usd > 0:
                self.ledger.add(actual_usd, self.clock())
