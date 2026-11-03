"""Caliper as an MCP server: `measure` and `study` as tools for other agents (Phase 6 item 2).

Run over stdio (the default for local agent clients):

    backend/.venv/Scripts/python.exe -m caliper.mcp_server

Same engine, same rules as the HTTP API: the language model never produces the number (AGENTS
rule 1), a failed check or audit veto comes back as an abstention with its reason (rule 3), every
API response is cached (rule 5), and every call passes the live-run caps from .env before any API
call (rule 14: LIVE_RUNS_ENABLED, clip length, cost estimate per run or study, daily spend). Cache
hits still go through the caps check; only API records a call adds to the cache count as spend.

Tools return the pydantic models from caliper.models (Result, StudySummary) as structured output.
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

from mcp.server.mcpserver import MCPServer
from pydantic import BaseModel, Field

from caliper import config, pipeline, study_live
from caliper.caps import CapError, Caps, api_cache_files, estimate_cost, spend_since
from caliper.models import Result, StudySummary
from caliper.normalize import normalize, probe

log = logging.getLogger(__name__)

VEHICLE_CLASSES = study_live.VEHICLE_CLASSES
CALLER = "mcp"  # the per-IP rate limit counts all MCP calls as one caller

server = MCPServer(
    name="caliper",
    instructions=(
        "Caliper measures size, speed and acceleration in a video and returns a number with a 90% "
        "interval, or an abstention with the reason. Give a prior (one known real size or speed, "
        "e.g. 'The coin is 0.027 m in diameter.') whenever you have one. `study` times vehicles "
        "between two gate lines a measured distance apart and reports the 85th-percentile speed."
    ),
)


class GateLine(BaseModel):
    """A line across the road, in pixels on frame 0 of the normalized video (longest side <= 1280
    for portrait clips, width <= 1280 otherwise)."""

    a: tuple[float, float] = Field(description="First end, (x, y) in pixels")
    b: tuple[float, float] = Field(description="Second end, (x, y) in pixels")


class StudyGates(BaseModel):
    gate_a: GateLine = Field(description="One gate line; the order of the two gates is free")
    gate_b: GateLine = Field(description="The other gate, distance_m away along the road")


_caps: Caps | None = None


def caps() -> Caps:
    global _caps
    if _caps is None:
        _caps = Caps()
    return _caps


def set_caps(c: Caps | None) -> None:
    """Tests inject caps with a temporary ledger; None restores the .env defaults."""
    global _caps
    _caps = c


def _clip(video_path: str) -> tuple[Path, float, int]:
    path = Path(video_path).expanduser()
    if not path.is_file():
        raise ValueError(f"No video at {video_path}")
    info = probe(path)
    fps, frames = float(info["fps"]), int(info["frames"])
    return path, (frames / fps if fps else 0.0), frames


def _refusal(exc: CapError) -> ValueError:
    return ValueError(f"{exc.code}: {exc.message}")


@server.tool(
    description="Measure a size, speed or acceleration in a video. Returns a measured value with "
    "a 90% interval, or status 'abstained' with abstain_reason. Never a guess."
)
def measure(video_path: str, question: str, prior: str | None = None) -> Result:
    path, duration, frames = _clip(video_path)
    try:
        ticket = caps().admit("measure", CALLER, duration, frames)
    except CapError as exc:
        raise _refusal(exc) from exc
    before = api_cache_files()
    try:
        result = pipeline.measure(
            path, question, prior, run_id=f"mcp-{uuid.uuid4().hex[:12]}",
            bootstrap_b=config.LIVE_BOOTSTRAP_B,
        )  # fmt: skip
    finally:
        cost = spend_since(before, int(probe(normalize(path))["frames"]))
        caps().settle(ticket, cost)
    log.info("mcp measure %s: %s, $%.4f", result.run_id, result.status, cost)
    return result


@server.tool(
    description="Street speed study: time every vehicle between two gate lines distance_m apart. "
    "Returns each vehicle's speed with a 90% interval (or why it has no reading), the median, "
    "and the 85th percentile with its interval."
)
def study(
    video_path: str,
    gates: StudyGates,
    distance_m: float,
    vehicle_classes: list[str] | None = None,
    speed_limit_kmh: float | None = None,
) -> StudySummary:
    if distance_m <= 0:
        raise ValueError("distance_m must be positive")
    classes = vehicle_classes or VEHICLE_CLASSES
    path, duration, frames = _clip(video_path)
    est = estimate_cost("study", frames, len(classes))
    if est > caps().settings.per_study_usd:
        raise ValueError(f"run_cost_cap: this study would cost about ${est:.2f}, above the "
                         f"${caps().settings.per_study_usd:.2f} cap per study.")  # fmt: skip
    try:
        ticket = caps().admit("study", CALLER, duration, frames)
    except CapError as exc:
        raise _refusal(exc) from exc
    before = api_cache_files()
    try:
        summary, _ = study_live.run_study(
            path, (gates.gate_a.a, gates.gate_a.b), (gates.gate_b.a, gates.gate_b.b), distance_m,
            f"mcp-study-{uuid.uuid4().hex[:12]}", classes, speed_limit_kmh,
        )  # fmt: skip
    finally:
        cost = spend_since(before, int(probe(normalize(path))["frames"]))
        caps().settle(ticket, cost)
    log.info("mcp study %s: %d of %d measured, $%.4f", summary.run_id,
             summary.vehicles_measured, summary.vehicles_seen, cost)  # fmt: skip
    return summary


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    server.run("stdio")


if __name__ == "__main__":
    main()
