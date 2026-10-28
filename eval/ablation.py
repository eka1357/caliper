"""A1 ablation: a rule-based parser in place of the Muse Spark spec writer.

rule_spec(question, prior) builds a MeasurementSpec with regex only: no model, no video. Same
SAM, engine and checks as `caliper` (run it with eval/quantiphy.py --variant
caliper_rule_parser). Patterns are generic English; writing them while seeing the dev questions
counts as dev tuning (EVAL_PROTOCOL section 6). When a pattern is missing, the parser returns
None with a reason and the question abstains.
"""

from __future__ import annotations

import re

from caliper.models import MeasurementSpec
from caliper.priors import parse_prior, unit_to_si

POSITION = {"left": "left", "right": "right", "middle": "middle", "center": "middle",
            "centre": "middle", "top": "top", "bottom": "bottom"}  # fmt: skip
SIZE_WORDS = {"big": "largest", "large": "largest", "bigger": "largest", "small": "smallest",
              "little": "smallest", "smaller": "smallest"}  # fmt: skip
AXIS_WORDS = {"diameter": "disc", "size": "disc", "height": "vertical", "tall": "vertical",
              "length": "longest", "long": "longest", "width": "horizontal",
              "thickness": "shortest", "wide": "horizontal"}  # fmt: skip
MEASURE = (
    r"(?:diameter|size|height|length|width|thickness|speed|velocity|acceleration|acc"
    r"|calibre|caliber)"
)
FILLER = r"\b(?:the|a|an|standing|sitting|moving|model of|one)\b"
DEFAULT_UNIT = {"size": "m", "speed": "m/s", "acceleration": "m/s^2"}
UNIT_ALIASES = {"meters": "m", "meter": "m", "metres": "m", "metre": "m", "centimeters": "cm",
                "millimeters": "mm"}  # fmt: skip


def _num(pattern: str, text: str) -> float | None:
    m = re.search(pattern, text)
    return float(m.group(1)) if m else None


def noun_phrase(text: str) -> tuple[str, str]:
    """(phrase, instance selector) from text like 'yellow ball on the left' or 'big bird'."""
    t = re.sub(r"\(.*?\)", " ", text.lower())
    selector = "auto"
    m = re.search(r"\b(?:on|in|at)\s+the\s+(left|right|middle|center|centre|top|bottom)\b", t)
    if m:
        selector = POSITION[m.group(1)]
        t = t[: m.start()] + t[m.end() :]
    words = re.sub(FILLER, " ", t).split()
    if words and words[0] in POSITION:
        selector = POSITION[words.pop(0)]
    if words and words[0] in SIZE_WORDS:
        selector = SIZE_WORDS[words.pop(0)]
    return " ".join(w.strip("'?.,") for w in words).strip(), selector


def _target_text(q: str) -> str | None:
    m = re.search(r"\bthe ([a-z ]+?)'s\b", q) or re.search(
        rf"\b{MEASURE}\b of (?:the )?(.+?)(?:\s+(?:in|at|during|from)\s+(?:time\s+)?[\d(]"
        r"|\s+in\s+[a-z/^0-9]+\s*\?|\?|$)",
        q,
    )
    return m.group(1) if m else None


def rule_spec(question: str, prior: str | None) -> tuple[MeasurementSpec | None, str]:
    q = re.sub(r"\s*\([^)]*\)", " ", question.lower())  # drop parentheticals
    q = re.sub(r"\s+", " ", q).strip().replace(" ?", "?")
    unit_m = re.search(r"\bin\s+([a-z/^0-9²]+)\s*\?\s*$", q)
    unit = UNIT_ALIASES.get(unit_m.group(1), unit_m.group(1)) if unit_m else None
    if unit is not None and unit_to_si(unit) is None:
        unit = None

    if "acceleration" in q:
        quantity = "acceleration"
    elif re.search(r"\b(velocity|speed)\b", q):
        quantity = "speed"
    else:
        quantity = "size"
    timestamp = _num(r"\bat\s+(?:time\s+)?(\d+(?:\.\d+)?)\s*s\b", q)
    window = re.search(r"\b(\d+(?:\.\d+)?)\s*s\s+to\s+(\d+(?:\.\d+)?)\s*s\b", q)
    time_range = (float(window.group(1)), float(window.group(2))) if window else None
    anchor = "first" if "initial" in q else "last" if "final" in q else "timestamp"
    axis = "horizontal" if "horizontal" in q else "vertical" if "vertical" in q else "path"
    second_phrase, second_instance = None, "auto"

    between = re.search(
        r"distance between (?:the )?(.+?) and (?:the )?(.+?)(?:\s+at\s|\s+in\s|\?|$)", q
    )
    if "traveled" in q or "travelled" in q:
        return None, "rule parser: distance travelled is not supported"
    if "orbit" in q and quantity == "size":
        return None, "rule parser: orbit questions need the central object, not in the text"
    if between:
        (target, t_inst), (second_phrase, second_instance) = (
            noun_phrase(between.group(1)), noun_phrase(between.group(2)))  # fmt: skip
        statistic = "separation"
    else:
        text = _target_text(q)
        if text is None:
            return None, "rule parser: no target phrase found"
        target, t_inst = noun_phrase(text)
        if quantity == "size":
            statistic = "extent"
            word = next((w for w in AXIS_WORDS if re.search(rf"\b{w}\b", q)), None)
            axis = AXIS_WORDS[word] if word else "longest"
        elif timestamp is not None and time_range is None:
            statistic = "instantaneous"
        else:
            statistic = "average"
    if not target:
        return None, "rule parser: empty target phrase"

    parsed = parse_prior(prior)
    if parsed is None:
        return None, "rule parser: prior not in the form 'X = value unit'"
    ref_text = re.sub(rf"\b{MEASURE}\b", " ", parsed.what.lower())
    ref_text = re.sub(r"\bof\b|'s\b", " ", ref_text)
    ref_phrase, ref_inst = noun_phrase(ref_text)
    ref_axis_word = next(
        (w for w in AXIS_WORDS if re.search(rf"\b{w}\b", parsed.what.lower())), None
    )
    if parsed.kind == "acceleration":
        ref = dict(reference_phrase=None, reference_kind="acceleration",
                   reference_statistic="acceleration", reference_axis="vertical")  # fmt: skip
    elif parsed.kind == "speed":
        ref = dict(reference_phrase=ref_phrase or None, reference_kind="speed",
                   reference_statistic="average_speed", reference_axis="path")  # fmt: skip
    else:
        ref = dict(reference_phrase=ref_phrase or None, reference_kind="size",
                   reference_statistic="extent",
                   reference_axis=AXIS_WORDS.get(ref_axis_word, "longest"))  # fmt: skip
    rp = ref["reference_phrase"]
    same_noun = rp is not None and (rp == target or target.endswith(" " + rp))
    if same_noun and ref_inst in (t_inst, "auto"):
        ref["reference_phrase"] = None  # the prior describes the target itself
    try:
        spec = MeasurementSpec(
            target_phrase=target, target_instance=t_inst, second_phrase=second_phrase,
            second_instance=second_instance, reference_instance=ref_inst,
            reference_value_si=parsed.value_si, reference_source="question prior (rule parser)",
            quantity=quantity, statistic=statistic, axis=axis, timestamp_s=timestamp,
            time_anchor=anchor if statistic == "separation" else "timestamp",
            time_range_s=time_range, output_unit=unit or DEFAULT_UNIT[quantity],
            depth_info=None, plausible_range_si=(0.0, 1e4), **ref,
        )  # fmt: skip
    except ValueError as exc:
        return None, f"rule parser: {exc}"
    return spec, ""
