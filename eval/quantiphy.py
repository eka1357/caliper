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

Frozen runs (DECISIONS 2026-11-02 "Freeze"; refuse to start if a frozen file changed):
  python eval/quantiphy.py --split holdout --specs-only --max-spend 2.50   # Muse spec calls
  python eval/quantiphy.py --split full --variant caliper --max-spend 5.00 # run JSONs only
  python eval/holdout_finalize.py                                         # score, results ($0)
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
from datetime import date

import pandas as pd
from ablation import rule_spec
from baseline import DATASET, EVAL, QP, link_videos, score, write_results
from baseline_analysis import load, update_results
from caliper import config
from caliper.depth import parse_depth
from caliper.meta_client import DiskCache, file_sha256, muse_cost_usd, request_key
from caliper.models import MeasurementSpec, Result
from caliper.pipeline import VideoContext, abstained, measure
from caliper.segment import sam_cost_usd
from caliper.spec import SpecError, write_spec
from field import SpendMeter

log = logging.getLogger("quantiphy")
HAND_SPECS = EVAL / "specs" / "phase1_dev_2d.json"
MUSE_SPECS = {"2D": EVAL / "specs" / "phase2_muse_dev_2d.json",
              "3D": EVAL / "specs" / "phase3_muse_dev_3d.json"}  # fmt: skip
SPEC_CACHE = config.CACHE_DIR / "specs"
VARIANTS = ("caliper", "caliper_no_audit", "caliper_rule_parser", "caliper_hand_spec")
MUSE_SPEC_VARIANTS = ("caliper", "caliper_no_audit")  # same cached Muse specs
SAM_CEILING_USD = 1.50  # Phase 2 plan: SAM for new phrases, both variants
MUSE_CEILING_USD = 6.0  # human, Phase 2: stop if the spec writer run is projected above this
# Phase 4 freeze (DECISIONS 2026-11-02 "Freeze"): --split runs refuse to start if any file that
# shapes a QuantiPhy answer differs from this commit (EVAL_PROTOCOL section 6).
FREEZE_COMMIT = "a5733dde6cfb0f806ded5d48781366cacb0d574d"
FROZEN_FILES = [f"backend/caliper/{m}.py" for m in (
    "config", "engine", "checks", "audit", "spec", "segment", "pipeline", "depth", "normalize",
    "models", "priors", "overlay", "backends", "meta_client", "study")]  # fmt: skip
# Per-question worst case for --max-spend: largest cached Responses call ($0.0309, cost_summary)
# +50%, the same bound eval/field.py uses; SAM bills every frame of each requested phrase.
MUSE_CALL_MAX_USD = 0.0309 * 1.5
SOURCES = {  # what the variant is; the split scope is added by source_for()
    "caliper": "Muse Spark spec writer, checks, visual audit",
    "caliper_no_audit": "Muse Spark spec writer, checks, no audit",
    "caliper_rule_parser": "A1 rule parser, eval/ablation.py",
    "caliper_hand_spec": "hand-written specs eval/specs/phase1_dev_2d.json",
}
SCOPES = {"dev_2d": "dev 2D only", "dev_3d": "dev 3D only", "dev": "dev, all four categories",
          "holdout": "holdout, all four categories, frozen at " + FREEZE_COMMIT[:7],
          "full": "dev + holdout, 158 questions, frozen at " + FREEZE_COMMIT[:7]}  # fmt: skip


def source_for(variant: str, split: str) -> str:
    """Source note for a results.csv row: the script, the split it covers, and the variant."""
    return f"eval/quantiphy.py ({SCOPES.get(split, split)}; {SOURCES[variant]})"


COMPARE = [
    "target_phrase", "target_instance", "second_phrase", "second_instance", "reference_phrase",
    "reference_instance", "reference_kind", "reference_statistic", "reference_axis",
    "reference_value_si", "quantity", "statistic", "axis", "timestamp_s", "time_anchor",
    "time_range_s", "output_unit",
]  # fmt: skip


