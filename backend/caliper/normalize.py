"""ffmpeg: H.264 MP4, faststart, no audio, original fps, width capped (ARCHITECTURE section 2)."""

from __future__ import annotations

import json
import logging
import subprocess
from fractions import Fraction
from pathlib import Path

from caliper import config
from caliper.meta_client import file_sha256

log = logging.getLogger(__name__)


def probe(path: Path) -> dict[str, float | int | str]:
    """fps, frame count, size and codec of the first video stream."""
    out = subprocess.run(
        [
            "ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets",
            "-show_entries", "stream=codec_name,width,height,r_frame_rate,nb_read_packets",
            "-of", "json", str(path),
        ],
        check=True, capture_output=True, text=True,
    ).stdout  # fmt: skip
    s = json.loads(out)["streams"][0]
    return {
        "codec": s["codec_name"],
        "width": int(s["width"]),
        "height": int(s["height"]),
        "fps": float(Fraction(s["r_frame_rate"])),
        "frames": int(s["nb_read_packets"]),
    }


def normalize(src: Path, out_dir: Path | None = None) -> Path:
    """Return the normalized copy, named by the source's sha256 so it is built once."""
    src = Path(src)
    out_dir = Path(out_dir) if out_dir is not None else config.NORMALIZED_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    dst = out_dir / f"{file_sha256(src)[:16]}.mp4"
    if dst.exists():
        return dst
    before = probe(src)
    tmp = dst.with_suffix(".tmp.mp4")
    subprocess.run(
        [
            "ffmpeg", "-y", "-v", "error", "-i", str(src), "-an",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", str(config.NORMALIZE_CRF),
            "-pix_fmt", "yuv420p",
            "-vf", f"scale='min({config.NORMALIZE_MAX_WIDTH},iw)':-2",
            "-movflags", "+faststart", str(tmp),
        ],
        check=True,
    )  # fmt: skip
    after = probe(tmp)
    if abs(before["fps"] - after["fps"]) > 1e-3 or before["frames"] != after["frames"]:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"normalize changed timing for {src.name}: {before} -> {after}")
    tmp.replace(dst)
    log.info("normalized %s -> %s", src.name, dst.name)
    return dst
