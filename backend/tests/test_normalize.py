import subprocess

from caliper.normalize import normalize, probe


def test_normalize_keeps_fps_and_frames(tmp_path):
    src = tmp_path / "src.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=320x240:rate=24",
         "-t", "1", "-c:v", "mpeg4", str(src)],
        check=True,
    )  # fmt: skip
    out = normalize(src, tmp_path / "norm")
    before, after = probe(src), probe(out)
    assert after["codec"] == "h264"
    assert after["fps"] == before["fps"] == 24
    assert after["frames"] == before["frames"] == 24
    assert normalize(src, tmp_path / "norm") == out  # built once


def test_scale_filter_caps_only_tall_portrait_clips():
    from caliper import config
    from caliper.normalize import scale_filter

    cap = config.NORMALIZE_MAX_WIDTH
    old = f"scale='min({cap},iw)':-2"
    # Landscape, square and short portrait clips keep the original filter (byte-identical cache)
    assert scale_filter(3840, 2160) == old
    assert scale_filter(1080, 1080) == old
    assert scale_filter(720, 1280) == old
    # Only portrait clips taller than the cap get the height cap
    assert scale_filter(774, 3370) == f"scale=-2:'min({cap},ih)'"
