"""Spec writer with a fake backend (no network), and the prior parser."""

from pathlib import Path

import pytest

from caliper import config
from caliper.priors import parse_prior
from caliper.spec import PROPERTIES, SCHEMA, SpecError, postprocess, write_spec


def raw_spec(**kw):
    base = {
        "target_phrase": "blue bicycle",
        "target_alt_phrases": ["bicycle", "cyclist", "bike"],
        "target_instance": "auto",
        "second_phrase": None,
        "second_instance": "auto",
        "reference_phrase": "bus",
        "reference_alt_phrases": ["bus", "city bus", "large vehicle"],
        "reference_instance": "auto",
        "reference_kind": "size",
        "reference_statistic": "extent",
        "reference_axis": "longest",
        "reference_value_si": 12.0,
        "reference_source": "question prior",
        "quantity": "speed",
        "statistic": "instantaneous",
        "axis": "path",
        "timestamp_s": 2.0,
        "time_anchor": "timestamp",
        "time_range_s": None,
        "output_unit": "km/h",
        "plausible_range_si": [0, 20],
        "notes": "",
    }
    base.update(kw)
    return base


class FakeBackend:
    name = "fake"

    def __init__(self, raw):
        self.raw, self.calls = raw, 0

    def json_with_video(self, video, prompt, schema, schema_name):
        self.calls += 1
        assert "do NOT estimate the answer" in prompt
        return self.raw, {"usage": {"input_tokens": 1, "output_tokens": 1}, "cost_usd": 0.0}


def test_schema_is_strict_and_has_no_answer_field():
    assert SCHEMA["additionalProperties"] is False
    assert SCHEMA["required"] == list(PROPERTIES)
    assert not any("answer" in k or k == "value" for k in PROPERTIES)


def test_write_spec_one_call_alt_phrases_trimmed():
    fake = FakeBackend(raw_spec())
    spec, info = write_spec(Path("x.mp4"), "How fast?", "the bus is 12 m long", backend=fake)
    assert fake.calls == 1
    assert spec.target_alt_phrases == ["bicycle", "cyclist"]  # 2 kept
    assert spec.reference_alt_phrases == ["city bus", "large vehicle"]  # main phrase dropped
    assert info["raw"]["target_phrase"] == "blue bicycle"


def test_answer_field_is_ignored():
    spec = postprocess(raw_spec(answer=42.0, value=7), "the bus is 12 m long", None)
    assert not hasattr(spec, "answer")


def test_parsed_prior_replaces_model_value():
    spec = postprocess(raw_spec(reference_value_si=5.72), "billiard ball diameter = 57.2 mm", None)
    assert spec.reference_value_si == pytest.approx(0.0572)
    assert "replaced by parsed prior" in spec.notes


def test_known_object_only_without_prior():
    ko = raw_spec(reference_kind="known_object", reference_phrase="cricket ball",
                  reference_value_si=1.0)  # fmt: skip
    spec = postprocess(ko, None, None)
    assert spec.reference_value_si == config.KNOWN_OBJECTS["cricket ball"]["size_m"]
    assert spec.reference_axis == "disc"
    with pytest.raises(SpecError, match="gives a prior"):
        postprocess(ko, "the bus is 12 m long", None)
    with pytest.raises(SpecError, match="not allowed"):
        postprocess(raw_spec(reference_kind="known_object", reference_phrase="banana"), None, None)


def test_invalid_spec_raises_without_retry():
    fake = FakeBackend(raw_spec(quantity="temperature"))
    with pytest.raises(SpecError, match="validation"):
        write_spec(Path("x.mp4"), "q", None, backend=fake)
    assert fake.calls == 1


@pytest.mark.parametrize(
    ("text", "value", "kind"),
    [
        ("billiard ball diameter = 57.2 mm", 0.0572, "size"),
        ("gravity acc = 9.8 m/s^2", 9.8, "acceleration"),
        ("pedestrian walking speed ~1.1 m/s", None, None),  # no '=': not parsed
        ("walking velocity = 1.25 m/s", 1.25, "speed"),
        ("height of the astronaut = 2.2 m", 2.2, "size"),
        ("ruler calibre = 1 cm", 0.01, "size"),
        ("car speed = 36 km/h", 10.0, "speed"),
    ],
)
def test_parse_prior(text, value, kind):
    p = parse_prior(text)
    if value is None:
        assert p is None
    else:
        assert p.value_si == pytest.approx(value) and p.kind == kind
