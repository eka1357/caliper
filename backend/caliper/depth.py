"""QuantiPhy depth_info parsing and the pinhole depth ratio (ARCHITECTURE section 6). Pure.

Format seen on all 89 3D validation questions (inspected 2026-10-28, before this code): free
text, one line per distance, `[t=<time>s, ]distance_<object>[_camera] = <metres> m`. Times are
optional, spacing varies, object names are free-form. With one camera, metres per pixel grow
linearly with distance: s(target) = s(reference) * Z_target / Z_reference.
"""

from __future__ import annotations

import re

import numpy as np

_LINE = re.compile(
    r"^\s*(?:t\s*=\s*(?P<t>\d+(?:\.\d+)?)\s*s?\s*,\s*)?distance[_ ]?(?P<key>.+?)\s*=\s*"
    r"(?P<z>\d+(?:\.\d+)?)\s*m\b",
    re.IGNORECASE,
)


def clean_key(raw: str) -> str:
    key = re.sub(r"[\s_]+", "_", raw.strip().lower()).strip("_")
    key = re.sub(r"_(?:and_)?camera$", "", key)
    return re.sub(r"^the_", "", key)


def parse_depth(text: str | None) -> dict[str, list[tuple[float | None, float]]]:
    """{object key: [(time or None, distance in metres), ...]} in file order."""
    out: dict[str, list[tuple[float | None, float]]] = {}
    for line in (text or "").splitlines():
        m = _LINE.match(line)
        if m:
            t = float(m["t"]) if m["t"] is not None else None
            out.setdefault(clean_key(m["key"]), []).append((t, float(m["z"])))
    return out


def depth_at(entries: list[tuple[float | None, float]], t: float) -> float:
    """Distance at time t: linear between listed times, held constant outside them; untimed
    entries are constant."""
    timed = sorted((et, z) for et, z in entries if et is not None)
    if not timed:
        return float(np.median([z for _, z in entries]))
    ts, zs = zip(*timed, strict=True)
    return float(np.interp(t, ts, zs))


def depth_ratio(
    depth: dict[str, list[tuple[float | None, float]]],
    target_key: str | None,
    reference_key: str | None,
    t_target: float,
    t_reference: float,
) -> float:
    """Z_target(t_target) / Z_reference(t_reference). Raises KeyError naming a missing key."""
    for name, key in (("target", target_key), ("reference", reference_key)):
        if key is None or key not in depth:
            raise KeyError(name)
    return depth_at(depth[target_key], t_target) / depth_at(depth[reference_key], t_reference)
