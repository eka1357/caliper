import type { ReactNode } from "react";
import { spring, useCurrentFrame, useVideoConfig } from "remotion";
import type { Pt } from "../lib/geometry.ts";
import { CALM, COLOR } from "../theme.ts";

export type Rect = [number, number, number, number]; // x, y, width, height on screen

/** A camera move: from frame `at`, spring over `dur` frames to the given window, focus and zoom. */
export type Shot = {
  at: number;
  dur: number;
  win?: Rect;
  focus?: Pt;
  zoom?: number;
  radius?: number;
};

type State = { win: Rect; focus: Pt; zoom: number; radius: number };

const lerp = (a: number, b: number, p: number) => a + (b - a) * p;

/** Moves blend in order, so a move that starts before the last one settles stays continuous. */
function stateAt(shots: Shot[], frame: number, fps: number): State {
  const first = shots[0];
  let s: State = {
    win: first.win!,
    focus: first.focus!,
    zoom: first.zoom!,
    radius: first.radius ?? 0,
  };
  for (const shot of shots.slice(1)) {
    if (frame < shot.at) continue;
    const p = spring({
      frame: frame - shot.at,
      fps,
      config: CALM,
      durationInFrames: shot.dur,
    });
    s = {
      win: shot.win
        ? (s.win.map((v, i) => lerp(v, shot.win![i], p)) as Rect)
        : s.win,
      focus: shot.focus
        ? [
            lerp(s.focus[0], shot.focus[0], p),
            lerp(s.focus[1], shot.focus[1], p),
          ]
        : s.focus,
      zoom: shot.zoom
        ? Math.exp(lerp(Math.log(s.zoom), Math.log(shot.zoom), p))
        : s.zoom,
      radius:
        shot.radius !== undefined ? lerp(s.radius, shot.radius, p) : s.radius,
    };
  }
  return s;
}

/**
 * A window onto a clip, with a slow spring-eased camera. Children are laid out in the clip's own
 * pixels (video and SAM overlays share them) and get the zoom, to keep strokes a constant width.
 */
export const ClipStage: React.FC<{
  shots: Shot[];
  srcW: number;
  srcH: number;
  children: (zoom: number) => ReactNode;
}> = ({ shots, srcW, srcH, children }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const st = stateAt(shots, frame, fps);
  const [x, y, w, h] = st.win;
  const fit = (win: number, src: number, t: number) =>
    src * st.zoom >= win
      ? Math.min(0, Math.max(win - src * st.zoom, t))
      : (win - src * st.zoom) / 2;
  const tx = fit(w, srcW, w / 2 - st.focus[0] * st.zoom);
  const ty = fit(h, srcH, h / 2 - st.focus[1] * st.zoom);
  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y,
        width: w,
        height: h,
        overflow: "hidden",
        borderRadius: st.radius,
        boxShadow: `0 0 0 1px ${COLOR.border}, 0 30px 80px rgba(0,0,0,0.55)`,
        backgroundColor: COLOR.background,
      }}
    >
      <div
        style={{
          position: "absolute",
          left: 0,
          top: 0,
          width: srcW,
          height: srcH,
          transformOrigin: "0 0",
          translate: `${tx}px ${ty}px`,
          scale: String(st.zoom),
        }}
      >
        {children(st.zoom)}
      </div>
      <div
        style={{
          position: "absolute",
          inset: 0,
          background:
            "radial-gradient(ellipse at center, rgba(0,0,0,0) 62%, rgba(0,0,0,0.32) 100%)",
          pointerEvents: "none",
        }}
      />
    </div>
  );
};
