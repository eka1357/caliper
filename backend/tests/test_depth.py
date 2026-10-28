"""depth_info parsing on made-up strings in the format seen in QuantiPhy, and the ratio."""

import pytest

from caliper.depth import depth_at, depth_ratio, parse_depth

TEXT = (
    "t=0s, distance_kite_camera =10.0 m\n"
    "t = 2.0s, distance_kite_camera = 14.0 m\n"
    "distance_the_red_door_camera = 20.5 m\n"
    "t=1s, distance_the big tree _and_camera = 8 m\n"
    "distance_the_nearest_bench = 6.0 m"
)


def test_parse_keys_and_times():
    d = parse_depth(TEXT)
    assert d["kite"] == [(0.0, 10.0), (2.0, 14.0)]
    assert d["red_door"] == [(None, 20.5)]
    assert d["big_tree"] == [(1.0, 8.0)]
    assert d["nearest_bench"] == [(None, 6.0)]
    assert parse_depth(None) == {}


def test_depth_interpolates_and_holds():
    d = parse_depth(TEXT)
    assert depth_at(d["kite"], 1.0) == pytest.approx(12.0)
    assert depth_at(d["kite"], 5.0) == pytest.approx(14.0)  # held outside the listed times
    assert depth_at(d["red_door"], 3.0) == pytest.approx(20.5)


def test_ratio_and_missing_key():
    d = parse_depth(TEXT)
    assert depth_ratio(d, "kite", "red_door", 1.0, 0.0) == pytest.approx(12.0 / 20.5)
    with pytest.raises(KeyError, match="reference"):
        depth_ratio(d, "kite", "lamp", 1.0, 0.0)
