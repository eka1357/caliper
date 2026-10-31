"""Compare mode: Muse Spark alone answers from the video (one call). Shown only as a "guess".

This is the baseline the workspace contrasts with the measurement (DESIGN principle 4); its
number is never presented as a Caliper result (AGENTS rule 1).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from caliper.backends import LanguageBackend, MetaApiBackend

PROMPT = (
    "Watch the video and answer the question with your best numeric estimate in the unit the "
    "question asks for. Reply with one short sentence in `text` and the number in `value`.\n\n"
    "Question: {question}"
)

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"text": {"type": "string"}, "value": {"type": ["number", "null"]}},
    "required": ["text", "value"],
    "additionalProperties": False,
}


def guess(
    video: Path, question: str, backend: LanguageBackend | None = None
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Returns ({text, parsed_value}, call info with cost_usd)."""
    out, info = (backend or MetaApiBackend()).json_with_video(
        video, PROMPT.format(question=question), SCHEMA, "guess"
    )
    value = out.get("value")
    parsed = float(value) if isinstance(value, int | float) else None
    return {"text": str(out.get("text", "")), "parsed_value": parsed}, info