def hand_entries() -> list[dict]:
    return json.loads(HAND_SPECS.read_text(encoding="utf-8"))["specs"]


def question_entries(dims: str, dataset: pd.DataFrame) -> list[dict]:
    """Dev questions: 2D from the hand-spec file (the Phase 1 set), 3D from the dataset."""
    out = hand_entries() if dims in ("2D", "all") else []
    if dims in ("3D", "all"):
        split = pd.read_csv(EVAL / "split.csv").set_index("video_id")["split"]
        rows = dataset[(dataset.video_id.map(split) == "dev") & (dataset.video_type.str[1] == "3")]
        out += [{"row_id": int(r), "video_id": v, "abstain_reason": None, "spec": None, "dim": "3D"}
                for r, v in zip(rows["Unnamed: 0"], rows.video_id, strict=True)]  # fmt: skip
    return out


def is_3d(q: pd.Series) -> bool:
    return str(q.video_type)[1] == "3"


def runs_dir(variant: str):
    return config.CACHE_DIR / "runs" / variant


def muse_spec_cached(row: int) -> dict | None:
    p = SPEC_CACHE / f"{row}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def get_spec(variant: str, entry: dict, q: pd.Series, ctx: VideoContext) -> tuple:
    """(spec or None, abstain reason, muse call info) for one question. Muse calls are cached."""
    if variant == "caliper_hand_spec":
        if entry.get("dim") == "3D":
            return None, "no hand-written spec (3D)", None
        if entry["abstain_reason"]:
            return None, entry["abstain_reason"], None
        return MeasurementSpec(**entry["spec"]), "", None
    if variant == "caliper_rule_parser":
        spec, why = rule_spec(q.question, q.ground_truth_prior,
                              parse_depth(q.depth_info) if is_3d(q) else None)  # fmt: skip
        return spec, why, None
    SPEC_CACHE.mkdir(parents=True, exist_ok=True)
    out = SPEC_CACHE / f"{entry['row_id']}.json"
    try:
        depth = parse_depth(q.depth_info) if is_3d(q) else None
        spec, info = write_spec(ctx.path, q.question, q.ground_truth_prior, depth)
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
    for dim in ("2D", "3D"):
        part = [e for e in entries if e.get("dim", "2D") == dim]
        if part:
            _write_muse_specs(part, dim)


def _write_muse_specs(entries: list[dict], dim: str) -> None:
    out = []
    for e in entries:
        rec = muse_spec_cached(e["row_id"]) or {}
        out.append({"row_id": e["row_id"], "video_id": e["video_id"],
                    "error": rec.get("error"), "spec": rec.get("spec")})  # fmt: skip
    doc = {
        "about": f"Specs written by Muse Spark 1.3 (caliper/spec.py) for the QuantiPhy dev {dim} "
        "questions. Keyed by dataset row id; no question text or answers stored.",
        "specs": out,
    }
    MUSE_SPECS[dim].write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {len(out)} specs to {MUSE_SPECS[dim]}")


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
    if variant in MUSE_SPEC_VARIANTS:
        rec = muse_spec_cached(entry["row_id"])
        return MeasurementSpec(**rec["spec"]) if rec and rec.get("spec") else None
    if variant == "caliper_rule_parser":
        return rule_spec(q.question, q.ground_truth_prior,
                         parse_depth(q.depth_info) if is_3d(q) else None)[0]  # fmt: skip
    return MeasurementSpec(**entry["spec"]) if entry["spec"] else None


def estimate(variant: str, entries, dataset, ctxs) -> float:
    need: dict[tuple[str, str], bool] = {}
    missing_specs = 0
    for e in entries:
        spec = offline_spec(variant, e, dataset.loc[e["row_id"]])
        if variant in MUSE_SPEC_VARIANTS and muse_spec_cached(e["row_id"]) is None:
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


