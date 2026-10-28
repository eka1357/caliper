"""Muse Spark call 1: question + video -> MeasurementSpec (ARCHITECTURE section 4).

One structured-output call (strict JSON schema, no answer field). The model plans the
measurement; it never returns the answer. After validation, deterministic checks:
- the prior is re-parsed (caliper.priors); when it parses, its SI value replaces the model's;
- a known object is allowed only when the question gives no prior, with the size from
  config.KNOWN_OBJECTS (the model's value is ignored);
- alternative phrases are trimmed to SPEC_ALT_PHRASES and never repeat the main phrase.
A spec that fails validation raises SpecError (the pipeline abstains); there is no retry, so the
second Muse call per question stays free for the audit (AGENTS.md rule 2).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from caliper import config
from caliper.backends import BackendError, LanguageBackend, MetaApiBackend
from caliper.models import MeasurementSpec
from caliper.priors import parse_prior

log = logging.getLogger(__name__)


class SpecError(RuntimeError):
    """The spec writer's output cannot be used; the message is the abstention reason."""


INSTANCES = ["auto", "left", "right", "middle", "top", "bottom", "largest", "smallest"] + [
    f"center_rank:{k}" for k in range(1, 9)
]
AXES = ["path", "horizontal", "vertical", "longest", "shortest", "disc"]


def _s(desc: str, enum: list[str] | None = None, nullable: bool = False) -> dict[str, Any]:
    out: dict[str, Any] = {
        "type": ["string", "null"] if nullable else "string",
        "description": desc,
    }
    if enum:
        out["enum"] = enum + ([None] if nullable else [])
    return out


def _n(desc: str, nullable: bool = False) -> dict[str, Any]:
    return {"type": ["number", "null"] if nullable else "number", "description": desc}


def _pair(desc: str, nullable: bool = False) -> dict[str, Any]:
    return {"type": ["array", "null"] if nullable else "array", "items": {"type": "number"},
            "description": desc}  # fmt: skip


def _phrases(desc: str) -> dict[str, Any]:
    return {"type": "array", "items": {"type": "string"}, "description": desc}


PROPERTIES: dict[str, Any] = {
    "target_phrase": _s("Short visible noun phrase for the object the question measures"),
    "target_alt_phrases": _phrases("Exactly 2 other ways to name the same target for SAM"),
    "target_instance": _s("Which match to keep if the phrase matches several objects", INSTANCES),
    "second_phrase": _s("The other object, only for separation or orbit_diameter", None, True),
    "second_instance": _s("Which match to keep for the second object", INSTANCES),
    "reference_phrase": _s(
        "Visible object the prior describes; null if it is the target", None, True
    ),  # fmt: skip
    "reference_alt_phrases": _phrases("Exactly 2 other ways to name the reference (or [])"),
    "reference_instance": _s("Which match to keep for the reference", INSTANCES),
    "reference_kind": _s(
        "What the prior gives", ["size", "speed", "acceleration", "known_object"]
    ),  # fmt: skip
    "reference_statistic": _s(
        "How to measure the reference in the video", ["extent", "average_speed", "acceleration"]
    ),  # fmt: skip
    "reference_axis": _s("Axis of the reference measurement", AXES),
    "reference_value_si": _n("The prior's value in SI units (m, m/s, m/s^2)", True),
    "reference_source": _s("'question prior', or 'world knowledge: <object> is <size>'"),
    "quantity": _s("What the question asks for", ["size", "speed", "acceleration"]),
    "statistic": _s(
        "How to compute it", ["instantaneous", "average", "extent", "separation", "orbit_diameter"]
    ),  # fmt: skip
    "axis": _s("Axis of the target measurement", AXES),
    "timestamp_s": _n("Time in seconds the question asks about, else null", True),
    "time_anchor": _s(
        "timestamp, or first/last for 'initial'/'final'", ["timestamp", "first", "last"]
    ),  # fmt: skip
    "time_range_s": _pair(
        "[start, end] in seconds for an average over a window, else null", True
    ),  # fmt: skip
    "output_unit": _s(
        "Unit the question asks for",
        ["m", "cm", "mm", "km", "m/s", "cm/s", "mm/s", "km/h", "m/s^2", "cm/s^2"],
    ),  # fmt: skip
    "plausible_range_si": _pair("[low, high] sanity bounds for the answer in SI units"),
    "notes": _s("One sentence on anything unusual (no numbers for the answer)"),
}
SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": PROPERTIES,
    "required": list(PROPERTIES),
    "additionalProperties": False,
}

