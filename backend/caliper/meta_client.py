"""OpenAI SDK client for the Meta Model API, Files API upload, and a disk cache.

Every API response is cached on disk under CACHE_DIR, keyed by sha256 of the canonical
request, so reruns cost $0 (AGENTS.md rule 5). Each record also keeps token usage and
latency, which is where Phase 0's measured facts come from.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from openai import OpenAI

from caliper import config

log = logging.getLogger(__name__)

_client: OpenAI | None = None


def get_client() -> OpenAI:
    """Return a shared client. The SDK does not read MODEL_API_KEY itself, so pass it."""
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.environ["MODEL_API_KEY"], base_url=config.META_API_BASE_URL)
    return _client


def request_key(payload: dict[str, Any]) -> str:
    """sha256 of the request serialized with sorted keys."""
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


class DiskCache:
    """One JSON file per request key. Writes are atomic, so threads can share it."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = Path(root) if root is not None else config.CACHE_DIR

    def path(self, key: str) -> Path:
        return self.root / "api" / key[:2] / f"{key}.json"

    def get(self, key: str) -> dict[str, Any] | None:
        p = self.path(key)
        if not p.exists():
            return None
        return json.loads(p.read_text(encoding="utf-8"))

    def put(self, key: str, record: dict[str, Any]) -> None:
        p = self.path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=p.parent, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(record, fh)
        os.replace(tmp, p)


def normalize_usage(usage: Any) -> dict[str, int]:
    """Map Responses (input/output_tokens) and Chat (prompt/completion_tokens) usage to one dict."""
    if not usage:
        return {"input_tokens": 0, "output_tokens": 0}
    get = usage.get if isinstance(usage, dict) else lambda k, d=None: getattr(usage, k, d)
    inp = get("input_tokens", None)
    out = get("output_tokens", None)
    if inp is None:
        inp = get("prompt_tokens", 0)
    if out is None:
        out = get("completion_tokens", 0)
    return {"input_tokens": int(inp or 0), "output_tokens": int(out or 0)}


def muse_cost_usd(usage: dict[str, int]) -> float:
    return (
        usage["input_tokens"] * config.MUSE_USD_PER_M_INPUT
        + usage["output_tokens"] * config.MUSE_USD_PER_M_OUTPUT
    ) / 1_000_000


def cached_call(
    kind: str,
    payload: dict[str, Any],
    fn: Callable[[], tuple[Any, dict[str, int]]],
    cache: DiskCache | None = None,
) -> tuple[dict[str, Any], bool]:
    """Return (record, hit). On a miss, fn() returns (json-able response, usage) and is cached.

    The request itself is not stored (it can hold megabytes of base64 frames); its key is.
    """
    cache = cache or DiskCache()
    key = request_key({"kind": kind, **payload})
    record = cache.get(key)
    if record is not None:
        log.debug("cache hit %s %s", kind, key[:12])
        return record, True
    start = time.perf_counter()
    response, usage = fn()
    record = {
        "kind": kind,
        "model": payload.get("model"),
        "key": key,
        "created_utc": datetime.now(UTC).isoformat(),
        "latency_ms": round((time.perf_counter() - start) * 1000, 1),
        "usage": usage,
        "response": response,
    }
    cache.put(key, record)
    log.info("cache miss %s %s (%.0f ms)", kind, key[:12], record["latency_ms"])
    return record, False


def responses_create(payload: dict[str, Any], cache: DiskCache | None = None) -> dict[str, Any]:
    """Non-streaming Responses API call, cached. Returns the cache record."""

    def call() -> tuple[Any, dict[str, int]]:
        resp = get_client().responses.create(**payload)
        return resp.model_dump(mode="json"), normalize_usage(resp.usage)

    record, _ = cached_call("responses", payload, call, cache)
    return record


def chat_create(payload: dict[str, Any], cache: DiskCache | None = None) -> dict[str, Any]:
    """Chat Completions call, cached. Used by the QuantiPhy baseline. Returns the cache record."""

    def call() -> tuple[Any, dict[str, int]]:
        resp = get_client().chat.completions.create(**payload)
        return resp.model_dump(mode="json"), normalize_usage(resp.usage)

    record, _ = cached_call("chat", payload, call, cache)
    return record


def upload_file(path: Path, cache: DiskCache | None = None) -> str:
    """Upload once with purpose user_data; the file_id is cached by the file's sha256."""
    path = Path(path)
    payload = {"op": "files.create", "purpose": "user_data", "sha256": file_sha256(path)}

    def call() -> tuple[Any, dict[str, int]]:
        with open(path, "rb") as fh:
            resp = get_client().files.create(file=fh, purpose="user_data")
        return resp.model_dump(mode="json"), {"input_tokens": 0, "output_tokens": 0}

    record, _ = cached_call("files", payload, call, cache)
    return str(record["response"]["id"])