def check_report(variant: str, entries: list[dict], dataset: pd.DataFrame) -> None:
    """Per check: bad answers (off by > 2x before checks) it catches, good answers it kills."""
    rd = runs_dir(variant)
    rows = []
    for e in entries:
        p = rd / f"{e['row_id']}.json"
        run_ = json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
        if not run_ or run_["artifacts"].get("unchecked_value") is None:
            continue
        gt = float(dataset.loc[e["row_id"], "ground_truth_posterior"])
        ratio = abs(run_["artifacts"]["unchecked_value"]) / gt
        failed = {c["name"] for c in run_["checks"] if not c["passed"]}
        rows.append((e["row_id"], ratio, failed, abs(ratio - 1) < 0.1))
    bad = [r for r in rows if r[1] > 2 or r[1] < 0.5]
    good = [r for r in rows if not (r[1] > 2 or r[1] < 0.5)]
    print(f"{variant}: {len(rows)} answered before checks: {len(bad)} off by > 2x, "
          f"{len(good)} not; {sum(r[3] for r in rows)} within 10%")  # fmt: skip
    names = sorted({n for r in rows for n in r[2]})
    for n in names:
        caught = [r[0] for r in bad if n in r[2]]
        killed = [r[0] for r in good if n in r[2]]
        killed10 = [r[0] for r in good if n in r[2] and r[3]]
        print(f"  {n:20s} catches {len(caught)}/{len(bad)} {caught}  "
              f"kills {len(killed)}/{len(good)} "
              f"{killed} (within 10%: {killed10})")  # fmt: skip
    kept = [r for r in rows if not r[2]]
    off = sum(1 for r in kept if r[1] > 2 or r[1] < 0.5)
    w10 = sum(1 for r in kept if r[3])
    print(f"  after all checks: answered {len(kept)}/{len(entries)}, "
          f"off by > 2x {off}/{len(kept)}, "
          f"within 10% {w10}/{len(kept)}")  # fmt: skip


def run(variant: str, entries: list[dict], dataset: pd.DataFrame, ctxs, dims: str) -> None:
    rd = runs_dir(variant)
    rd.mkdir(parents=True, exist_ok=True)
    preds, muse_cost, sam_requests = {}, 0.0, set()
    for e in entries:
        q = dataset.loc[e["row_id"]]
        ctx = ctxs[e["video_id"]]
        run_id = f"{variant}-{e['row_id']}"
        spec, why, _ = get_spec(variant, e, q, ctx)
        res: Result = (
            measure(
                ctx,
                q.question,
                q.ground_truth_prior,
                spec=spec,
                run_id=run_id,
                audit=variant == "caliper",
            )
            if spec is not None
            else abstained(why, run_id, method="spec")
        )
        if variant in MUSE_SPEC_VARIANTS:
            rec = muse_spec_cached(e["row_id"]) or {}
            res.cost_usd += rec.get("cost_usd", 0.0)
            muse_cost += rec.get("cost_usd", 0.0)
        muse_cost += (res.artifacts.get("audit_call") or {}).get("cost_usd") or 0.0  # call 2
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
    split = "dev" if dims == "all" else f"dev_{dims.lower()}"
    m = score(rows, split, variant)
    write_results([{
        "variant": variant, "split": split,
        "mra_average": m.get("mra_average") if pd.notna(m.get("mra_average")) else "",
        **{k: m.get(k) if pd.notna(m.get(k)) else "" for k in
           ("mra_S2", "mra_D2", "mra_S3", "mra_D3")},
        "abstain_rate": m.get("invalid_percentage", 0) / 100, "n": len(rows),
        "cost_usd": round(cost, 4), "run_date": date.today().isoformat(),
        "source": source_for(variant, split),
    }])  # fmt: skip
    update_results()
    print(f"{variant}: abstained {sum(v is None for v in preds.values())}/{len(preds)}; "
          f"S2={m.get('mra_S2')} D2={m.get('mra_D2')} S3={m.get('mra_S3')} D3={m.get('mra_D3')} "
          f"run cost ${cost:.4f}")  # fmt: skip


