import type { ReactNode } from "react";
import type { Pt } from "../lib/geometry.ts";
import { FONT } from "../theme.ts";

type Anchor =
  | "above-right"
  | "above-left"
  | "above"
  | "right"
  | "left"
  | "below";

const PLACE: Record<Anchor, React.CSSProperties> = {
  "above-right": { right: 0, bottom: 10 },
  "above-left": { left: 0, bottom: 10 },
  above: { left: 0, bottom: 12, translate: "-50% 0px" },
  right: { left: 14, top: 0, translate: "0px -50%" },
  left: { right: 14, top: 0, translate: "0px -50%" },
  below: { left: 0, top: 12, translate: "-50% 0px" },
};

/** A label pinned to a point of a clip that keeps its screen size while the camera zooms. */
export const Pin: React.FC<{
  at: Pt;
  z: number;
  anchor: Anchor;
  children: ReactNode;
}> = ({ at, z, anchor, children }) => (
  <div
    style={{
      position: "absolute",
      left: at[0],
      top: at[1],
      width: 0,
      height: 0,
      scale: String(1 / z),
      transformOrigin: "0 0",
    }}
  >
    <div
      style={{ position: "absolute", whiteSpace: "nowrap", ...PLACE[anchor] }}
    >
      {children}
    </div>
  </div>
);

export const pill = (color: string, size = 24): React.CSSProperties => ({
  fontFamily: FONT.mono,
  fontSize: size,
  color,
  padding: "5px 12px",
  borderRadius: 8,
  backgroundColor: "rgba(10,12,15,0.84)",
  border: `1px solid ${color}66`,
  fontVariantNumeric: "tabular-nums",
});
