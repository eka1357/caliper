"""FastAPI app (ARCHITECTURE section 10): cached runs for replay, capped live runs.

Live endpoints (measure, guess) check caps.Caps before any API call. Cached demo runs and
API-run cache hits never count against the caps. Measure responses use the cached-run shape
(runs.CachedRun) so the UI renders live and recorded runs the same way.

  uvicorn caliper.api:app --port 8000
"""

from __future__ import annotations

import hashlib
import json
import logging
import tempfile
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated, Any

import pandas as pd
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from caliper import config, guess, pipeline, runs
from caliper.caps import CapError, Caps
from caliper.models import Result
from caliper.normalize import normalize, probe

log = logging.getLogger(__name__)

app = FastAPI(title="Caliper API")
app.add_middleware(CORSMiddleware, allow_origins=config.WEB_ORIGINS, allow_methods=["GET", "POST"],
                   allow_headers=["*"])  # fmt: skip
app.state.caps = Caps()
config.RUNS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/runs", StaticFiles(directory=config.RUNS_DIR), name="runs")


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


def _cached_list() -> list[dict[str, Any]]:
    return [e.model_dump() for e in runs.list_runs()]


@app.exception_handler(CapError)
def _cap_error(_: Request, exc: CapError) -> JSONResponse:
    body = {"code": exc.code, "message": exc.message, "cached_runs": _cached_list()}
    return JSONResponse(body, status_code=exc.status)


@app.exception_handler(ApiError)
def _api_error(_: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse({"code": exc.code, "message": exc.message}, status_code=exc.status)


@app.exception_handler(runs.RunNotFound)
def _not_found(_: Request, exc: runs.RunNotFound) -> JSONResponse:
    return JSONResponse({"code": "not_found", "message": f"No run {exc.args[0]}"}, 404)


def _ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")  # set by the hosting proxy
    return fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "?")


@contextmanager
def _saved_upload(video: UploadFile) -> Iterator[tuple[Path, str]]:
    """Stream the upload to a temp file under the size limit; yield (path, sha256)."""
    with tempfile.TemporaryDirectory() as tmp:
        suffix = Path(video.filename or "clip.mp4").suffix.lower() or ".mp4"
        path, digest, size = Path(tmp) / f"upload{suffix}", hashlib.sha256(), 0
        with open(path, "wb") as fh:
            while chunk := video.file.read(1 << 20):
                size += len(chunk)
                if size > config.LIVE_MAX_UPLOAD_BYTES:
                    raise ApiError(413, "too_large", "The clip file is too large.")
                digest.update(chunk)
                fh.write(chunk)
        yield path, digest.hexdigest()


def _probe(path: Path) -> tuple[float, int]:
    try:
        info = probe(path)
    except Exception as exc:  # ffprobe could not read it: not a video we can use
        raise ApiError(400, "bad_video", "That file isn't a video we can read.") from exc
    fps, frames = float(info["fps"]), int(info["frames"])
    return frames / fps if fps else 0.0, frames


def _run_key(*parts: str) -> str:
    return hashlib.sha256("\x1f".join(parts).encode()).hexdigest()[:32]


def _cache_get(key: str) -> dict[str, Any] | None:
    path = config.API_RUNS_DIR / f"{key}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def _cache_put(key: str, body: dict[str, Any]) -> None:
    config.API_RUNS_DIR.mkdir(parents=True, exist_ok=True)
    (config.API_RUNS_DIR / f"{key}.json").write_text(json.dumps(body), encoding="utf-8")


def _backend(name: str | None) -> str:
    if name not in (None, "", "meta_api"):
        raise ApiError(400, "backend", "Only the meta_api backend is available.")
    return "meta_api"


@app.get("/api/health")
def health() -> dict[str, Any]:
    caps: Caps = app.state.caps
    return {"ok": True, "live_runs_enabled": caps.settings.enabled,
            "caps": caps.settings.public()}  # fmt: skip


