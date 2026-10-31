// /study copy (docs/DESIGN.md section 6). Never implies enforcement; no plates or faces.
export const STUDY_COPY = {
  title: "Speed survey for road-safety requests",
  guide:
    "Phone fixed, side-on to the road. Two marks a measured distance apart along the road edge, both in frame.",
  gates: "Drag the ends of the two gate lines onto the marks on the first frame.",
  noReading: "no reading",
  privacy: "No number plates or faces are stored or shown.",
  method:
    "Two gate lines are drawn across the road on marks a measured distance apart. SAM 3.1 tracks each vehicle; the time each one takes between the gates gives its speed, with a 90% range from frame timing, gate placement and the tape tolerance. Vehicles that are hidden at a gate, change identity, or give inconsistent estimates get no reading instead of a guess. The 85th-percentile speed has its own range, bootstrapped over vehicles.",
  limitations: [
    "Speeds are averages between the two gates, not spot speeds.",
    "Accuracy depends on the tape-measured gate distance and on the camera staying still.",
    "Vehicles marked “no reading” are left out of the median and the 85th percentile.",
    "A survey of a few minutes is a sample of one time of day, not a traffic count.",
    "This is evidence for road-safety requests, not a tool for enforcement.",
  ],
  noStudy:
    "No street study has been recorded yet. Studies come from our own street clips, which arrive with Phase 4. Until then nothing here shows a number.",
} as const;

export const fmtKmh = (v: number | null) => (v == null ? "n/a" : Math.round(v).toString());
export const fmtRange = (r: [number, number] | null) =>
  r ? `${Math.round(r[0])}–${Math.round(r[1])}` : "n/a";
