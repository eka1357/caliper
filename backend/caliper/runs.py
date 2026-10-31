"""Cached runs for replay: web/public/runs/index.json plus one folder per run.

Schema v1 (DECISIONS.md, Phase 5). Placeholder, field and saved live runs all use this writer,
so new runs appear in the UI without code changes:

    runs/index.json              [{run_id, kind, title, status, source, placeholder, created_utc}]
    runs/<run_id>/run.json       {schema_version, kind, meta, result, overlay, guess?}
    runs/<run_id>/clip.mp4       H.264, faststart, under MAX_CLIP_BYTES
    runs/<run_id>/poster.jpg     first frame
"""

from __future__ import annotations

import json
import logging
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import cv2
from pydantic import BaseModel, Field

from caliper import config
from caliper.models import Result

log = logging.getLogger(__name__)

SCHEMA_VERSION = 1
MAX_CLIP_BYTES = 3 * 1024 * 1024  # PROMPTS.md Phase 4 step 6: demo copies under 3 MB
_RUN_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")

Source = Literal["placeholder_synthetic", "field", "live"]


class RunMeta(BaseModel):
    title: str
    question: str
    source: Source
    placeholder: bool  # the UI shows the placeholder badge from this field alone
    notes: str = ""
    created_utc: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(timespec="seconds")
    )
    clip: str | None = "clip.mp4"
    poster: str | None = "poster.jpg"


class CachedRun(BaseModel):
    schema_version: int = SCHEMA_VERSION
    kind: Literal["measure", "study"]
    meta: RunMeta
    result: dict[str, Any]  # Result for measure, StudySummary for study (Phase 4)
    overlay: dict[str, Any]
    guess: dict[str, Any] | None = None  # optional Muse Spark alone answer {text, parsed_value}


class RunIndexEntry(BaseModel):
    run_id: str
    kind: Literal["measure", "study"]
    title: str
    status: str
    source: Source
    placeholder: bool
    created_utc: str


class RunNotFound(KeyError):
    pass


def _check_id(run_id: str) -> str:
    if not _RUN_ID.match(run_id):
        raise RunNotFound(run_id)
    return run_id


def _index_path(root: Path) -> Path:
    return root / "index.json"


def list_runs(root: Path | None = None) -> list[RunIndexEntry]:
    path = _index_path(root or config.RUNS_DIR)
    if not path.exists():
        return []
    return [RunIndexEntry(**e) for e in json.loads(path.read_text(encoding="utf-8"))]


def load_run(run_id: str, root: Path | None = None) -> CachedRun:
    path = (root or config.RUNS_DIR) / _check_id(run_id) / "run.json"
    if not path.exists():
        raise RunNotFound(run_id)
    return CachedRun.model_validate_json(path.read_text(encoding="utf-8"))


def _write_poster(clip: Path, dest: Path) -> bool:
    cap = cv2.VideoCapture(str(clip))
    ok, frame = cap.read()
    cap.release()
    return bool(ok and cv2.imwrite(str(dest), frame))


def save_cached_run(
    run_id: str,
    kind: Literal["measure", "study"],
    result: Result | dict[str, Any],
    overlay: dict[str, Any],
    meta: RunMeta,
    clip: Path | None = None,
    root: Path | None = None,
    guess: dict[str, Any] | None = None,
) -> CachedRun:
    """Write runs/<run_id>/ (run.json, clip, poster) and upsert the manifest entry."""
    root = root or config.RUNS_DIR
    folder = root / _check_id(run_id)
    folder.mkdir(parents=True, exist_ok=True)
    payload = result.model_dump(mode="json") if isinstance(result, Result) else result
    if kind == "measure":
        Result.model_validate(payload)
    meta = meta.model_copy()
    if clip is not None:
        size = clip.stat().st_size
        if size > MAX_CLIP_BYTES:
            raise ValueError(f"{clip.name} is {size} bytes; demo clips must be under 3 MB")
        shutil.copyfile(clip, folder / "clip.mp4")
        if not _write_poster(folder / "clip.mp4", folder / "poster.jpg"):
            meta.poster = None
    else:
        meta.clip = meta.poster = None
    run = CachedRun(kind=kind, meta=meta, result=payload, overlay=overlay, guess=guess)
    (folder / "run.json").write_text(run.model_dump_json(indent=1), encoding="utf-8")
    entry = RunIndexEntry(
        run_id=run_id, kind=kind, title=meta.title, status=str(payload.get("status", "")),
        source=meta.source, placeholder=meta.placeholder, created_utc=meta.created_utc,
    )  # fmt: skip
    entries = [e for e in list_runs(root) if e.run_id != run_id] + [entry]
    entries.sort(key=lambda e: (e.placeholder, e.run_id))  # real runs first
    _index_path(root).write_text(
        json.dumps([e.model_dump() for e in entries], indent=1), encoding="utf-8"
    )
    log.info("saved cached run %s (%s, %s)", run_id, kind, meta.source)
    return run
