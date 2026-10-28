"""Language-model backends behind one interface (ARCHITECTURE section 4).

MetaApiBackend: muse-spark-1.3 on the Meta Model API, video through the Files API, every call
cached on disk (meta_client). MuseSparkOpenBackend: stretch (Phase 6), not implemented.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Protocol

from caliper import config
from caliper.meta_client import DiskCache, muse_cost_usd, responses_create, upload_file

log = logging.getLogger(__name__)


class BackendError(RuntimeError):
    """The model call returned no usable output (incomplete, refused, empty)."""


class LanguageBackend(Protocol):
    name: str

    def json_with_video(
        self, video: Path, prompt: str, schema: dict[str, Any], schema_name: str
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """One call with a video and a prompt; returns (parsed JSON, call info)."""
        ...


def _output_text(response: dict[str, Any]) -> str:
    return "".join(
        part.get("text", "")
        for item in response.get("output", [])
        if item.get("type") == "message"
        for part in item.get("content") or []
        if part.get("type") == "output_text"
    )


class MetaApiBackend:
    name = "meta_api"

    def __init__(self, cache: DiskCache | None = None) -> None:
        self.cache = cache

    def json_with_video(
        self, video: Path, prompt: str, schema: dict[str, Any], schema_name: str
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        file_id = upload_file(video, self.cache)
        payload = {
            "model": config.MUSE_MODEL,
            "input": [
                {
                    "type": "message",
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {"type": "input_file", "file_id": file_id},
                    ],
                }
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "schema": schema,
                    "strict": True,
                }  # fmt: skip
            },
            "max_output_tokens": config.SPEC_MAX_OUTPUT_TOKENS,
        }
        record = responses_create(payload, self.cache)
        resp = record["response"]
        info = {
            "key": record["key"],
            "usage": record["usage"],
            "latency_ms": record["latency_ms"],
            "cost_usd": muse_cost_usd(record["usage"]),
            "status": resp.get("status"),
        }
        text = _output_text(resp)
        if resp.get("status") not in (None, "completed") or not text:
            raise BackendError(f"model call {resp.get('status')}: {resp.get('incomplete_details')}")
        try:
            return json.loads(text), info
        except json.JSONDecodeError as exc:
            raise BackendError(f"model output is not JSON: {exc}") from exc


class MuseSparkOpenBackend:
    """Stretch (Phase 6): meta-models/muse-spark-open-1026 on Baseten, keyframes as images."""

    name = "muse_spark_open"

    def json_with_video(
        self, video: Path, prompt: str, schema: dict[str, Any], schema_name: str
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        raise NotImplementedError("Muse Spark Open backend is a Phase 6 stretch goal")