PROMPT = """You plan a physical measurement from a video. You do NOT estimate the answer: \
deterministic code will track the objects with SAM 3.1 (a segmentation model prompted by short \
noun phrases) and compute the number. Fill every field of the JSON schema.

Question: {question}
Given information (prior): {prior}

Rules
1. target_phrase names the object whose size or motion the question asks about, as a short \
visible noun phrase SAM can segment (colour + noun works well: "red car", "white ball"). Never a \
scene feature, region, label, text or the camera. target_alt_phrases: exactly 2 different \
names for the same object (a synonym, a more generic noun, or a colour/shape description).
2. The prior sets the scale. reference_phrase names the visible object the prior describes, with \
2 alternatives in reference_alt_phrases. If the prior describes the target itself, set \
reference_phrase to null and reference_alt_phrases to []. reference_value_si is the prior's \
value in SI units (m, m/s, m/s^2).
   - Prior is a size (length, height, diameter): reference_kind "size", reference_statistic \
"extent", reference_axis: "disc" for round objects, "vertical" for heights of standing things, \
"horizontal" or "longest" for lengths.
   - Prior is a speed of an object: reference_kind "speed", reference_statistic "average_speed".
   - Prior is an acceleration such as gravity: reference_kind "acceleration", reference_statistic \
"acceleration", reference_axis "vertical", and reference_phrase is an object visibly in free \
flight or free fall (null if that is the target).
   - Only if there is no prior may you use a known object: reference_kind "known_object", \
reference_phrase exactly one of {known}, reference_source "world knowledge: ...".
3. quantity and statistic: a size is "extent" (axis "longest", "shortest", "horizontal", \
"vertical" or "disc"); a distance between two objects is "separation" (second_phrase = the other \
object; axis "path", or "horizontal"/"vertical" if asked); the diameter of a circular path around \
a central object is "orbit_diameter" (second_phrase = the central object); a speed or \
acceleration at a moment is "instantaneous" with timestamp_s; an average speed is "average" \
(time_range_s if the question gives a window, else null; axis "horizontal" if it asks for \
horizontal velocity, else "path").
4. Times: timestamp_s for "at 1.5 s". time_anchor "first" for initial, "last" for final, \
otherwise "timestamp". Use null where a time does not apply.
5. Instances: when a phrase can match several objects, pick target_instance (and \
second_instance, reference_instance) from left, right, middle, top, bottom, largest, smallest, \
center_rank:k (k-th closest to the frame centre), or auto (the longest-tracked one). Use the \
question's own words ("the ball on the left" -> left, "the big bird" -> largest).
6. output_unit: the unit the question asks for; if it gives none, use m, m/s or m/s^2.
7. plausible_range_si: wide sanity bounds for the true answer in SI, from physics and the scene.

Example (different scene): "How fast is the blue bicycle at 2.0 s in km/h? Prior: the bus behind \
it is 12 m long." -> target_phrase "blue bicycle", target_alt_phrases ["bicycle", "cyclist"], \
reference_phrase "bus", reference_alt_phrases ["city bus", "large vehicle"], reference_kind \
"size", reference_statistic "extent", reference_axis "longest", reference_value_si 12, \
quantity "speed", statistic "instantaneous", axis "path", timestamp_s 2.0, time_anchor \
"timestamp", time_range_s null, output_unit "km/h", plausible_range_si [0, 20].
"""


def prompt_for(question: str, prior: str | None) -> str:
    return PROMPT.format(question=question, prior=prior or "none",
                         known=", ".join(f'"{k}"' for k in config.KNOWN_OBJECTS))  # fmt: skip


def _alts(main: str | None, alts: list[str]) -> list[str]:
    seen = {(main or "").strip().lower()}
    out = []
    for a in alts:
        key = a.strip().lower()
        if key and key not in seen:
            out.append(a.strip())
            seen.add(key)
    return out[: config.SPEC_ALT_PHRASES]


def postprocess(raw: dict[str, Any], prior: str | None, depth_info: dict | None) -> MeasurementSpec:
    """Validate the model's JSON and apply the deterministic checks."""
    extra = set(raw) - set(PROPERTIES)
    if extra:
        log.warning("spec writer returned extra keys, ignored: %s", sorted(extra))
    data = {k: raw[k] for k in PROPERTIES if k in raw}
    data["target_alt_phrases"] = _alts(
        data.get("target_phrase"), data.get("target_alt_phrases") or []
    )
    data["reference_alt_phrases"] = (
        _alts(data.get("reference_phrase"), data.get("reference_alt_phrases") or [])
        if data.get("reference_phrase")
        else []
    )
    notes = [data.get("notes") or ""]
    parsed = parse_prior(prior)
    kind = data.get("reference_kind")
    if kind == "known_object":
        if prior:
            raise SpecError("spec used a known object although the question gives a prior")
        match = {k.lower(): k for k in config.KNOWN_OBJECTS}.get(
            (data.get("reference_phrase") or "").strip().lower()
        )
        if match is None:
            raise SpecError(f"known object {data.get('reference_phrase')!r} is not allowed")
        obj = config.KNOWN_OBJECTS[match]
        data.update(reference_value_si=obj["size_m"], reference_axis=obj["axis"],
                    reference_statistic="extent",
                    reference_source=f"world knowledge: {match}, {obj['source']}")  # fmt: skip
    elif parsed is not None:
        model_value = data.get("reference_value_si")
        if model_value is None or abs(
            model_value - parsed.value_si
        ) > config.PRIOR_MISMATCH_TOL * abs(parsed.value_si):
            notes.append(
                f"reference value {model_value} replaced by parsed prior {parsed.value_si}"
            )
            data["reference_value_si"] = parsed.value_si
    data["notes"] = "; ".join(n for n in notes if n)
    data["depth_info"] = depth_info
    for key in ("time_range_s", "plausible_range_si"):
        if data.get(key) is not None and len(data[key]) != 2:
            raise SpecError(f"spec field {key} must have 2 numbers")
    try:
        return MeasurementSpec(**data)
    except ValidationError as exc:
        raise SpecError(f"spec failed validation: {exc.errors()[0]['msg']}") from exc


def write_spec(
    video: Path,
    question: str,
    prior: str | None,
    depth_info: dict | None = None,
    backend: LanguageBackend | None = None,
) -> tuple[MeasurementSpec, dict[str, Any]]:
    """One Muse Spark call. Returns the spec and call info (usage, cost, raw JSON)."""
    backend = backend or MetaApiBackend()
    try:
        raw, info = backend.json_with_video(video, prompt_for(question, prior), SCHEMA,
                                            "MeasurementSpec")  # fmt: skip
    except BackendError as exc:
        raise SpecError(str(exc)) from exc
    info = {**info, "raw": raw}
    return postprocess(raw, prior, depth_info), info


def spec_json(spec: MeasurementSpec) -> str:
    return json.dumps(spec.model_dump(), sort_keys=True)