@app.get("/api/runs")
def list_runs() -> list[dict[str, Any]]:
    return _cached_list()


@app.get("/api/runs/{run_id}")
def get_run(run_id: str) -> dict[str, Any]:
    return runs.load_run(run_id).model_dump(mode="json")


def _measure_live(
    path: Path, question: str, prior: str | None, ticket_args: tuple[str, float, int]
) -> Result:
    caps: Caps = app.state.caps
    ticket = caps.admit("measure", *ticket_args)
    run_id, t0, cost = f"live-{uuid.uuid4().hex[:12]}", time.perf_counter(), 0.0
    try:
        result = pipeline.measure(
            path, question, prior, run_id=run_id, bootstrap_b=config.LIVE_BOOTSTRAP_B,
            with_overlay=True,
        )  # fmt: skip
        cost = result.cost_usd
    except Exception as exc:
        log.exception("live measure %s failed", run_id)
        raise ApiError(500, "error", "Something broke on our side.") from exc
    finally:
        caps.settle(ticket, cost)
    result.timings_ms["total"] = round((time.perf_counter() - t0) * 1000)
    log.info("live measure %s: %s, $%.4f", run_id, result.status, cost)
    return result


@app.post("/api/measure")
def measure(
    request: Request,
    video: Annotated[UploadFile, File()],
    question: Annotated[str, Form(min_length=3, max_length=500)],
    prior: Annotated[str | None, Form(max_length=300)] = None,
    backend: Annotated[str | None, Form()] = None,
) -> dict[str, Any]:
    name = _backend(backend)
    with _saved_upload(video) as (path, sha):
        key = _run_key("measure", sha, question, prior or "", name)
        if (hit := _cache_get(key)) is not None:
            return hit  # cache hit: free, never counted
        duration, frames = _probe(path)
        result = _measure_live(path, question, prior, (_ip(request), duration, frames))
    ov = result.artifacts.pop("overlay", {})
    meta = runs.RunMeta(title="Your clip", question=question, source="live", placeholder=False,
                        clip=None, poster=None)  # fmt: skip
    body = runs.CachedRun(kind="measure", meta=meta, result=result.model_dump(mode="json"),
                          overlay=ov).model_dump(mode="json")  # fmt: skip
    _cache_put(key, body)
    return body


@app.post("/api/guess")
def guess_endpoint(
    request: Request,
    video: Annotated[UploadFile, File()],
    question: Annotated[str, Form(min_length=3, max_length=500)],
    prior: Annotated[str | None, Form(max_length=300)] = None,
    backend: Annotated[str | None, Form()] = None,
) -> dict[str, Any]:
    name = _backend(backend)
    with _saved_upload(video) as (path, sha):
        key = _run_key("guess", sha, question, prior or "", name)
        if (hit := _cache_get(key)) is not None:
            return hit
        duration, frames = _probe(path)
        caps: Caps = app.state.caps
        ticket = caps.admit("guess", _ip(request), duration, frames)
        cost = 0.0
        try:
            out, info = guess.guess(normalize(path), question, prior=prior or None)
            cost = info["cost_usd"]
        except Exception as exc:
            log.exception("live guess failed")
            raise ApiError(500, "error", "Something broke on our side.") from exc
        finally:
            caps.settle(ticket, cost)
    body = {**out, "cost_usd": cost}
    _cache_put(key, body)
    return body


@app.post("/api/study")
def study() -> dict[str, Any]:
    raise ApiError(503, "study_unavailable", "The street speed study isn't built yet.")


@app.get("/api/results")
def results() -> dict[str, Any]:
    """Benchmark rows from eval/results.csv and eval/field_results.csv (when it exists)."""
    out: dict[str, Any] = {}
    for name in ("results", "field_results"):
        path = config.ROOT / "eval" / f"{name}.csv"
        out[name] = json.loads(pd.read_csv(path).to_json(orient="records")) if path.exists() else []
    return out
