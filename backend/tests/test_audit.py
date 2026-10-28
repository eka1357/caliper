"""Visual audit with a fake backend: no numbers reach the model; veto only."""

import re
from pathlib import Path

from caliper import audit
from caliper.backends import BackendError
from caliper.models import MeasurementSpec, Track, TrackFrame


def track(frames=range(30)) -> Track:
    ext = {"horizontal": 10.0, "vertical": 10.0, "longest": 10.0, "shortest": 10.0, "disc": 10.0}
    fs = [TrackFrame(frame=f, t_s=f / 30, box=(0, 0, 1, 1), confidence=0.9, area_px=100,
                     centroid_px=(10.0 + f, 20.0), extent_px=ext) for f in frames]  # fmt: skip
    return Track(phrase="red ball", object_ordinal=0, frames=fs, fps=30, width=640, height=360)


SPEC = MeasurementSpec(
    target_phrase="red ball", reference_phrase="blue box", reference_kind="size",
    reference_value_si=0.5, reference_source="question prior", quantity="speed",
    statistic="instantaneous", timestamp_s=1.0, output_unit="m/s", depth_info=None,
    plausible_range_si=(0, 10),
)  # fmt: skip


class Fake:
    name = "fake"

    def __init__(self, raw=None, fail=False):
        self.raw, self.fail, self.prompts = raw, fail, []

    def json_with_images(self, images, prompt, schema, schema_name):
        self.prompts.append(prompt)
        if self.fail:
            raise BackendError("down")
        return self.raw, {"usage": {"input_tokens": 1, "output_tokens": 1}, "cost_usd": 0.0}


def verdict(**kw):
    base = dict(target_is_right_object=True, reference_is_right_object=True,
                reference_same_plane="yes", occlusion_or_identity_switch=False, approve=True,
                reason="Outlines are on the named objects.")  # fmt: skip
    base.update(kw)
    return base


def test_prompt_has_no_numbers(monkeypatch):
    monkeypatch.setattr(audit, "render", lambda *a, **k: [b"png"] * 4)
    fake = Fake(verdict())
    audit.audit(Path("v.mp4"), "How fast is the red ball at 1.25 s in m/s? Prior: box = 50 cm",
                SPEC, track(), track(), (0.8, 1.2), fake)  # fmt: skip
    assert not re.search(r"\d", fake.prompts[0].replace("frame numbers", ""))


def test_veto_and_failure(monkeypatch):
    monkeypatch.setattr(audit, "render", lambda *a, **k: [b"png"] * 3)
    v, _ = audit.audit(Path("v.mp4"), "q", SPEC, track(), None, (0, 1),
                       Fake(verdict(approve=False, reason="Outline on the shadow.")))  # fmt: skip
    assert v.approve is False and "shadow" in v.reason
    v, _ = audit.audit(Path("v.mp4"), "q", SPEC, track(), None, (0, 1), Fake(fail=True))
    assert v.approve is False  # AGENTS.md rule 3: if the audit fails, abstain


def test_keyframes_span_the_window():
    assert audit.keyframe_ids(track(), 0.2, 0.8) == [6, 12, 18, 24]
    assert audit.keyframe_ids(track(range(3)), 0, 10) == [0, 1, 2]


def test_schema_matches_verdict_fields():
    from caliper.models import AuditVerdict

    assert set(audit.SCHEMA["properties"]) == set(AuditVerdict.model_fields)
    assert audit.SCHEMA["additionalProperties"] is False