def split_entries(split: str, dataset: pd.DataFrame) -> list[dict]:
    """Every question of a split (dev, holdout or full), all four categories, dataset order."""
    s = pd.read_csv(EVAL / "split.csv").set_index("video_id")["split"]
    rows = dataset if split == "full" else dataset[dataset.video_id.map(s) == split]
    return [{"row_id": int(r), "video_id": v, "abstain_reason": None, "spec": None,
             "dim": f"{t[1]}D"} for r, v, t in
            zip(rows["Unnamed: 0"], rows.video_id, rows.video_type, strict=True)]  # fmt: skip


def check_frozen() -> None:
    """Refuse to run if any answer-shaping file differs from the freeze commit (worktree incl.)."""
    proc = subprocess.run(["git", "diff", "--quiet", FREEZE_COMMIT, "--", *FROZEN_FILES],
                          cwd=EVAL.parent, check=False)  # fmt: skip
    if proc.returncode != 0:
        sys.exit(f"STOP: frozen files differ from {FREEZE_COMMIT[:7]} "
                 f"(git diff {FREEZE_COMMIT[:7]} -- backend/caliper): not frozen")  # fmt: skip
    print(f"frozen files match {FREEZE_COMMIT[:7]}")


def specs_split(entries: list[dict], dataset: pd.DataFrame, max_spend: float) -> None:
    """Muse spec call 1 for every question in the split, metered; stops before passing the cap."""
    ctxs = contexts(entries, dataset)
    meter, stopped = SpendMeter(), None
    for e in entries:
        if muse_spec_cached(e["row_id"]) is None and meter.total + MUSE_CALL_MAX_USD > max_spend:
            stopped = f"stopped before row {e['row_id']}: spent ${meter.total:.4f}"
            break
        spec, why, _ = get_spec("caliper", e, dataset.loc[e["row_id"]], ctxs[e["video_id"]])
        meter.settle(ctxs[e["video_id"]].frames)
        print(f"{e['row_id']} {e['video_id']}: {'ok' if spec else 'SPEC ERROR ' + why} "
              f"total=${meter.total:.4f}")  # fmt: skip
    print(json.dumps({"step": "specs", "questions": len(entries),
                      "real_spend_usd": round(meter.total, 4), "stopped": stopped}))  # fmt: skip
    if stopped:
        sys.exit(f"STOP: {stopped} (cap ${max_spend:.2f})")


