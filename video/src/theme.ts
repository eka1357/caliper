// The site's look (web/src/app/globals.css, docs/DESIGN.md sections 2 and 3).
import { loadFont as loadGeist } from "@remotion/google-fonts/Geist";
import { loadFont as loadGeistMono } from "@remotion/google-fonts/GeistMono";
import { loadFont as loadInstrumentSerif } from "@remotion/google-fonts/InstrumentSerif";

export const COLOR = {
  background: "#0A0C0F",
  card: "#12161B",
  muted: "#181D23",
  border: "#232A32",
  foreground: "#E9EDF1",
  mutedForeground: "#8A96A3",
  primary: "#FFB224", // amber: the ruler (scale reference, "Measured")
  track: "#2FD3E6", // cyan: the target being measured
  success: "#3DDC97",
  destructive: "#FF5A5F",
} as const;

export const FONT = {
  display: loadInstrumentSerif("normal", {
    weights: ["400"],
    subsets: ["latin"],
  }).fontFamily,
  sans: loadGeist("normal", {
    weights: ["400", "500", "600"],
    subsets: ["latin"],
  }).fontFamily,
  mono: loadGeistMono("normal", { weights: ["400", "500"], subsets: ["latin"] })
    .fontFamily,
} as const;

/** Critically damped: no overshoot, so a counted number never passes its value. */
export const CALM = { damping: 200 } as const;

export const W = 1920;
export const H = 1080;
