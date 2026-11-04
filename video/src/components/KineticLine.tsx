import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { CALM, COLOR, FONT } from "../theme.ts";

/**
 * A key line as large Instrument Serif type: the scene dims, words rise in one by one, and one
 * word can get an amber underline (the "measures" of the site's title card). With `end`, it fades
 * out over the last 10 frames before that frame.
 */
export const KineticLine: React.FC<{
  lines: string[];
  start: number;
  end?: number;
  underline?: string;
  size?: number;
  dim?: number;
  lift?: number;
}> = ({ lines, start, end, underline, size = 150, dim = 0.9, lift = 0 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  if (frame < start || (end !== undefined && frame >= end)) return null;
  const clamp = {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  } as const;
  const out =
    end === undefined ? 1 : interpolate(frame, [end - 10, end], [1, 0], clamp);
  const bg = interpolate(frame - start, [0, 12], [0, dim], clamp) * out;
  let k = 0;
  const total = lines.reduce((n, l) => n + l.split(" ").length, 0);
  const lastIn = start + 4 * (total - 1) + 18;
  return (
    <AbsoluteFill
      style={{
        backgroundColor: `rgba(10,12,15,${bg})`,
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: size * 0.08,
          opacity: out,
          translate: `0px ${-lift}px`,
        }}
      >
        {lines.map((line) => (
          <div
            key={line}
            style={{
              display: "flex",
              gap: size * 0.26,
              fontFamily: FONT.display,
              fontSize: size,
              lineHeight: 1.05,
              color: COLOR.foreground,
            }}
          >
            {line.split(" ").map((word) => {
              const i = k++;
              const p = spring({
                frame: frame - start - 4 * i,
                fps,
                config: CALM,
                durationInFrames: 22,
              });
              const u =
                underline && word === underline
                  ? spring({
                      frame: frame - lastIn,
                      fps,
                      config: CALM,
                      durationInFrames: 24,
                    })
                  : 0;
              return (
                <span
                  key={`${word}-${i}`}
                  style={{
                    position: "relative",
                    display: "inline-block",
                    opacity: p,
                    translate: `0px ${(1 - p) * 34}px`,
                  }}
                >
                  {word}
                  {u > 0 && (
                    <span
                      style={{
                        position: "absolute",
                        left: 0,
                        right: size * 0.06,
                        bottom: -size * 0.04,
                        height: Math.max(5, size * 0.045),
                        borderRadius: 4,
                        backgroundColor: COLOR.primary,
                        transformOrigin: "0 50%",
                        scale: `${u} 1`,
                      }}
                    />
                  )}
                </span>
              );
            })}
          </div>
        ))}
      </div>
    </AbsoluteFill>
  );
};
