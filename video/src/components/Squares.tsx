import { spring, useCurrentFrame, useVideoConfig } from "remotion";
import { CALM, COLOR, FONT } from "../theme.ts";

/** A row of n unit squares, k of them filled one by one from `start`: "9 of 15" made visible. */
export const Squares: React.FC<{
  n: number;
  k: number;
  start: number;
  color: string;
  label: string;
  size?: number;
}> = ({ n, k, start, color, label, size = 44 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = spring({
    frame: frame - start,
    fps,
    config: CALM,
    durationInFrames: 30,
  });
  const lit = p > 0.995 ? k : Math.floor(k * p + 1e-9);
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 14,
        opacity: frame >= start - 6 ? 1 : 0,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "baseline",
          gap: 18,
          fontFamily: FONT.sans,
        }}
      >
        <span
          style={{
            fontFamily: FONT.mono,
            fontSize: 64,
            color,
            fontVariantNumeric: "tabular-nums",
          }}
        >
          {lit}{" "}
          <span style={{ fontSize: 34, color: COLOR.mutedForeground }}>
            of {n}
          </span>
        </span>
        <span style={{ fontSize: 30, color: COLOR.foreground }}>{label}</span>
      </div>
      <div style={{ display: "flex", gap: 10 }}>
        {Array.from({ length: n }, (_, i) => (
          <div
            key={i}
            style={{
              width: size,
              height: size,
              borderRadius: 7,
              border: `2px solid ${i < lit ? color : COLOR.border}`,
              backgroundColor: i < lit ? color : "transparent",
              opacity: i < lit ? 0.92 : 0.7,
            }}
          />
        ))}
      </div>
    </div>
  );
};
