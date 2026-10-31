"use client";

import { useSyncExternalStore } from "react";

const QUERY = "(prefers-reduced-motion: reduce)";

function subscribe(cb: () => void) {
  const m = window.matchMedia(QUERY);
  m.addEventListener("change", cb);
  return () => m.removeEventListener("change", cb);
}

/**
 * True when motion is allowed. The server snapshot is false, so the first paint is always the
 * final, readable state; effects start only after hydration and only without reduced motion.
 */
export function useMotionAllowed(): boolean {
  return useSyncExternalStore(
    subscribe,
    () => !window.matchMedia(QUERY).matches,
    () => false,
  );
}

/** True when the viewport matches `query`. The server snapshot is false. */
export function useMedia(query: string): boolean {
  return useSyncExternalStore(
    (cb) => {
      const m = window.matchMedia(query);
      m.addEventListener("change", cb);
      return () => m.removeEventListener("change", cb);
    },
    () => window.matchMedia(query).matches,
    () => false,
  );
}