def run_split(variant: str, entries: list[dict], dataset: pd.DataFrame, ctxs,
              max_spend: float) -> None:  # fmt: skip
    """Run JSONs for every question of the split, metered. Scoring is eval/holdout_finalize.py."""
    rd = runs_dir(variant)
    rd.mkdir(parents=True, exist_ok=True)
    meter, stopped, done = SpendMeter(), None, []
    for e in entries:
        q, ctx = dataset.loc[e["row_id"]], ctxs[e["video_id"]]
        spec, why, _ = get_spec(variant, e, q, ctx)  # cached: specs_split ran first
        n_sam = sum(not sam_cached(ctx, p) for p in sam_phrases(spec)) if spec else 0
        bound = n_sam * ctx.frames * config.SAM_USD_PER_FRAME
        bound += MUSE_CALL_MAX_USD if variant == "caliper" and spec else 0.0
        if meter.total + bound > max_spend:
            stopped = (f"stopped before row {e['row_id']}: spent ${meter.total:.4f}, "
                       f"worst case for it ${bound:.4f}")  # fmt: skip
            break
        run_id = f"{variant}-{e['row_id']}"
        res: Result = (
            measure(
                ctx,
                q.question,
                q.ground_truth_prior,
                spec=spec,
                run_id=run_id,
                audit=variant == "caliper",
            )  # fmt: skip
            if spec is not None
            else abstained(why, run_id, method="spec")
        )
        meter.settle(ctx.frames)
        (rd / f"{e['row_id']}.json").write_text(res.model_dump_json(indent=1), encoding="utf-8")
        done.append(res.status)
        print(f"{e['row_id']} {e['video_id']}: {res.status} {res.value} {res.unit} "
              f"{res.abstain_reason or ''} total=${meter.total:.4f}")  # fmt: skip
    print(json.dumps({"step": variant, "questions": len(entries), "written": len(done),
                      "measured": done.count("measured"), "real_spend_usd": round(meter.total, 4),
                      "stopped": stopped}))  # fmt: skip
    if stopped:
        sys.exit(f"STOP: {stopped} (cap ${max_spend:.2f})")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=("dev", "holdout", "full"), default=None,
                    help="frozen run over a whole split; needs --max-spend")  # fmt: skip
    ap.add_argument("--max-spend", type=float, default=None, help="USD cap for this command")
    ap.add_argument("--variant", choices=VARIANTS, default="caliper")
    ap.add_argument("--specs-only", action="store_true")
    ap.add_argument("--dims", choices=("2D", "3D", "all"), default="2D", help="dev questions")
    ap.add_argument("--rows", type=int, nargs="*", default=[], help="row ids (pilot)")
    ap.add_argument("--estimate", action="store_true")
    ap.add_argument("--compare-specs", action="store_true")
    ap.add_argument("--worst", type=int, default=0)
    ap.add_argument("--check-report", action="store_true", help="per-check catches (no API)")
    ap.add_argument("--audit-pilot", type=int, default=0, help="audit one row, print, no results")
    ap.add_argument(
        "--sam-ceiling",
        type=float,
        default=SAM_CEILING_USD,
        help="one-run override, only with the human's approval (DECISIONS.md)",
    )
    args = ap.parse_args()
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    dataset = pd.read_csv(DATASET).set_index("Unnamed: 0", drop=False)
    if args.split:
        if args.max_spend is None:
            sys.exit("--split needs --max-spend")
        if args.variant not in MUSE_SPEC_VARIANTS:
            sys.exit("--split runs caliper or caliper_no_audit only")
        check_frozen()
        entries = split_entries(args.split, dataset)
        if args.specs_only:
            specs_split(entries, dataset, args.max_spend)
            return
        ctxs = contexts(entries, dataset)
        estimate(args.variant, entries, dataset, ctxs)  # upper bound, printed for the record
        if args.estimate:
            return
        if any(muse_spec_cached(e["row_id"]) is None for e in entries):
            sys.exit("STOP: run --split ... --specs-only first")
        run_split(args.variant, entries, dataset, ctxs, args.max_spend)
        return
    entries = question_entries(args.dims, dataset)
    if args.worst:
        worst(args.variant, args.worst)
        return
    if args.audit_pilot:
        e = next(x for x in entries if x["row_id"] == args.audit_pilot)
        q = dataset.loc[e["row_id"]]
        ctx = contexts([e], dataset)[e["video_id"]]
        spec, why, _ = get_spec("caliper", e, q, ctx)
        res = measure(ctx, q.question, q.ground_truth_prior, spec=spec, audit=True)
        print(res.status, res.abstain_reason, res.audit)
        print("audit call:", res.artifacts.get("audit_call"))
        return
    if args.check_report:
        check_report(args.variant, entries, dataset)
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
    if args.variant in MUSE_SPEC_VARIANTS and any(
        muse_spec_cached(e["row_id"]) is None for e in entries
    ):
        sys.exit("STOP: run --specs-only first (Muse calls need their own approval)")
    if est > args.sam_ceiling:
        sys.exit(f"STOP: SAM estimate ${est:.2f} is above ${args.sam_ceiling:.2f}")
    run(args.variant, entries, dataset, ctxs, args.dims)


if __name__ == "__main__":
    main()
