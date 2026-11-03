# Evaluation protocol

Written before the build so the result cannot be bent after the fact. Every number below is a target, not a result.

## 1. Claims

| ID | Claim | Primary metric | Target | Disproved if |
| --- | --- | --- | --- | --- |
| H1 | Grounded measurement beats the same model guessing | QuantiPhy MRA on the holdout split | Caliper at least 10 points above `muse_spark_alone`, and above the human baseline of 55.6 | Caliper beats `muse_spark_alone` by under 5 points |
| H2 | Caliper is accurate on real phone video | Median relative error on the field set | At most 10% | Above 20% |
| H3 | Caliper's ranges are honest | Share of field clips whose 90% interval contains the truth | At least 80% | Under 60% |
| H4 | Caliper refuses when it should | Abstention on the no-reference clips | All of them abstain | Any of them returns a number |
| H5 | The street speed study is accurate per vehicle | Set A through the study code path: absolute error vs GPS speed | Median at most 3 km/h; 90% ranges contain the GPS value in at least 8 of 10 | Median above 6 km/h |
| A1 | The model earns its place in the spec | MRA of `caliper` minus `caliper_rule_parser` | Reported, whatever it is | n/a (an honest finding either way) |
| A2 | The audit earns its place | Wrong-object tracks caught (against your Phase 0 verdicts) and correct results wrongly vetoed; MRA with and without audit | Catches most wrong-object tracks while vetoing few correct ones; report both counts | n/a (report honestly) |

If a claim is disproved, the README and demo say so plainly. That is part of the submission, not a failure to hide.

## 2. Datasets

