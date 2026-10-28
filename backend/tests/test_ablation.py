"""Rule-parser ablation on made-up questions (generic patterns, no QuantiPhy text)."""

import sys

import pytest

from caliper import config

sys.path.insert(0, str(config.ROOT / "eval"))
from ablation import noun_phrase, rule_spec  # noqa: E402


def test_noun_phrase_position_and_size_words():
    assert noun_phrase("red cup on the left") == ("red cup", "left")
    assert noun_phrase("big truck") == ("truck", "largest")
    assert noun_phrase("dog standing in the middle (the brown one)") == ("dog", "middle")


def test_instantaneous_speed_with_size_prior():
    spec, why = rule_spec("What is the speed of the red car at 2.5s in km/h?",
                          "length of the truck = 8 m")  # fmt: skip
    assert why == ""
    assert (spec.target_phrase, spec.quantity, spec.statistic) == (
        "red car",
        "speed",
        "instantaneous",
    )
    assert spec.timestamp_s == 2.5 and spec.output_unit == "km/h"
    assert spec.reference_phrase == "truck" and spec.reference_value_si == 8.0


def test_average_over_window_and_possessive():
    spec, _ = rule_spec("What is the green kite's average velocity in 1.00s to 3.00s in m/s?",
                        "kite width = 90 cm")  # fmt: skip
    assert spec.target_phrase == "green kite" and spec.statistic == "average"
    assert spec.time_range_s == (1.0, 3.0)
    assert spec.reference_phrase is None  # the prior describes the target itself
    assert spec.reference_value_si == pytest.approx(0.9)


def test_separation_with_anchor_and_gravity_prior():
    spec, _ = rule_spec("What is the final distance between the blue box and the red box in cm?",
                        "gravity acc = 9.8 m/s^2")  # fmt: skip
    assert spec.statistic == "separation" and spec.time_anchor == "last"
    assert (spec.target_phrase, spec.second_phrase) == ("blue box", "red box")
    assert spec.reference_kind == "acceleration" and spec.reference_phrase is None


def test_size_axis_words():
    spec, _ = rule_spec("What is the height of the lamp post in meters?",
                        "diameter of the wheel = 0.7 m")  # fmt: skip
    assert spec.axis == "vertical" and spec.output_unit == "m"
    assert spec.reference_phrase == "wheel" and spec.reference_axis == "disc"


def test_unsupported_patterns_abstain():
    assert (
        rule_spec("What is the total distance traveled by the cat in m?", "cat length = 0.5 m")[0]
        is None
    )
    assert rule_spec("How big is it?", "the door is tall")[0] is None


def test_at_time_phrasing_and_parentheticals():
    spec, _ = rule_spec(
        "What is the speed of the drone at time 1.5s in m/s?", "drone width = 0.4 m"
    )
    assert spec.target_phrase == "drone" and spec.timestamp_s == 1.5
    assert spec.statistic == "instantaneous"
    q = "What is the vertical distance(up-down) between the cat and the dog at 2 s in m?"
    spec, _ = rule_spec(q,
                        "cat length = 0.5 m")  # fmt: skip
    assert spec.statistic == "separation" and (spec.target_phrase, spec.second_phrase) == (
        "cat",
        "dog",
    )
