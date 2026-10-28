"""$ Caliper on QuantiPhy with hand-written specs (Phase 1: dev split, 2D questions only).

Per question: SAM 3.1 once per (video, phrase) through the disk cache, instance selection,
the deterministic engine, unit conversion. Abstentions leave parsed_value blank (a miss for
the scorer, EVAL_PROTOCOL section 4.4). Writes eval/quantiphy/model_outputs/caliper.csv,
scores it with the official evaluator, adds the caliper/dev row to eval/results.csv, and saves
one run JSON per question under data/cache/runs/phase1/.

  python eval/quantiphy.py --estimate   # SAM frames and cost of uncached requests, no API calls
  python eval/quantiphy.py              # spends credits on cache misses only
  python eval/quantiphy.py --worst 5    # the worst questions from the last run (no API calls)
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date
from pathlib import Path

import pandas as pd
from baseline import DATASET, EVAL, QP, link_videos, score, write_results
from baseline_analysis import load, update_results
from caliper import config, engine
from caliper.engine import Abstain
from caliper.meta_client import DiskCache, file_sha256, request_key
from caliper.models import MeasurementSpec, Result
from caliper.normalize import normalize, probe
from caliper.segment import sam_cost_usd, segment, select_instance, tracks_from_segmentation

log = logging.getLogger("quantiphy")
SPECS = EVAL / "specs" / "phase1_dev_2d.json"
VARIANT = "caliper"
RUNS = config.CACHE_DIR / "runs" / "phase1"
CEILING_USD = 0.75  # Phase 1 plan: stop if the uncached SAM estimate is above this


def load_specs() -> list[dict]:
    return json.loads(SPECS.read_text(encoding="utf-8"))["specs"]


def phrases_of(spec: MeasurementSpec) -> list[str]:
    return [p for p in (spec.target_phrase, spec.second_phrase, spec.reference_phrase) if p]


def sam_cached(video: Path, phrase: str) -> bool:
    payload = {
        "model": config.SAM_MODEL,
        "video_sha256": file_sha256(video),
        "phrase": phrase,
        "metadata": {"include_confidence": "true"},
    }
    return DiskCache().get(request_key({"kind": "sam", **payload})) is not None


class Clip:
    """A normalized video with its probed time base and its segmentations, one per phrase."""

    def __init__(self, video_id: str, src: Path, dataset_fps: float) -> None:
        self.video_id = video_id
        self.path = normalize(src)
        info = probe(self.path)
        self.fps, self.frames = float(info["fps"]), int(info["frames"])
        self.width, self.height = int(info["width"]), int(info["height"])
        self.fps_mismatch = None
        if abs(self.fps - dataset_fps) > config.FPS_MISMATCH_TOL:
            self.fps_mismatch = {"probed": self.fps, "dataset": dataset_fps}
            log.warning("%s: ffprobe fps %.4f, dataset fps %s", video_id, self.fps, dataset_fps)
        self._tracks: dict[str, list] = {}

    def tracks(self, phrase: str) -> list:
        if phrase not in self._tracks:
            seg = segment(self.path, phrase)
            self._tracks[phrase] = tracks_from_segmentation(seg, self.fps, self.width, self.height)
        return self._tracks[phrase]

    def pick(self, phrase: str, selector: str):
        tracks = self.tracks(phrase)
        if not tracks:
            raise Abstain(f"SAM found no '{phrase}'")
        return select_instance(tracks, selector, self.frames)


def run_one(entry: dict, clip: Clip) -> Result:
    spec = MeasurementSpec(**entry["spec"]) if entry["spec"] else None
    artifacts = {"video_id": clip.video_id, "fps": clip.fps, "fps_mismatch": clip.fps_mismatch}
    base = dict(
        run_id=f"phase1-{entry['row_id']}", unit=spec.output_unit if spec else "",
        quantity=spec.quantity if spec else "size", checks=[], audit=None,
        backend="meta_api", cost_usd=0.0, timings_ms={},
    )  # fmt: skip
    if entry["abstain_reason"]:
        stub = MeasurementSpec(
            target_phrase="", reference_phrase=None, reference_kind="given_prior",
            reference_value_si=None, reference_source="", quantity="size", statistic="extent",
            timestamp_s=None, output_unit="", depth_info=None, plausible_range_si=(0, 0),
        )  # fmt: skip
        return Result(status="abstained", value=None, interval_90=None, spec=stub,
                      scale_m_per_px=None, method="spec", abstain_reason=entry["abstain_reason"],
                      artifacts=artifacts, **base)  # fmt: skip
    try:
        target, t_rule = clip.pick(spec.target_phrase, spec.target_instance)
        second, s_rule = (
            clip.pick(spec.second_phrase, spec.second_instance)
            if spec.second_phrase
            else (None, "")
        )
        reference, r_rule = (
            clip.pick(spec.reference_phrase, spec.reference_instance)
            if spec.reference_phrase
            else (None, "reference = target")
        )
        artifacts["instances"] = {"target": t_rule, "second": s_rule, "reference": r_rule}
        artifacts["detected_frames"] = {
            "target": len(target.frames),
            "second": len(second.frames) if second else None,
            "reference": len(reference.frames) if reference else None,
            "clip": clip.frames,
        }
        m = engine.measure(spec, target, reference, second)
    except Abstain as exc:
        return Result(status="abstained", value=None, interval_90=None, spec=spec,
                      scale_m_per_px=None, method="engine", abstain_reason=str(exc),
                      artifacts=artifacts, **base)  # fmt: skip
    value = engine.to_unit(m.value_si, spec.output_unit)
    interval = (
        tuple(engine.to_unit(x, spec.output_unit) for x in m.interval_si) if m.interval_si else None
    )
    artifacts["value_px"] = m.value_px
    artifacts["bootstrap_ok"] = m.bootstrap_ok
    return Result(status="measured", value=value, interval_90=interval, spec=spec,
                  scale_m_per_px=m.scale_m_per_px, method=m.method, abstain_reason=None,
                  artifacts=artifacts, **base)  # fmt: skip


def needed(specs: list[dict], clips: dict[str, Clip]) -> dict[tuple[str, str], bool]:
    """(video_id, phrase) -> already cached."""
    out = {}
    for e in specs:
        if e["spec"] is None:
            continue
        for p in phrases_of(MeasurementSpec(**e["spec"])):
            key = (e["video_id"], p)
            if key not in out:
                out[key] = sam_cached(clips[e["video_id"]].path, p)
    return out


def worst(n: int) -> None:
    df = load(VARIANT)
    runs = {
        r: json.loads((RUNS / f"{r}.json").read_text(encoding="utf-8")) for r in df["Unnamed: 0"]
    }
    df = df.assign(
        status=[runs[r]["status"] for r in df["Unnamed: 0"]],
        reason=[runs[r]["abstain_reason"] or "" for r in df["Unnamed: 0"]],
    )
    cols = ["Unnamed: 0", "video_id", "category", "status", "pred", "ground_truth_posterior", "mra"]
    for _, r in df.sort_values(["mra", "Unnamed: 0"]).head(n).iterrows():
        run = runs[r["Unnamed: 0"]]
        print(r[cols].to_dict())
        print(f"   reason={r['reason']!r}")
        print(f"   method={run['method']}")
        print(f"   instances={run['artifacts'].get('instances')}")
        print(f"   detected={run['artifacts'].get('detected_frames')} "
              f"scale={run['scale_m_per_px']} px={run['artifacts'].get('value_px')}")  # fmt: skip


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--estimate", action="store_true")
    ap.add_argument("--worst", type=int, default=0)
    args = ap.parse_args()
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    if args.worst:
        worst(args.worst)
        return

    dataset = pd.read_csv(DATASET).set_index("Unnamed: 0", drop=False)
    specs = load_specs()
    videos = link_videos()
    fps = dataset.groupby("video_id")["fps"].first()
    clips = {v: Clip(v, videos[v], float(fps[v])) for v in sorted({e["video_id"] for e in specs})}
    need = needed(specs, clips)
    misses = [(v, p) for (v, p), hit in need.items() if not hit]
    est = sam_cost_usd(sum(clips[v].frames for v, _ in misses))
    full_cost = sam_cost_usd(sum(clips[v].frames for v, _ in need))
    print(f"SAM requests: {len(need)} ({len(misses)} not cached)")
    for v, p in misses:
        print(f"  miss: {v} '{p}' frames={clips[v].frames}")
    print(f"estimate: uncached cost_usd={est:.4f}; cost of the run from scratch={full_cost:.4f}")
    if args.estimate:
        return
    if est > CEILING_USD:
        sys.exit(f"STOP: estimate ${est:.2f} is above ${CEILING_USD:.2f}")

    RUNS.mkdir(parents=True, exist_ok=True)
    preds = {}
    for e in specs:
        res = run_one(e, clips[e["video_id"]])
        (RUNS / f"{e['row_id']}.json").write_text(res.model_dump_json(indent=1), encoding="utf-8")
        preds[e["row_id"]] = res.value
        print(f"{e['row_id']} {e['video_id']}: {res.status} {res.value} {res.unit} "
              f"{res.abstain_reason or ''}")  # fmt: skip

    rows = dataset.loc[[e["row_id"] for e in specs]].reset_index(drop=True)
    rows["parsed_value"] = [preds[r] for r in rows["Unnamed: 0"]]
    rows.to_csv(QP / "model_outputs" / f"{VARIANT}.csv", index=False)
    m = score(rows, "dev", VARIANT)
    write_results(
        [
            {
                "variant": VARIANT,
                "split": "dev",
                "mra_average": "",  # the scorer averages all 4 categories; Phase 1 is 2D only
                "mra_S2": m.get("mra_S2"),
                "mra_D2": m.get("mra_D2"),
                "mra_S3": "",
                "mra_D3": "",
                "abstain_rate": m.get("invalid_percentage", 0) / 100,
                "n": len(rows),
                "cost_usd": round(full_cost, 4),
                "run_date": date.today().isoformat(),
                "source": "eval/quantiphy.py (dev 2D only; hand-written specs "
                "eval/specs/phase1_dev_2d.json)",
            }
        ]
    )
    update_results()
    abstained = sum(v is None for v in preds.values())
    print(f"abstained {abstained}/{len(preds)}; S2={m.get('mra_S2')} D2={m.get('mra_D2')}")


if __name__ == "__main__":
    main()