QuantiPhy validation ([dataset](https://huggingface.co/datasets/PaulineLi/QuantiPhy-validation), [code](https://github.com/Paulineli/QuantiPhy))
- 158 questions on 24 videos with ground truth; videos are 2 to 3 seconds with a static camera.
- Fields: `video_id`, `video_source`, `video_type`, `fps`, `inference_type`, `question`, `ground_truth_prior`, `depth_info`, `ground_truth_posterior` (the answer), plus an unnamed index column (the row ID the scorer matches on). File: `data/quantiphy-val/validation_dataset.csv`; videos in `validation_videos/`.
- Annotations CC BY 4.0; videos keep their original licenses (research and evaluation only; never shown in the demo).
- Split by video, not by question, so one video never lands in both halves: `dev` = videos where `int(hashlib.sha256(video_id.encode()).hexdigest(), 16) % 2 == 0`, `holdout` = the rest. With 24 videos expect roughly 12 per side; if the split is worse than 10 to 14, use a fixed seeded shuffle of video_ids instead and record it. Write the split to `eval/split.csv` on Phase 0 and never change it.
- Tune thresholds, windows and prompts on `dev` only. Report `dev`, `holdout` and `full`, and lead with `holdout`.

Field set (`data/field/`, protocol in docs/DATA_COLLECTION.md)
- 30 measurement clips with instrument truth (10 speed, 10 gravity, 10 size) plus 5 no-reference clips.
- Set S: one or two street clips for the speed study demo. No per-vehicle truth; shown as a demonstration, never as an accuracy claim.
- Out-of-sample by construction: never used for tuning. If a bug fix is needed, fix it, rerun everything, and log the change in docs/DECISIONS.md.

## 3. Variants (rows in eval/results.csv)

| Row | What it is |
| --- | --- |
| `muse_spark_alone` | Muse Spark 1.3 with QuantiPhy's official zero-shot prompt (option 3, "original"), parsed as the official script does |
| `caliper` | Full pipeline (spec + SAM + engine + checks + audit) |
| `caliper_no_audit` | Same, audit switched off |
| `caliper_rule_parser` | Muse Spark spec replaced by a rule-based parser; same SAM, engine, checks |
| `caliper_hand_spec` | Reference only (added 2026-10-29): hand-written specs (`eval/specs/phase1_dev_2d.json`, dev 2D) through the same SAM and engine; the Phase 1 `caliper` row, renamed |
| `caliper_open` | Stretch: spec and audit on Muse Spark Open (Baseten), everything else identical |
| `human_baseline` | 55.6, copied from the [QuantiPhy leaderboard](https://quantiphy.stanford.edu/) with the source noted |
| `gpt_5_1_validation` | 48.4 on the validation set, copied from the leaderboard with the source noted (our local scorer run reproduced 0.4824) |

Copied rows carry a `source` column.

## 4. Running the official scorer

1. Clone the repo into `eval/quantiphy/` and download the validation data into `data/quantiphy-val/`.
2. Baseline: adapt `model_run_example/run_API_results.py` so its OpenAI client uses `base_url="https://api.meta.ai/v1"`, `api_key=os.environ["MODEL_API_KEY"]`, `model="muse-spark-1.3"`. Keep the prompt text unchanged and select zero-shot option 3. Record the exact diff in `eval/baseline_patch.diff`.
3. Every variant writes a CSV into `eval/quantiphy/model_outputs/<variant>.csv`.
4. Abstentions: leave `parsed_value` empty. The scorer counts blank, non-numeric and zero values as invalid; treat invalid as a miss. Report the abstention rate next to MRA.
5. Run from `eval/quantiphy`: `python evaluator.py model_outputs mra_results --gt_file ../../data/quantiphy-val/validation_dataset.csv`, then read `mra_results/all_model_results.csv`.
6. `eval/report.py` copies the rows we need into `eval/results.csv` and builds `web/public/results.json` and the README table.
7. Prediction CSVs must start with the ground-truth row ID ("Unnamed: 0") as their first column. Build them by copying validation_dataset.csv and adding a parsed_value column, as in eval/quantiphy/model_outputs/gpt-5.1.csv. Check the scorer prints "Matched 158/158".

Columns in `eval/results.csv`: `variant, split, mra_average, mra_S2, mra_D2, mra_S3, mra_D3, abstain_rate, share_within_10pct, share_off_2x, n, cost_usd, run_date, source`. `share_within_10pct` is the share of all n questions with relative error below 10%; `share_off_2x` is the share with pred/truth above 2 or below 0.5. Both count an invalid answer as a miss; both are computed by `eval/baseline_analysis.py` from the prediction CSV.

### 4a. Answered-only reporting (pre-registered 2026-10-28, before the first Phase 1 tuning rerun)

- The official MRA (scorer output, an abstention counts as a miss) stays the headline benchmark number everywhere it is shown.
- Also reported, for every variant and split, as extra columns in `eval/results.csv`:
  - `coverage`: share of the n questions answered (a valid, nonzero number);
  - `mra_answered`: mean per-question MRA over the answered questions only (pooled over questions, not averaged over categories);
  - `share_within_10pct_answered` and `share_off_2x_answered`: the two error shares over the answered questions only.
- Like-for-like comparison: `eval/paired_results.csv` reports `muse_spark_alone` on exactly the questions each Caliper variant answered, with columns `variant, split, category, n_answered, mra_variant, mra_muse, within10_variant, within10_muse, off2x_variant, off2x_muse` (`category` = S2, D2, S3, D3 or `all`).
- All of these are computed by `eval/baseline_analysis.py` from the prediction CSVs.
- No variant may fill Caliper's abstentions with an LLM's answers. Abstentions stay abstentions.
- Added 2026-11-03, after the holdout run: the post-hoc analysis row `hybrid_posthoc` (Caliper where it answered, Muse Spark alone where it abstained) is not a variant and not a claim. It is reported only as a labelled post-hoc analysis (docs/DECISIONS.md 2026-11-03); the rule above is unchanged.

## 5. Field set metrics

- Relative error per clip: `abs(pred - truth) / truth`. Report median and 90th percentile.
- Coverage: share of clips where the truth lies inside the 90% interval.
- Abstained measurement clips count as abstentions, not as errors; report their count.
- Per-clip table in `eval/field_results.csv`: `clip_id, set, path, truth, pred, lo, hi, rel_error, covered, status, reason, audit_approve`. `path` is `measure` or `study` (set A runs through both).

## 6. Guardrails against fooling ourselves

- Freeze engine, study and audit parameters at the end of Phase 4 (Oct 31). After that, only bug fixes, each logged.
- No per-question special cases. A rule that names a specific video_id or clip_id is a bug.
- Every chart and table in the UI, README, demo video and X post is rendered from the files above.
- Rerun `make eval` from a clean cache once before submission to prove reproducibility (costs money: check the budget first).

## 7. What would change the plan

| Finding | Response |
| --- | --- |
| Phase 0: SAM tracks the wrong object on more than 10 of 20 clips | Stop. Try box prompts from a frame-0 detection; if still failing, rethink scope with the human |
| `muse_spark_alone` already at or above 55.6 | The gap is smaller than assumed; lead with field accuracy, the speed study and abstention honesty |
| QuantiPhy challenge results show tool pipelines far ahead | Compare honestly; our contribution becomes the verified field set, the audit, abstention, and the speed study |
| Ablation equals full Caliper | Say so; show where the model matters (free-form questions, known-object scale, the audit) |
| Audit vetoes many correct results | Tighten its prompt on dev only; if it still hurts, ship it as a warning instead of a veto and say so |
