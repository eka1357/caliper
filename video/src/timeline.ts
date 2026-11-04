// Scene lengths: each scene runs from a short lead-in, through its narration, to a short hold.
// Fitted to the audio: pauses are extended or trimmed here, speech is never sped up.
import type { Narration } from "./lib/media.ts";

export const FPS = 30;
/** Crossfade between scenes, in frames. Scene 2 to 3 is the one hard (match) cut. */
export const FADE = 15;

/** Seconds before the voice starts and after it ends. */
export const PAD: Record<string, [number, number]> = {
  s1: [1.4, 1.6],
  s2: [0.8, 1.6],
  s3: [0.6, 1.4],
  s4: [0.6, 1.4],
  s5: [0.7, 1.6],
  s6: [0.8, 2.6],
  s7: [0.8, 2.0],
  s8: [0.6, 5.0],
  x1: [0.5, 0.9],
  x3: [0.3, 1.3],
  x7: [0.5, 2.8],
};

export const leadFrames = (id: string) => Math.round(PAD[id][0] * FPS);

export const sceneFrames = (n: Narration) =>
  Math.ceil((PAD[n.id][0] + n.durationMs / 1000 + PAD[n.id][1]) * FPS);
