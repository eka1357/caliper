// Display names and colours for benchmark rows. Names only: every number comes from the CSVs.

export const VARIANT_LABEL: Record<string, string> = {
  muse_spark_alone: "Muse Spark alone",
  caliper: "Caliper",
  caliper_no_audit: "Caliper, audit off",
  caliper_rule_parser: "Caliper, rule parser",
  caliper_hand_spec: "Caliper, hand-written specs",
  caliper_open: "Caliper on Muse Spark Open",
};

export const VARIANT_NOTE: Record<string, string> = {
  muse_spark_alone: "The model answers from the video alone (QuantiPhy's official zero-shot prompt).",
  caliper: "Full pipeline: spec, SAM 3.1 tracks, engine, checks, visual audit.",
  caliper_no_audit: "Same pipeline with the visual audit switched off.",
  caliper_rule_parser: "Ablation A1: the Muse Spark spec replaced by a rule-based parser.",
  caliper_hand_spec: "Reference only: hand-written specs through the same SAM and engine.",
};

export const VARIANT_COLOR: Record<string, string> = {
  muse_spark_alone: "var(--muted-foreground)",
  caliper: "var(--primary)",
  caliper_no_audit: "var(--track)",
  caliper_rule_parser: "var(--success)",
  caliper_hand_spec: "var(--chart-4)",
};

export const SPLIT_LABEL: Record<string, string> = {
  holdout: "Holdout",
  dev: "Dev",
  full: "Full",
  dev_2d: "Dev, 2D",
  dev_3d: "Dev, 3D",
};

export const SPLIT_NOTE: Record<string, string> = {
  holdout: "Videos never used for tuning. The headline split.",
  dev: "Videos used to tune thresholds and prompts, so these numbers flatter Caliper.",
  full: "All 158 validation questions.",
  dev_2d: "Dev split, 2D categories (S2, D2) only.",
  dev_3d: "Dev split, 3D categories (S3, D3) only.",
};

export const CATEGORY_NOTE: Record<string, string> = {
  S2: "Static object, 2D",
  D2: "Moving object, 2D",
  S3: "Static object, 3D",
  D3: "Moving object, 3D",
};

export const variantLabel = (v: string) => VARIANT_LABEL[v] ?? v;
export const splitLabel = (s: string) => SPLIT_LABEL[s] ?? s;

/** MRA on the leaderboard's 0 to 100 scale. */
export const fmtMra = (v: number | null) => (v == null ? "n/a" : (v * 100).toFixed(1));
export const fmtPct = (v: number | null) => (v == null ? "n/a" : `${Math.round(v * 100)}%`);
