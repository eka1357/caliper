"""Engine time and interval at the eval bootstrap (BOOTSTRAP_B) vs the live one (LIVE_BOOTSTRAP_B).

Usage: backend/.venv/Scripts/python.exe scripts/time_bootstrap.py
Uses the synthetic rolling-ball clip from make_placeholder_runs.py ($0, no API). The numbers
are recorded in docs/DECISIONS.md (live bootstrap entry).
"""

from __future__ import annotations

import statistics
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import make_placeholder_runs as ph  # noqa: E402
from caliper import config, engine  # noqa: E402

REPEATS = 7


def main() -> None:
    px_per_m = 40 / 0.5

    def painter(img, layers, t):
        ph.box(img, layers, 540, 40, 40)
        ph.ball(img, layers, "orange ball", 60 + 1.2 * px_per_m * t, 250, 14, ph.BALL)

    with tempfile.TemporaryDirectory() as tmp:
        masks = ph.draw_clip(painter, Path(tmp) / "c.mp4")
    tgt = ph.track("orange ball", masks["orange ball"])
    ref = ph.track("white box", masks["white box"])
    sp = ph.spec("orange ball", 0.5)
    print(f"clip: {ph.N} frames at {ph.FPS:g} fps; truth 1.2 m/s; median of {REPEATS} runs")
    for b in (config.BOOTSTRAP_B, config.LIVE_BOOTSTRAP_B):
        times, m = [], None
        for _ in range(REPEATS):
            t0 = time.perf_counter()
            m = engine.measure(sp, tgt, ref, boot=b)
            times.append((time.perf_counter() - t0) * 1000)
        lo, hi = m.interval_si
        print(
            f"B={b}: engine {statistics.median(times):.0f} ms; value {m.value_si:.4f} m/s; "
            f"90% interval {lo:.4f} to {hi:.4f} (width {hi - lo:.4f})"
        )


if __name__ == "__main__":
    main()
