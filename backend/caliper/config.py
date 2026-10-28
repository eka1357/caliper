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
# a fixed seeded shuffle of the sorted video_ids, stratified by 2D/3D (human decision,
# 2026-10-28, so holdout is not 15 2D questions vs 68 3D). Seed = building-period start.
SPLIT_SEED = 20261027
SPLIT_HASH_MIN_DEV = 10
SPLIT_HASH_MAX_DEV = 14

# Normalize (ARCHITECTURE section 2)
NORMALIZE_MAX_WIDTH = 1280
NORMALIZE_CRF = 18

# Engine (ARCHITECTURE section 6). Starting values; tune on the QuantiPhy dev split only, and log
# every change in DECISIONS.md.
FIT_WINDOW_MIN_FRAMES = 9  # ARCHITECTURE section 6: window = max(9 frames, 0.30 s)
FIT_WINDOW_MIN_S = 0.30  # ARCHITECTURE section 6
FIT_MIN_POINTS = 5  # human, Phase 0 finding 3: fit detected frames only; fewer than this abstains
AREA_STABLE_BAND = 0.15  # human, Phase 0 finding 4: size frames within +-15% of median mask area
AREA_STABLE_MIN_FRAMES = 5  # same finding: fewer stable frames than this abstains
INSTANCE_MIN_FRAME_SHARE = 0.30  # Phase 1 plan: drop candidates seen on < 30% of frames
SEPARATION_MAX_GAP_S = 0.10  # both objects must be seen within this of the asked time
BOOTSTRAP_B = 500  # ARCHITECTURE section 6
BOOTSTRAP_SEED = 20261027  # fixed so intervals are reproducible; building-period start
JITTER_PX = 1.0  # ARCHITECTURE section 6: reference and target extents jittered by +-1 px
FPS_MISMATCH_TOL = 0.01  # human, Phase 0 finding 1: log when dataset fps differs from ffprobe
# Dev tuning C (human-approved, 2026-10-28): minimum window for acceleration fits only, one
# value chosen from {0.0 (same as speed), 0.6, 1.0} s by dev MRA on the 5 dev 2D acceleration
# questions. See DECISIONS.md.
ACCEL_WINDOW_MIN_S = 0.0  # 1.0 s tried on dev, reverted 2026-10-28 (DECISIONS.md)

# Spec writer (ARCHITECTURE section 4). Structured output (Responses text.format json_schema,
# strict) is confirmed for muse-spark-1.3 at https://dev.meta.ai/docs/structured-output
# (checked 2026-10-29). Output budget covers reasoning; the Phase 0 baseline used up to 32,106
# output tokens on one question, so 4000 would truncate.
SPEC_MAX_OUTPUT_TOKENS = 16_000
SPEC_ALT_PHRASES = 2  # human, Phase 1 lesson 2: two alternatives per phrase, tried with SAM only
PRIOR_MISMATCH_TOL = 0.01  # model's reference_value_si vs the parsed prior; parsed value wins

# Known-size objects the spec writer may use only when the question gives no prior
# (ARCHITECTURE section 4). Sizes in metres, each with its source.
KNOWN_OBJECTS = {
    "INR 10 coin": {"size_m": 0.027, "axis": "disc", "source": "RBI: 27 mm diameter"},
    "cricket ball": {"size_m": 0.072, "axis": "disc", "source": "MCC Law 4: about 72 mm"},
    "A4 sheet": {"size_m": 0.297, "axis": "longest", "source": "ISO 216: 297 x 210 mm"},
    "credit card": {"size_m": 0.0856, "axis": "longest", "source": "ISO/IEC 7810 ID-1: 85.6 mm"},
}

# Checks (ARCHITECTURE section 7, Phase 3). Start values from ARCHITECTURE section 7 or the Phase 3
# plan; tune on the QuantiPhy dev split only and log every change in DECISIONS.md.
SCENE_WIDTH_M = (0.05, 2000.0)  # Phase 3 plan: frame width x scale; internet_0004 gave 1.3 cm
MIN_REFERENCE_PX = 8.0  # Phase 3 plan: the simulation_0193 moons are 2 to 3 px
MIN_REFERENCE_PATH_PX = 20.0  # Phase 3 plan: a speed reference must visibly move
GRAVITY_MIN_R2 = 0.9  # Phase 3 plan: a clear parabola on y
GRAVITY_MIN_DY_PX = 20.0  # Phase 3 plan: a standing person barely moves vertically
SCALE_AGREE_TOL = 0.25  # ARCHITECTURE section 7 (estimates_agree, 25%)
PERSPECTIVE_TOL = 0.15  # Phase 3 plan; internet_0027 showed about 8% across the frame
PERSPECTIVE_MIN_ROWS_PX = 40.0  # need this vertical spread of the reference to fit a slope
DEPTH_CHANGE_TOL = 0.30  # Phase 3 plan: apparent linear size change over the window, 2D only
TARGET_FOUND_SHARE = 0.80  # ARCHITECTURE section 7
REFERENCE_FOUND_SHARE = (
    0.20  # ARCHITECTURE section 7 said 0.50; dev tuning 2026-10-29 (DECISIONS.md)
)
MAX_GAP_FRAMES = 3  # ARCHITECTURE section 7 (track_continuity)
MASK_CV_MAX = 0.30  # ARCHITECTURE section 7 said 0.25; dev tuning 2026-10-29 (DECISIONS.md)
INTERVAL_HALF_MAX = 0.50  # ARCHITECTURE section 7 (interval_width)
CHECKS_ENABLED = True
AUDIT_ENABLED = True  # ARCHITECTURE section 8; the runner turns it off for caliper_no_audit
