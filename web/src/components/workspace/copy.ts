// Workspace copy, exactly as in docs/DESIGN.md section 6 (States and copy).
import type { Result } from "@/lib/types";

export const COPY = {
  idle: "Drop a clip or record one. Keep the phone still.",
  uploading: (n: number) => `Uploading ${n}%`,
  preparing: "Preparing the video",
  reading: "Reading your question",
  finding: (target: string, reference: string) => `Finding the ${target} and the ${reference}`,
  measuring: "Measuring",
  checking: "Checking the measurement",
  auditing: "Muse Spark is checking the evidence",
  abstained: "I won't guess.",
  cap: "Live runs are paused for now. Try one of these recorded runs.",
  error: "Something broke on our side.",
  captureGuide:
    "Keep the phone still. Put a coin beside the object, at the same distance. Film the motion side to side, not toward you.",
} as const;

/** The server steps a live run goes through, in order (listed while waiting; not live-tracked). */
export const LIVE_STEPS = [
  COPY.preparing,
  COPY.reading,
  COPY.finding("target", "reference"),
  COPY.measuring,
  COPY.checking,
  COPY.auditing,
] as const;

export const EXAMPLES = [
  "How fast is the white car in m/s?",
  "How long is the box in cm?",
  "How hard does the ball accelerate in m/s²?",
] as const;

// One fix per refusal (DESIGN: "followed by the reason ... and one fix").
const FIX_BY_CHECK: Record<string, string> = {
  reference_found: "Add a coin next to the object.",
  reference_too_small: "Move closer, or use a bigger reference such as an A4 sheet.",
  same_plane: "Put the reference beside the object, at the same distance from the camera.",
  depth_change: "Film the motion side to side, not toward you.",
  track_continuity: "Keep the whole motion in view, with nothing passing in front.",
  target_found: "Keep the object in frame for the whole clip.",
  mask_stability: "Film in steady light against a plain background.",
  interval_width: "Film closer, or keep the motion in view for longer.",
  estimates_agree: "Film closer and keep the phone still.",
  scene_scale: "Check the size you gave for the reference.",
  physical_bounds: "Check the size you gave for the reference.",
  gravity_reference: "Give one real size in the question instead.",
};

export function fixFor(result: Result): string {
  if (result.audit && !result.audit.approve) {
    return "Make the object you mean the only one of its kind in view, or name it more precisely.";
  }
  const failed = result.checks.find((c) => !c.passed);
  if (failed && FIX_BY_CHECK[failed.name]) return FIX_BY_CHECK[failed.name];
  const reason = result.abstain_reason ?? "";
  if (reason.includes("never fully inside the picture")) {
    return "Film from farther back so the whole object stays in the picture while it moves.";
  }
  if (reason.startsWith("No reference value")) {
    return "Type one known size, or put a coin or an A4 sheet next to the object.";
  }
  return "Add a coin next to the object.";
}
