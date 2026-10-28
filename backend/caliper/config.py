"""Every threshold, limit, price and path in one place. Each value says where it came from."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Repo root: backend/caliper/config.py -> parents[2]
ROOT = Path(__file__).resolve().parents[2]

# Load .env from the repo root into the environment. Values are never logged.
load_dotenv(ROOT / ".env")


def _path(var: str, default: str) -> Path:
    value = Path(os.environ.get(var, default))
    return value if value.is_absolute() else ROOT / value


# Meta Model API (AGENTS.md section 3, checked Oct 2026)
META_API_BASE_URL = os.environ.get("META_API_BASE_URL", "https://api.meta.ai/v1")
MUSE_MODEL = os.environ.get("MUSE_MODEL", "muse-spark-1.3")
SAM_MODEL = os.environ.get("SAM_MODEL", "sam-3.1")

# Muse Spark: reasoning shares the output budget, so at least 4000 (AGENTS.md section 3)
MUSE_MAX_OUTPUT_TOKENS = 4000

# Prices in USD (AGENTS.md section 3)
MUSE_USD_PER_M_INPUT = 1.25
MUSE_USD_PER_M_OUTPUT = 4.25
SAM_USD_PER_FRAME = 0.20 / 1000

# SAM 3.1 request limits (AGENTS.md section 3)
SAM_MAX_OBJECTS_PER_FRAME = 16
SAM_MAX_FRAMES_PER_REQUEST = 15_000

# Paths (.env.example)
CACHE_DIR = _path("CACHE_DIR", "data/cache")
QUANTIPHY_DIR = _path("QUANTIPHY_DIR", "data/quantiphy-val")
FIELD_DIR = _path("FIELD_DIR", "data/field")
NORMALIZED_DIR = CACHE_DIR / "normalized"

# QuantiPhy split (EVAL_PROTOCOL section 2). The sha256 rule gave 8 dev / 16 holdout on the
# 24 validation videos, outside the allowed 10 to 14, so the protocol's fallback applies:
# a fixed seeded shuffle of the sorted video_ids, first half dev. Seed = building-period start.
SPLIT_SEED = 20261027
SPLIT_HASH_MIN_DEV = 10
SPLIT_HASH_MAX_DEV = 14

# Normalize (ARCHITECTURE section 2)
NORMALIZE_MAX_WIDTH = 1280
NORMALIZE_CRF = 18
