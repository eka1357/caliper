// Mirrors backend/caliper/models.py, runs.py and overlay.py. Keep in sync with the pydantic models.

export type Quantity = "size" | "speed" | "acceleration";
export type Statistic = "instantaneous" | "average" | "extent" | "separation" | "orbit_diameter";
export type Axis = "path" | "horizontal" | "vertical" | "longest" | "shortest" | "disc";
export type TimeAnchor = "timestamp" | "first" | "last";
export type Instance = string;

export interface MeasurementSpec {
  target_phrase: string;
  target_alt_phrases: string[];
  target_instance: Instance;
  second_phrase: string | null;
  second_instance: Instance;
  reference_phrase: string | null;
  reference_alt_phrases: string[];
  reference_instance: Instance;
  reference_kind: "size" | "speed" | "acceleration" | "given_prior" | "known_object";
  reference_statistic: "extent" | "average_speed" | "acceleration";
  reference_axis: Axis;
  reference_value_si: number | null;
  reference_source: string;
  quantity: Quantity;
  statistic: Statistic;
  axis: Axis;
  timestamp_s: number | null;
  time_anchor: TimeAnchor;
  time_range_s: [number, number] | null;
  output_unit: string;
  depth_info: Record<string, unknown> | null;
  target_depth_key: string | null;
  reference_depth_key: string | null;
  plausible_range_si: [number, number];
  notes: string;
}

export interface Check {
  name: string;
  passed: boolean;
  value: number | null;
  threshold: string;
  detail: string;
}

export interface AuditVerdict {
  target_is_right_object: boolean;
  reference_is_right_object: boolean;
  reference_same_plane: "yes" | "no" | "unclear";
  occlusion_or_identity_switch: boolean;
  approve: boolean;
  reason: string;
}

export interface Result {
  run_id: string;
  status: "measured" | "abstained";
  value: number | null;
  unit: string;
  interval_90: [number, number] | null;
  quantity: Quantity;
  spec: MeasurementSpec;
  scale_m_per_px: number | null;
  method: string;
  checks: Check[];
  audit: AuditVerdict | null;
  abstain_reason: string | null;
  artifacts: Record<string, unknown>;
  backend: "meta_api" | "muse_spark_open";
  cost_usd: number;
  timings_ms: Record<string, number>;
}

// Overlay (backend/caliper/overlay.py)
export interface OverlayObject {
  path: string; // SVG path in video pixels
  centroid: [number, number];
}

export interface OverlayFrame {
  frame: number;
  target: OverlayObject | null;
  reference: OverlayObject | null;
}

export interface FitRow {
  t_s: number;
  pos_m: number;
  fit_m: number;
}

export interface SpeedRow {
  t_s: number;
  speed_m_s: number;
}

export interface Overlay {
  fps?: number;
  width?: number;
  height?: number;
  frames?: OverlayFrame[];
  fit?: FitRow[];
  speed?: SpeedRow[];
}

// Cached runs (backend/caliper/runs.py, schema v1)
export type RunSource = "placeholder_synthetic" | "field" | "live";

export interface RunMeta {
  title: string;
  question: string;
  source: RunSource;
  placeholder: boolean;
  notes: string;
  created_utc: string;
  clip: string | null;
  poster: string | null;
}

export interface CachedRun {
  schema_version: number;
  kind: "measure" | "study";
  meta: RunMeta;
  result: Result; // measure runs; study runs arrive with Phase 4
  overlay: Overlay;
  guess?: Pick<Guess, "text" | "parsed_value"> | null; // recorded Muse Spark alone answer
}

// Street speed study (ARCHITECTURE section 3 StudySummary, section 11 study overlay).
// Phase 4 writes these through runs.save_cached_run(kind="study", result=StudySummary, overlay=...).
export interface VehicleReading {
  vehicle_id: string;
  vehicle_class: string; // car, motorcycle, auto rickshaw, bus
  status: "measured" | "no_reading";
  speed_kmh: number | null;
  interval_90_kmh: [number, number] | null;
  t_gate_a_s: number | null;
  t_gate_b_s: number | null;
  reason: string | null;
}

export interface StudySummary {
  run_id: string;
  gate_distance_m: number;
  duration_s: number;
  vehicles_seen: number;
  vehicles_measured: number;
  median_kmh: number | null;
  p85_kmh: number | null;
  p85_interval_90_kmh: [number, number] | null;
  speed_limit_kmh: number | null;
  share_over_limit: number | null;
  readings: VehicleReading[];
}

/** A gate line in video pixels: two points across the road. */
export type GateLine = [[number, number], [number, number]];

export interface StudyCrossing {
  frame: number;
  path: string; // SVG outline in video pixels at the crossing
  anchor: [number, number]; // where the label sits
}

export interface StudyOverlay {
  fps?: number;
  width?: number;
  height?: number;
  gate_a?: GateLine;
  gate_b?: GateLine;
  vehicles?: { vehicle_id: string; crossings: StudyCrossing[] }[];
}

export interface CachedStudyRun {
  schema_version: number;
  kind: "study";
  meta: RunMeta;
  result: StudySummary;
  overlay: StudyOverlay;
}

export interface RunIndexEntry {
  run_id: string;
  kind: "measure" | "study";
  title: string;
  status: string;
  source: RunSource;
  placeholder: boolean;
  created_utc: string;
}

export interface Caps {
  max_clip_seconds: number;
  max_study_seconds: number;
  runs_per_ip_per_hour: number;
  per_run_cap_usd: number;
  per_study_cap_usd: number;
  daily_spend_cap_usd: number;
}

export interface Health {
  ok: boolean;
  live_runs_enabled: boolean;
  caps: Caps;
}

export interface Guess {
  text: string;
  parsed_value: number | null;
  cost_usd: number;
}

export interface ApiErrorBody {
  code: string;
  message: string;
  cached_runs?: RunIndexEntry[];
}
