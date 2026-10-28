"""Parse a prior written as "<object description> = <value> <unit>" into SI. Pure, no I/O.

Used by the rule-parser ablation, and to check the spec writer's reference_value_si: when the
prior parses, the parsed value wins over the model's (unit conversion stays deterministic).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_LENGTH = {"m": 1.0, "meter": 1.0, "meters": 1.0, "metre": 1.0, "metres": 1.0, "cm": 0.01,
           "mm": 0.001, "km": 1000.0}  # fmt: skip
_TIME = {"s": 1.0, "sec": 1.0, "h": 3600.0, "hr": 3600.0}

_PRIOR = re.compile(
    r"^\s*(?P<what>.+?)\s*(?:=|:|is)\s*~?\s*(?P<value>[-+]?\d+(?:\.\d+)?)\s*(?P<unit>[^\s,;]+)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ParsedPrior:
    what: str  # e.g. "billiard ball diameter"
    value_si: float
    kind: str  # "size" | "speed" | "acceleration"


def unit_to_si(unit: str) -> tuple[float, str] | None:
    """Factor to SI and the kind of quantity, or None for an unknown unit."""
    u = unit.strip().rstrip(".").replace("²", "^2").replace("**", "^").lower()
    if u.endswith(("/s^2", "/s2")):
        length = u.rsplit("/", 1)[0]
        return (_LENGTH[length], "acceleration") if length in _LENGTH else None
    if "/" in u:
        length, time = u.split("/", 1)
        if length in _LENGTH and time in _TIME:
            return _LENGTH[length] / _TIME[time], "speed"
        return None
    return (_LENGTH[u], "size") if u in _LENGTH else None


def parse_prior(text: str | None) -> ParsedPrior | None:
    if not text:
        return None
    m = _PRIOR.match(text)
    if not m:
        return None
    conv = unit_to_si(m["unit"])
    if conv is None:
        return None
    factor, kind = conv
    return ParsedPrior(m["what"].strip(), float(m["value"]) * factor, kind)
