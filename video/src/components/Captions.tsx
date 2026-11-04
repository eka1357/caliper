import { useMemo } from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { pages } from "../lib/captions.ts";
import type { Narration, Word } from "../lib/media.ts";
import { FONT } from "../theme.ts";

/**
 * Burned-in captions of exactly what the voice says (ElevenLabs timings), bottom centre, white on
 * near-black. Words of a key line are left out: that line is on screen as large type.
 */
export const Captions: React.FC<{
  narration: Narration;
  delay: number;
  maxChars?: number;
  bottom?: number;
}> = ({ narration, delay, maxChars = 54, bottom = 44 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const list = useMemo(() => {
    const inKey = (w: Word) =>
      narration.keys.some(
        (k) => w.startMs >= k.startMs - 30 && w.endMs <= k.endMs + 30,
      );
    return pages(narration.words, maxChars, inKey);
  }, [narration, maxChars]);
  const t = ((frame - delay) / fps) * 1000;
  const i = list.findIndex((p, k) => {
    const next = list[k + 1];
    const until = Math.min(next ? next.startMs : Infinity, p.endMs + 900);
    return t >= p.startMs - 60 && t < until;
  });
  if (i < 0) return null;
  return (
    <div
      style={{
        position: "absolute",
        left: "50%",
        bottom,
        translate: "-50% 0px",
        maxWidth: 1600,
        padding: "10px 28px 13px",
        borderRadius: 10,
        backgroundColor: "rgba(5,7,9,0.88)",
        color: "#FFFFFF",
        fontFamily: FONT.sans,
        fontWeight: 500,
        fontSize: 44,
        lineHeight: 1.25,
        letterSpacing: "-0.005em",
        whiteSpace: "nowrap",
        textAlign: "center",
      }}
    >
      {list[i].text}
    </div>
  );
};
