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


def display_size(path: Path) -> tuple[int, int]:
    """Width and height as shown, after the rotation in the stream's side data."""
    out = subprocess.run(
        [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height:stream_side_data=rotation",
            "-of", "json", str(path),
        ],
        check=True, capture_output=True, text=True,
    ).stdout  # fmt: skip
    s = json.loads(out)["streams"][0]
    rot = next((int(d["rotation"]) for d in s.get("side_data_list", []) if "rotation" in d), 0)
    w, h = int(s["width"]), int(s["height"])
    return (h, w) if abs(rot) % 180 == 90 else (w, h)


def scale_filter(width: int, height: int) -> str:
    """Cap the longest side at NORMALIZE_MAX_WIDTH. Only portrait clips taller than the cap get a
    new filter; every other clip keeps the original width-only filter, so earlier normalized
    files (QuantiPhy, the 2D/3D cache) stay byte-identical."""
    cap = config.NORMALIZE_MAX_WIDTH
    if height > width and height > cap:
        return f"scale=-2:'min({cap},ih)'"
    return f"scale='min({cap},iw)':-2"


def normalize(src: Path, out_dir: Path | None = None) -> Path:
    """Return the normalized copy, named by the source's sha256 so it is built once."""
    src = Path(src)
    out_dir = Path(out_dir) if out_dir is not None else config.NORMALIZED_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    vf = scale_filter(*display_size(src))
    # A clip that needs the height cap gets its own name, so an older width-only copy is never
    # reused; every other name is unchanged (cache keys use the normalized file's sha256).
    tag = "" if vf == scale_filter(1, 1) else f"-h{config.NORMALIZE_MAX_WIDTH}"
    dst = out_dir / f"{file_sha256(src)[:16]}{tag}.mp4"
    if dst.exists():
        return dst
    before = probe(src)
    tmp = dst.with_suffix(".tmp.mp4")
    subprocess.run(
        [
            "ffmpeg", "-y", "-v", "error", "-i", str(src), "-an",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", str(config.NORMALIZE_CRF),
            "-pix_fmt", "yuv420p",
            "-vf", vf,
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
