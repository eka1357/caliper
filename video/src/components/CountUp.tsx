import { spring, useCurrentFrame, useVideoConfig } from "remotion";
import { fmt } from "../../../web/src/lib/format.ts";
import { CALM } from "../theme.ts";

/** Counts from 0 to the value with a critically damped spring; ends exactly on the value. */
export const CountUp: React.FC<{
  value: number;
  decimals: number;
  start: number;
  duration?: number;
}> = ({ value, decimals, start, duration }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = spring({
    frame: frame - start,
    fps,
    config: CALM,
    durationInFrames: duration ?? Math.round(fps * 1.1),
  });
  return <>{fmt(p > 0.995 ? value : value * p, decimals)}</>;
};

/** Decimals of a number printed raw, e.g. "16.2" -> 1 (the site shows guesses and tape readings raw). */
export const decimalsOf = (raw: string) => (raw.split(".")[1] ?? "").length;
