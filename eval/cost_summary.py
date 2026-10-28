"""Phase 0 measured facts from the disk cache (no API calls).

Muse Spark tokens and latency come from the cached chat records (the baseline) and responses
records (smoke test and tracking phrases). SAM requests are matched to their clips through
eval/phase0_tracking*.csv, so billed frames come from ffprobe on the normalized video.

  python eval/cost_summary.py
"""

from __future__ import annotations

import csv
import json
import statistics as st

from baseline import EVAL, link_videos
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
    print(f"muse responses (smoke + phrases): records={len(resp)} cost_usd={resp_cost:.4f}")

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
