"""Measured facts and spend from the disk cache (no API calls).

Muse Spark tokens and latency come from the cached chat records (the baseline) and responses
records (smoke test, tracking phrases, spec writer). Phase 0 SAM requests are matched to their
clips through eval/phase0_tracking*.csv. All SAM requests (every phase) are matched by trying,
on every validation video, every phrase in the tracking CSVs and eval/specs/*.json (main and
alternative phrases, and phrases quoted in spec revisions) plus the rule parser's phrases
(eval/ablation.py). Billed frames come from ffprobe on the normalized video.

  python eval/cost_summary.py
"""

from __future__ import annotations

import csv
import json
import re
import statistics as st

import pandas as pd
from ablation import rule_spec
from baseline import DATASET, EVAL, link_videos
from caliper import config
from caliper.meta_client import DiskCache, file_sha256, muse_cost_usd, request_key
from caliper.normalize import normalize, probe
from caliper.segment import sam_cost_usd

TRACKING = [EVAL / "phase0_tracking.csv", EVAL / "phase0_tracking_corrected.csv"]
VERDICTS = ("right object", "wrong object", "lost")


def muse_records() -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {"chat": [], "responses": [], "sam": []}
    for p in (config.CACHE_DIR / "api").glob("*/*.json"):
        rec = json.loads(p.read_text(encoding="utf-8"))
        if rec["kind"] in out:
            out[rec["kind"]].append(rec)
    return out


