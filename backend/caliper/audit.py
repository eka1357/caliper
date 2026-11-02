"""Muse Spark call 2: visual audit of the evidence, veto only (ARCHITECTURE section 8).

Input: the question with its digits removed, the spec's phrases, and 3 to 4 keyframes with the
target outline (cyan), reference outline (amber), the target's trajectory and the frame number
drawn in. No measured value, scale, prior value or interval is ever shown. Output: AuditVerdict.
approve=false turns a measured result into an abstention; the audit never changes a number.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from caliper import config
from caliper.backends import BackendError, LanguageBackend, MetaApiBackend
from caliper.models import AuditVerdict, MeasurementSpec, Track
from caliper.segment import mask_rasters

log = logging.getLogger(__name__)

CYAN, AMBER, WHITE = (255, 255, 0), (0, 191, 255), (255, 255, 255)  # BGR

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "target_is_right_object": {"type": "boolean"},
        "reference_is_right_object": {"type": "boolean"},
        "reference_same_plane": {"type": "string", "enum": ["yes", "no", "unclear"]},
        "occlusion_or_identity_switch": {"type": "boolean"},
        "approve": {"type": "boolean"},
        "reason": {"type": "string"},
    },
    "required": [
        "target_is_right_object",
        "reference_is_right_object",
        "reference_same_plane",
        "occlusion_or_identity_switch",
        "approve",
        "reason",
    ],  # fmt: skip
    "additionalProperties": False,
}

PROMPT = """You audit the evidence behind a video measurement. You do NOT measure anything and \
you will not see any measured number. Deterministic code tracked two objects with a \
segmentation model and will compute the answer from these tracks.

Question (numbers removed): {question}
Target (CYAN outline, white line = its path): {target}
Scale reference (AMBER outline): {reference}

Look at the keyframes (frame numbers in the corner) and answer:
- target_is_right_object: does the cyan outline sit on the object the question asks about, in \
every keyframe?
- reference_is_right_object: does the amber outline sit on the object named as the reference? \
(true if there is no separate reference)
- reference_same_plane: are the reference and the target at about the same distance from the \
camera, so one scale fits both? (yes / no / unclear; yes if there is no separate reference)
- occlusion_or_identity_switch: is the target hidden, merged with another object, or does the \
outline jump to a different object between keyframes?
- approve: false only if the evidence is clearly wrong (wrong object, outline on something \
else, identity switch, reference clearly at a different depth). Do not veto for small outline \
errors.
- reason: one short sentence a user can read, without numbers.
"""


SAME_PLANE_ITEM = (
    "- reference_same_plane: are the reference and the target at about the same distance from "
    "the camera, so one scale fits both? (yes / no / unclear; yes if there is no separate "
    "reference)"
)
DEPTH_SCALED_ITEM = (
    '- reference_same_plane: answer "yes": the distances of both objects from the camera are '
    "known and the scale is already corrected for them, so do not judge depth."
)
DEPTH_VETO = ", reference clearly at a different depth"
assert SAME_PLANE_ITEM in PROMPT and DEPTH_VETO in PROMPT


def strip_numbers(text: str) -> str:
    return re.sub(r"\d+(?:[.,]\d+)?", "#", text)


def keyframe_ids(target: Track, lo_s: float, hi_s: float, k: int = 4) -> list[int]:
    """Up to k detected target frames spread over [lo_s, hi_s] (start, middle, end)."""
    frames = [f.frame for f in target.frames if lo_s - 1e-9 <= f.t_s <= hi_s + 1e-9]
    frames = frames or [f.frame for f in target.frames]
    idx = np.unique(np.linspace(0, len(frames) - 1, num=min(k, len(frames))).round().astype(int))
    return [frames[i] for i in idx]


def render(
    video: Path, target: Track, reference: Track | None, frames: list[int], max_width: int = 640,
    before_draw: Callable[[np.ndarray, int], None] | None = None,
) -> list[bytes]:  # fmt: skip
    """PNG keyframes with outlines, trajectory and frame number; no measured numbers.

    before_draw(img, frame) edits the raw frame first (demo copies blur faces, plates and
    artwork there); the audit itself never passes it, so its images are unchanged."""
    w, h = target.width, target.height
    t_masks = mask_rasters(video, target.phrase, str(target.object_ordinal), frames, w, h)
    r_masks = (
        mask_rasters(video, reference.phrase, str(reference.object_ordinal), frames, w, h)
        if reference is not None
        else {}
    )
    path = np.array([f.centroid_px for f in target.frames], np.int32).reshape(-1, 1, 2)
    cap = cv2.VideoCapture(str(video))
    out = []
    for f in frames:
        cap.set(cv2.CAP_PROP_POS_FRAMES, f)
        ok, img = cap.read()
        if not ok:
            continue
        if before_draw is not None:
            before_draw(img, f)
        cv2.polylines(img, [path], False, WHITE, 1, cv2.LINE_AA)
        for masks, color in ((r_masks, AMBER), (t_masks, CYAN)):
            if f in masks:
                cnts, _ = cv2.findContours(masks[f], cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
                cv2.drawContours(img, cnts, -1, color, 2)
        cv2.putText(img, f"frame {f}", (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 3)
        cv2.putText(img, f"frame {f}", (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, WHITE, 1)
        if img.shape[1] > max_width:
            img = cv2.resize(img, (max_width, round(img.shape[0] * max_width / img.shape[1])))
        ok, png = cv2.imencode(".png", img)
        if ok:
            out.append(png.tobytes())
    cap.release()
    return out


def audit(
    video: Path,
    question: str,
    spec: MeasurementSpec,
    target: Track,
    reference: Track | None,
    window_s: tuple[float, float],
    backend: LanguageBackend | None = None,
    depth_scaled: bool = False,
) -> tuple[AuditVerdict, dict[str, Any]]:
    """One Muse Spark call. A failed call vetoes (AGENTS.md rule 3: if the audit fails, abstain).

    depth_scaled: the camera distances are known (QuantiPhy 3D depth_info) and the engine already
    corrects the scale for them, so the same-plane question is dropped from the prompt.
    """
    frames = keyframe_ids(target, *window_s)
    images = render(video, target, reference, frames)
    prompt = PROMPT.format(
        question=strip_numbers(question),
        target=spec.target_phrase,
        reference=spec.reference_phrase or "none (the target sets its own scale)",
    )
    if depth_scaled:
        prompt = prompt.replace(SAME_PLANE_ITEM, DEPTH_SCALED_ITEM).replace(DEPTH_VETO, "")
    backend = backend or MetaApiBackend()
    try:
        raw, info = backend.json_with_images(images, prompt, SCHEMA, "AuditVerdict")
        verdict = AuditVerdict(**raw)
    except (BackendError, ValueError) as exc:
        log.warning("audit call failed, abstaining: %s", exc)
        verdict = AuditVerdict(target_is_right_object=False, reference_is_right_object=False,
                               reference_same_plane="unclear", occlusion_or_identity_switch=False,
                               approve=False,
                               reason="The evidence check could not run.")  # fmt: skip
        info = {"usage": {"input_tokens": 0, "output_tokens": 0}, "cost_usd": 0.0}
    return verdict, {**info, "keyframes": frames, "images": len(images)}


def enabled() -> bool:
    return config.AUDIT_ENABLED
