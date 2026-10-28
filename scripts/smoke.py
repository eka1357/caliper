"""$ Phase 0 smoke test: one muse-spark-1.3 text call and one sam-3.1 concept call.

Spends about $0.01 on the first run; reruns are disk-cache hits and cost $0.
Usage: backend\\.venv\\Scripts\\python.exe scripts\\smoke.py [--video internet_0001] [--phrase "black car"]
"""

from __future__ import annotations

import argparse
import logging
from collections import Counter

from caliper import config
from caliper.meta_client import muse_cost_usd, responses_create
from caliper.normalize import normalize, probe
from caliper.segment import sam_cost_usd, segment


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", default="internet_0001")  # 2D (S2SC), 31 frames
    ap.add_argument("--phrase", default="black car")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    rec = responses_create(
        {
            "model": config.MUSE_MODEL,
            "input": "Reply with the single word: ready",
            "max_output_tokens": config.MUSE_MAX_OUTPUT_TOKENS,
        }
    )
    text = "".join(
        part.get("text", "")
        for item in rec["response"].get("output", [])
        for part in item.get("content") or []
    )
    print(f"muse: text={text.strip()!r} usage={rec['usage']} latency_ms={rec['latency_ms']}")
    print(f"muse: cost_usd={muse_cost_usd(rec['usage']):.6f}")

    src = config.QUANTIPHY_DIR / "validation_videos" / f"{args.video}.mp4"
    video = normalize(src)
    info = probe(video)
    seg = segment(video, args.phrase)
    per_frame = seg.objects_per_frame()
    print(f"sam: video={args.video} source_frames={info['frames']} fps={info['fps']}")
    print(
        f"sam: phrase={args.phrase!r} frames_returned={seg.frames_returned} cache_hit={seg.cache_hit}"
    )
    print(f"sam: objects per frame (count -> frames) {dict(Counter(per_frame.values()))}")
    confs = [d.confidence for d in seg.detections if d.confidence is not None]
    if confs:
        print(f"sam: mean_confidence={sum(confs) / len(confs):.3f} over {len(confs)} detections")
    print(f"sam: diagnostics={seg.diagnostics[:5]} latency_ms={seg.latency_ms}")
    print(f"sam: cost_usd={sam_cost_usd(info['frames']):.6f} (billed on source frames)")


if __name__ == "__main__":
    main()
