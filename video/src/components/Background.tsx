import { AbsoluteFill } from "remotion";
import { COLOR } from "../theme.ts";

/** The site's measurement grid (1 px border lines) on the page colour, with a soft vignette. */
export const Background: React.FC<{ grid?: number }> = ({ grid = 48 }) => (
  <AbsoluteFill style={{ backgroundColor: COLOR.background }}>
    <AbsoluteFill
      style={{
        backgroundImage: `linear-gradient(${COLOR.border} 1px, transparent 1px), linear-gradient(90deg, ${COLOR.border} 1px, transparent 1px)`,
        backgroundSize: `${grid}px ${grid}px`,
        opacity: 0.45,
      }}
    />
    <AbsoluteFill
      style={{
        background:
          "radial-gradient(ellipse at 50% 45%, rgba(10,12,15,0) 35%, rgba(10,12,15,0.85) 100%)",
      }}
    />
  </AbsoluteFill>
);
