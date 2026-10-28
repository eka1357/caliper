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
