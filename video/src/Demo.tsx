// The 3-minute demo: eight scenes, crossfades, and one hard match cut (the scooter pass straight
// into the car pass that Caliper refuses). Scene lengths follow their narration (src/timeline.ts).
import { linearTiming, TransitionSeries } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import type { Footage, Narration, Recording } from "./lib/media.ts";
import { Scene1 } from "./scenes/Scene1.tsx";
import { Scene2 } from "./scenes/Scene2.tsx";
import { Scene3 } from "./scenes/Scene3.tsx";
import { Scene4 } from "./scenes/Scene4.tsx";
import { Scene5 } from "./scenes/Scene5.tsx";
import { Scene6 } from "./scenes/Scene6.tsx";
import { Scene7 } from "./scenes/Scene7.tsx";
import { Scene8 } from "./scenes/Scene8.tsx";
import { SceneX7 } from "./scenes/SceneX7.tsx";
import { FADE, sceneFrames } from "./timeline.ts";

export type Media = {
  n: Record<string, Narration> | null;
  f: Record<string, Footage> | null;
  r: Record<string, Recording> | null;
};

// TransitionSeries takes its own elements only, so this returns one (not a component).
const fadeT = () => (
  <TransitionSeries.Transition
    presentation={fade()}
    timing={linearTiming({ durationInFrames: FADE })}
  />
);

export const demoFrames = (n: Record<string, Narration>) =>
  ["s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8"].reduce(
    (s, id) => s + sceneFrames(n[id]),
    0,
  ) -
  6 * FADE;

export const Demo: React.FC<Media> = ({ n, f, r }) => {
  if (!n || !f || !r) return null;
  return (
    <TransitionSeries>
      <TransitionSeries.Sequence durationInFrames={sceneFrames(n.s1)}>
        <Scene1 narration={n.s1} footage={f.c07} />
      </TransitionSeries.Sequence>
      {fadeT()}
      <TransitionSeries.Sequence durationInFrames={sceneFrames(n.s2)}>
        <Scene2 narration={n.s2} footage={f.a14} />
      </TransitionSeries.Sequence>
      <TransitionSeries.Sequence durationInFrames={sceneFrames(n.s3)}>
        <Scene3 narration={n.s3} footage={f.a08} rec={r.s3_refusal} />
      </TransitionSeries.Sequence>
      {fadeT()}
      <TransitionSeries.Sequence durationInFrames={sceneFrames(n.s4)}>
        <Scene4 narration={n.s4} chain={r.s4_chain} audit={r.s4_audit} />
      </TransitionSeries.Sequence>
      {fadeT()}
      <TransitionSeries.Sequence durationInFrames={sceneFrames(n.s5)}>
        <Scene5 narration={n.s5} rec={r.s5_study} />
      </TransitionSeries.Sequence>
      {fadeT()}
      <TransitionSeries.Sequence durationInFrames={sceneFrames(n.s6)}>
        <Scene6 narration={n.s6} />
      </TransitionSeries.Sequence>
      {fadeT()}
      <TransitionSeries.Sequence durationInFrames={sceneFrames(n.s7)}>
        <Scene7 narration={n.s7} rec={r.s7_results} />
      </TransitionSeries.Sequence>
      {fadeT()}
      <TransitionSeries.Sequence durationInFrames={sceneFrames(n.s8)}>
        <Scene8 narration={n.s8} rec={r.s8_landing} />
      </TransitionSeries.Sequence>
    </TransitionSeries>
  );
};

const X_FADE = 12;

export const xFrames = (n: Record<string, Narration>) =>
  sceneFrames(n.x1) + sceneFrames(n.x3) + sceneFrames(n.x7) - 2 * X_FADE;

/** The 40-second cut for X: scenes 1, 3 and 7, condensed, with their own shorter narration. */
export const XCut: React.FC<Media> = ({ n, f, r }) => {
  if (!n || !f || !r) return null;
  const xf = (
    <TransitionSeries.Transition
      presentation={fade()}
      timing={linearTiming({ durationInFrames: X_FADE })}
    />
  );
  return (
    <TransitionSeries>
      <TransitionSeries.Sequence durationInFrames={sceneFrames(n.x1)}>
        <Scene1 narration={n.x1} footage={f.c07} variant="x" />
      </TransitionSeries.Sequence>
      {xf}
      <TransitionSeries.Sequence durationInFrames={sceneFrames(n.x3)}>
        <Scene3
          narration={n.x3}
          footage={f.a08}
          rec={r.s3_refusal}
          variant="x"
        />
      </TransitionSeries.Sequence>
      {xf}
      <TransitionSeries.Sequence durationInFrames={sceneFrames(n.x7)}>
        <SceneX7 narration={n.x7} />
      </TransitionSeries.Sequence>
    </TransitionSeries>
  );
};
