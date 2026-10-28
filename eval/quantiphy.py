"""$ Caliper on QuantiPhy dev 2D (the 42 questions of eval/specs/phase1_dev_2d.json).

Variants (all through caliper.pipeline.measure, same SAM, engine and abstention rules):
  caliper              spec from Muse Spark call 1 (spends credits on cache misses)
  caliper_rule_parser  spec from the regex parser in eval/ablation.py (A1; no model)
  caliper_hand_spec    hand-written specs, eval/specs/phase1_dev_2d.json (Phase 1 reference)

Abstentions leave parsed_value blank (a miss, EVAL_PROTOCOL section 4.4). Each run writes
eval/quantiphy/model_outputs/<variant>.csv, scores it with the official evaluator, replaces the
<variant>/dev row in eval/results.csv, refreshes eval/paired_results.csv, and saves one run JSON
per question under data/cache/runs/<variant>/.

  python eval/quantiphy.py --specs-only --rows 427   # Muse pilot (one question) + projection
  python eval/quantiphy.py --specs-only              # all spec calls
  python eval/quantiphy.py --variant caliper --estimate               # SAM cost, no API calls
  python eval/quantiphy.py --variant caliper                          # SAM + engine + score
  python eval/quantiphy.py --compare-specs                            # agreement with hand specs
  python eval/quantiphy.py --variant caliper --worst 5                # no API calls
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date

import pandas as pd
from ablation import rule_spec
from baseline import DATASET, EVAL, QP, link_videos, score, write_results
from baseline_analysis import load, update_results
from caliper import config
from caliper.meta_client import DiskCache, file_sha256, muse_cost_usd, request_key
from caliper.models import MeasurementSpec, Result
from caliper.pipeline import VideoContext, abstained, measure
from caliper.segment import sam_cost_usd
from caliper.spec import SpecError, write_spec

log = logging.getLogger("quantiphy")
HAND_SPECS = EVAL / "specs" / "phase1_dev_2d.json"
MUSE_SPECS = EVAL / "specs" / "phase2_muse_dev_2d.json"
SPEC_CACHE = config.CACHE_DIR / "specs"
VARIANTS = ("caliper", "caliper_rule_parser", "caliper_hand_spec")
SAM_CEILING_USD = 1.50  # Phase 2 plan: SAM for new phrases, both variants
MUSE_CEILING_USD = 6.0  # human, Phase 2: stop if the spec writer run is projected above this
SOURCES = {
    "caliper": "eval/quantiphy.py (dev 2D only; Muse Spark spec writer, caliper/spec.py)",
    "caliper_rule_parser": "eval/quantiphy.py (dev 2D only; A1 rule parser, eval/ablation.py)",
    "caliper_hand_spec": "eval/quantiphy.py (dev 2D only; hand-written specs "
    "eval/specs/phase1_dev_2d.json)",
}
COMPARE = [
    "target_phrase", "target_instance", "second_phrase", "second_instance", "reference_phrase",
    "reference_instance", "reference_kind", "reference_statistic", "reference_axis",
    "reference_value_si", "quantity", "statistic", "axis", "timestamp_s", "time_anchor",
    "time_range_s", "output_unit",
]  # fmt: skip


def hand_entries() -> list[dict]:
    return json.loads(HAND_SPECS.read_text(encoding="utf-8"))["specs"]


def runs_dir(variant: str):
    return config.CACHE_DIR / "runs" / variant


def muse_spec_cached(row: int) -> dict | None:
    p = SPEC_CACHE / f"{row}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def get_spec(variant: str, entry: dict, q: pd.Series, ctx: VideoContext) -> tuple:
    """(spec or None, abstain reason, muse call info) for one question. Muse calls are cached."""
    if variant == "caliper_hand_spec":
        if entry["abstain_reason"]:
            return None, entry["abstain_reason"], None
        return MeasurementSpec(**entry["spec"]), "", None
    if variant == "caliper_rule_parser":
        spec, why = rule_spec(q.question, q.ground_truth_prior)
        return spec, why, None
    SPEC_CACHE.mkdir(parents=True, exist_ok=True)
    out = SPEC_CACHE / f"{entry['row_id']}.json"
    try:
        spec, info = write_spec(ctx.path, q.question, q.ground_truth_prior)
    except SpecError as exc:
        rec = {"row_id": entry["row_id"], "video_id": entry["video_id"], "error": str(exc)}
        out.write_text(json.dumps(rec, indent=1), encoding="utf-8")
        return None, str(exc), None
    rec = {"row_id": entry["row_id"], "video_id": entry["video_id"], "spec": spec.model_dump(),
           "usage": info["usage"], "cost_usd": info["cost_usd"],
           "latency_ms": info["latency_ms"]}  # fmt: skip
    out.write_text(json.dumps(rec, indent=1), encoding="utf-8")
    return spec, "", info


def contexts(entries: list[dict], dataset: pd.DataFrame) -> dict[str, VideoContext]:
    videos = link_videos()
    fps = dataset.groupby("video_id")["fps"].first()
    return {v: VideoContext(videos[v], v, float(fps[v]))
            for v in sorted({e["video_id"] for e in entries})}  # fmt: skip


def specs_only(entries: list[dict], dataset: pd.DataFrame, rows: list[int]) -> None:
    """Muse spec calls only (all questions, or `rows`); prints spend and the projected cost."""
    ctxs = contexts(entries, dataset)
    todo = [e for e in entries if e["row_id"] in rows] if rows else entries
    spent, used, frames_done, calls = 0.0, {"input_tokens": 0, "output_tokens": 0}, 0, 0
    for e in todo:
        q = dataset.loc[e["row_id"]]
        ctx = ctxs[e["video_id"]]
        spec, why, info = get_spec("caliper", e, q, ctx)
        if info is not None:
            spent += info["cost_usd"]
            for k in used:
                used[k] += info["usage"][k]
            frames_done += ctx.frames
            calls += 1
        print(f"{e['row_id']} {e['video_id']} frames={ctx.frames}: "
              f"{'ok' if spec else 'ERROR ' + why} usage={info and info['usage']} "
              f"cost={info and round(info['cost_usd'], 4)}")  # fmt: skip
        if spent > MUSE_CEILING_USD:
            sys.exit(f"STOP: spec writer spend ${spent:.2f} passed ${MUSE_CEILING_USD:.0f}")
    total_frames = sum(ctxs[e["video_id"]].frames for e in entries)
    if calls:
        in_per_frame = used["input_tokens"] / frames_done
        out_per_q = used["output_tokens"] / calls
        proj = {"input_tokens": round(in_per_frame * total_frames),
                "output_tokens": round(out_per_q * len(entries))}  # fmt: skip
        cost = muse_cost_usd(proj)
        print(f"usage={used} cost_usd={spent:.4f} over {calls} calls, {frames_done} frames")
        print(f"input tokens per video frame (incl. prompt) = {in_per_frame:.1f}")
        print(f"projection for {len(entries)} questions ({total_frames} frames): {proj} "
              f"cost_usd={cost:.2f}")  # fmt: skip
        if cost > MUSE_CEILING_USD:
            print(f"STOP: projection ${cost:.2f} is above the ${MUSE_CEILING_USD:.0f} ceiling")
    if not rows:
        write_muse_spec_file(entries)


def write_muse_spec_file(entries: list[dict]) -> None:
    out = []
    for e in entries:
        rec = muse_spec_cached(e["row_id"]) or {}
        out.append({"row_id": e["row_id"], "video_id": e["video_id"],
                    "error": rec.get("error"), "spec": rec.get("spec")})  # fmt: skip
    doc = {
        "about": "Specs written by Muse Spark 1.3 (caliper/spec.py) for the QuantiPhy dev 2D "
        "questions. Keyed by dataset row id; no question text or answers stored.",
        "specs": out,
    }
    MUSE_SPECS.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {len(out)} specs to {MUSE_SPECS}")


def sam_phrases(spec: MeasurementSpec) -> list[str]:
    """Upper bound: every phrase that might be sent to SAM (main and alternatives)."""
    out = [spec.target_phrase, *spec.target_alt_phrases]
    if spec.second_phrase:
        out.append(spec.second_phrase)
    if spec.reference_phrase:
        out += [spec.reference_phrase, *spec.reference_alt_phrases]
    return out


def sam_cached(ctx: VideoContext, phrase: str) -> bool:
    payload = {"model": config.SAM_MODEL, "video_sha256": file_sha256(ctx.path),
               "phrase": phrase, "metadata": {"include_confidence": "true"}}  # fmt: skip
    return DiskCache().get(request_key({"kind": "sam", **payload})) is not None


def offline_spec(variant: str, entry: dict, q: pd.Series) -> MeasurementSpec | None:
    if variant == "caliper":
        rec = muse_spec_cached(entry["row_id"])
        return MeasurementSpec(**rec["spec"]) if rec and rec.get("spec") else None
    if variant == "caliper_rule_parser":
        return rule_spec(q.question, q.ground_truth_prior)[0]
    return MeasurementSpec(**entry["spec"]) if entry["spec"] else None


def estimate(variant: str, entries, dataset, ctxs) -> float:
    need: dict[tuple[str, str], bool] = {}
    missing_specs = 0
    for e in entries:
        spec = offline_spec(variant, e, dataset.loc[e["row_id"]])
        if variant == "caliper" and muse_spec_cached(e["row_id"]) is None:
            missing_specs += 1
        if spec is None:
            continue
        for p in sam_phrases(spec):
            key = (e["video_id"], p)
            if key not in need:
                need[key] = sam_cached(ctxs[e["video_id"]], p)
    misses = [(v, p) for (v, p), hit in need.items() if not hit]
    est = sam_cost_usd(sum(ctxs[v].frames for v, _ in misses))
    print(f"{variant}: SAM phrases (main + alternatives) {len(need)}, {len(misses)} not cached")
    for v, p in misses:
        print(f"  miss: {v} '{p}' frames={ctxs[v].frames}")
    print(f"estimate (upper bound; alternatives only run if the main phrase finds nothing): "
          f"uncached SAM cost_usd={est:.4f}")  # fmt: skip
    if missing_specs:
        print(f"  {missing_specs} Muse specs not written yet (run --specs-only first)")
    return est


def compare_specs(entries: list[dict], dataset: pd.DataFrame) -> None:
    def same(field, a, b) -> bool:
        if a is None or b is None:
            return a is None and b is None
        if field == "reference_value_si":
            return abs(a - b) <= 0.01 * abs(b)
        if field == "timestamp_s":
            return abs(a - b) <= 0.05
        if field == "time_range_s":
            return all(abs(x - y) <= 0.05 for x, y in zip(a, b, strict=True))
        if isinstance(a, str):
            return a.strip().lower() == b.strip().lower()
        return a == b

    for variant in ("caliper", "caliper_rule_parser"):
        agree = dict.fromkeys(COMPARE, 0)
        n = produced = 0
        for e in entries:
            if not e["spec"]:
                continue
            n += 1
            spec = offline_spec(variant, e, dataset.loc[e["row_id"]])
            if spec is None:
                continue
            produced += 1
            hand = e["spec"]
            for f in COMPARE:
                agree[f] += same(f, getattr(spec, f), hand.get(f))
        print(f"== {variant}: spec produced for {produced}/{n} questions with a hand spec "
              f"(agreement counted over all {n})")  # fmt: skip
        for f in COMPARE:
            print(f"  {f:22s} {agree[f]:2d}/{n} = {agree[f] / n:.2f}")


def worst(variant: str, n: int) -> None:
    df = load(variant)
    rd = runs_dir(variant)
    runs = {r: json.loads((rd / f"{r}.json").read_text(encoding="utf-8")) for r in df["Unnamed: 0"]}
    cols = ["Unnamed: 0", "video_id", "category", "pred", "ground_truth_posterior", "mra"]
    for _, r in df.sort_values(["mra", "Unnamed: 0"]).head(n).iterrows():
        run_ = runs[r["Unnamed: 0"]]
        sp = run_["spec"]
        print(r[cols].to_dict(), run_["status"], run_["abstain_reason"] or "")
        print(f"   spec: target={sp['target_phrase']!r} ({sp['target_instance']}) "
              f"ref={sp['reference_phrase']!r} {sp['statistic']} axis={sp['axis']} "
              f"t={sp['timestamp_s']}")  # fmt: skip
        print(f"   used={run_['artifacts'].get('phrases_used')} "
              f"instances={run_['artifacts'].get('instances')}")  # fmt: skip


def run(variant: str, entries: list[dict], dataset: pd.DataFrame, ctxs) -> None:
    rd = runs_dir(variant)
    rd.mkdir(parents=True, exist_ok=True)
    preds, muse_cost, sam_requests = {}, 0.0, set()
    for e in entries:
        q = dataset.loc[e["row_id"]]
        ctx = ctxs[e["video_id"]]
        run_id = f"{variant}-{e['row_id']}"
        spec, why, _ = get_spec(variant, e, q, ctx)
        res: Result = (
            measure(ctx, q.question, q.ground_truth_prior, spec=spec, run_id=run_id)
            if spec is not None
            else abstained(why, run_id, method="spec")
        )
        if variant == "caliper":
            rec = muse_spec_cached(e["row_id"]) or {}
            res.cost_usd += rec.get("cost_usd", 0.0)
            muse_cost += rec.get("cost_usd", 0.0)
        sam_requests |= {(e["video_id"], p) for p in res.artifacts.get("phrases_tried", [])}
        (rd / f"{e['row_id']}.json").write_text(res.model_dump_json(indent=1), encoding="utf-8")
        preds[e["row_id"]] = res.value
        print(f"{e['row_id']} {e['video_id']}: {res.status} {res.value} {res.unit} "
              f"{res.abstain_reason or ''}")  # fmt: skip

    # cost of the whole run from scratch: each spec call, and each (video, phrase) SAM request once
    cost = muse_cost + sam_cost_usd(sum(ctxs[v].frames for v, _ in sam_requests))
    rows = dataset.loc[[e["row_id"] for e in entries]].reset_index(drop=True)
    rows["parsed_value"] = [preds[r] for r in rows["Unnamed: 0"]]
    rows.to_csv(QP / "model_outputs" / f"{variant}.csv", index=False)
    m = score(rows, "dev", variant)
    write_results([{
        "variant": variant, "split": "dev",
        "mra_average": "",  # the scorer averages all 4 categories; these runs are 2D only
        "mra_S2": m.get("mra_S2"), "mra_D2": m.get("mra_D2"), "mra_S3": "", "mra_D3": "",
        "abstain_rate": m.get("invalid_percentage", 0) / 100, "n": len(rows),
        "cost_usd": round(cost, 4), "run_date": date.today().isoformat(),
        "source": SOURCES[variant],
    }])  # fmt: skip
    update_results()
    print(f"{variant}: abstained {sum(v is None for v in preds.values())}/{len(preds)}; "
          f"S2={m.get('mra_S2')} D2={m.get('mra_D2')} run cost ${cost:.4f}")  # fmt: skip


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", choices=VARIANTS, default="caliper")
    ap.add_argument("--specs-only", action="store_true")
    ap.add_argument("--rows", type=int, nargs="*", default=[], help="row ids (pilot)")
    ap.add_argument("--estimate", action="store_true")
    ap.add_argument("--compare-specs", action="store_true")
    ap.add_argument("--worst", type=int, default=0)
    args = ap.parse_args()
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    dataset = pd.read_csv(DATASET).set_index("Unnamed: 0", drop=False)
    entries = hand_entries()
    if args.worst:
        worst(args.variant, args.worst)
        return
    if args.compare_specs:
        compare_specs(entries, dataset)
        return
    if args.specs_only:
        specs_only(entries, dataset, args.rows)
        return
    ctxs = contexts(entries, dataset)
    est = estimate(args.variant, entries, dataset, ctxs)
    if args.estimate:
        return
    if args.variant == "caliper" and any(muse_spec_cached(e["row_id"]) is None for e in entries):
        sys.exit("STOP: run --specs-only first (Muse calls need their own approval)")
    if est > SAM_CEILING_USD:
        sys.exit(f"STOP: SAM estimate ${est:.2f} is above ${SAM_CEILING_USD:.2f}")
    run(args.variant, entries, dataset, ctxs)


if __name__ == "__main__":
    main()