def sam_runs() -> list[dict]:
    videos = link_videos()
    cache, runs = DiskCache(), []
    for path in TRACKING:
        if not path.exists():
            continue
        with open(path, encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                video = normalize(videos[row["video_id"]])
                payload = {
                    "model": config.SAM_MODEL,
                    "video_sha256": file_sha256(video),
                    "phrase": row["phrase"],
                    "metadata": {"include_confidence": "true"},
                }
                rec = cache.get(request_key({"kind": "sam", **payload}))
                if rec is None:
                    continue
                frames = int(probe(video)["frames"])
                runs.append({**row, "source": path.name, "billed_frames": frames, "rec": rec})
    return runs


def phrase_pool() -> set[str]:
    pool: set[str] = set()
    for path in TRACKING:
        if path.exists():
            with open(path, encoding="utf-8", newline="") as fh:
                pool |= {row["phrase"] for row in csv.DictReader(fh)}
    for path in (EVAL / "specs").glob("*.json"):
        doc = json.loads(path.read_text(encoding="utf-8"))
        for e in doc["specs"]:
            if e["spec"]:
                pool |= spec_phrases(e["spec"])
        for rev in doc.get("revisions", []):
            pool |= set(re.findall(r"'([^']+)'", rev))
    # The rule parser's phrases are generated from the question text, not stored in a file
    dataset = pd.read_csv(DATASET)
    for q, prior in zip(dataset.question, dataset.ground_truth_prior, strict=True):
        spec, _ = rule_spec(q, prior)
        if spec is not None:
            pool |= spec_phrases(spec.model_dump())
    return pool


def spec_phrases(spec: dict) -> set[str]:
    """Every phrase a spec can send to SAM: main phrases and their alternatives."""
    out = {spec.get(k) for k in ("target_phrase", "second_phrase", "reference_phrase")}
    out |= set(spec.get("target_alt_phrases") or []) | set(spec.get("reference_alt_phrases") or [])
    return {p for p in out if p}


def all_sam_frames() -> tuple[int, int]:
    """(matched SAM records, billed frames) over every phase."""
    cache, matched, frames = DiskCache(), 0, 0
    pool = phrase_pool()
    for video in sorted(link_videos().values()):
        norm = normalize(video)
        sha, n = file_sha256(norm), None
        for phrase in pool:
            payload = {"model": config.SAM_MODEL, "video_sha256": sha, "phrase": phrase,
                       "metadata": {"include_confidence": "true"}}  # fmt: skip
            if cache.get(request_key({"kind": "sam", **payload})) is not None:
                n = n if n is not None else int(probe(norm)["frames"])
                matched, frames = matched + 1, frames + n
    return matched, frames


def main() -> None:
    recs = muse_records()
    chat = recs["chat"]
    inp = [r["usage"]["input_tokens"] for r in chat]
    out = [r["usage"]["output_tokens"] for r in chat]
    lat = [r["latency_ms"] / 1000 for r in chat]
    chat_cost = muse_cost_usd({"input_tokens": sum(inp), "output_tokens": sum(out)})
    print(f"muse chat (baseline): records={len(chat)} cost_usd={chat_cost:.4f}")
    print(
        f"  input tokens/question: mean={st.mean(inp):.0f} median={st.median(inp):.0f} "
        f"min={min(inp)} max={max(inp)}"
    )
    print(
        f"  output tokens/question: mean={st.mean(out):.0f} median={st.median(out):.0f} "
        f"min={min(out)} max={max(out)}"
    )
    print(f"  cost/question: mean={chat_cost / len(chat):.4f}")
    print(f"  latency s: median={st.median(lat):.1f} max={max(lat):.1f}")

    resp = recs["responses"]
    resp_usage = {k: sum(r["usage"][k] for r in resp) for k in ("input_tokens", "output_tokens")}
    resp_cost = muse_cost_usd(resp_usage)
    print(f"muse responses (smoke, phrases, specs): records={len(resp)} cost_usd={resp_cost:.4f}")
    per_call = sorted(muse_cost_usd(r["usage"]) for r in resp)
    if per_call:  # basis of config.MUSE_CALL_ESTIMATE_USD for the live cost estimate
        print(f"  cost/call: mean={st.mean(per_call):.4f} max={per_call[-1]:.4f}")

    runs = sam_runs()
    matched = {r["rec"]["key"] for r in runs}
    unmatched = [r for r in recs["sam"] if r["key"] not in matched]
    frames = sum(r["billed_frames"] for r in {r["rec"]["key"]: r for r in runs}.values())
    sam_cost = sam_cost_usd(frames)
    print(f"sam: records={len(recs['sam'])} matched={len(matched)} unmatched={len(unmatched)}")
    print(f"  billed frames={frames} cost_usd={sam_cost:.4f}")
    per90 = [r["rec"]["latency_ms"] / 1000 * 90 / r["billed_frames"] for r in runs]
    sec = [r["rec"]["latency_ms"] / 1000 for r in runs]
    print(
        f"  latency s per request: median={st.median(sec):.1f} min={min(sec):.1f} "
        f"max={max(sec):.1f}; scaled to 90 frames: median={st.median(per90):.1f}"
    )
    near = [r for r in runs if 60 <= r["billed_frames"] <= 120]
    if near:
        s = [r["rec"]["latency_ms"] / 1000 for r in near]
        print(f"  clips with 60-120 frames: n={len(near)} latency s median={st.median(s):.1f}")

    total = chat_cost + resp_cost + sam_cost
    print(f"phase 0 spend from cache: cost_usd={total:.4f}")
    n_all, frames_all = all_sam_frames()
    sam_all = sam_cost_usd(frames_all)
    print(f"sam, all phases: records={len(recs['sam'])} matched={n_all} "
          f"billed frames={frames_all} cost_usd={sam_all:.4f}")  # fmt: skip
    print(f"total spend from cache, all phases: cost_usd={chat_cost + resp_cost + sam_all:.4f}")

    for path in TRACKING:
        if not path.exists():
            continue
        with open(path, encoding="utf-8", newline="") as fh:
            v = [row["my_verdict"].strip().lower() for row in csv.DictReader(fh)]
        counts = {k: v.count(k) for k in VERDICTS}
        blank = v.count("")
        other = len(v) - blank - sum(counts.values())
        print(f"verdicts {path.name}: {counts} blank={blank} other={other} of {len(v)}")


if __name__ == "__main__":
    main()
