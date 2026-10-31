// Motion presets (docs/DESIGN.md section 5). Workspace motion only confirms state changes.
import type { Transition } from "motion/react";

export const EASE: [number, number, number, number] = [0.2, 0, 0, 1];

/** Hover and press: 120 to 160 ms. */
export const press: Transition = { duration: 0.14, ease: EASE };

/** Result card enter and exit: 240 ms, opacity 0 to 1, y 8 px to 0. */
export const cardEnter = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: 8 },
  transition: { duration: 0.24, ease: EASE } satisfies Transition,
};

/** Readout number counts to its value over 600 ms, ease-out; the interval bar grows after. */
export const readout: Transition = { duration: 0.6, ease: "easeOut" };
export const intervalGrow: Transition = { duration: 0.3, ease: EASE, delay: 0.6 };

/** Mask outlines: 200 ms fade per object. */
export const outlineFade: Transition = { duration: 0.2, ease: EASE };

/** Panel layout changes: spring, no overshoot. */
export const layoutSpring: Transition = { type: "spring", bounce: 0, duration: 0.35 };

/** Reduced motion: final state with at most a 150 ms opacity fade. */
export const reducedFade: Transition = { duration: 0.15 };
