"use client";

import { useSyncExternalStore } from "react";
import type * as GsapModule from "./gsap";

export type GsapLib = typeof GsapModule;

let lib: GsapLib | null = null;
let started = false;
const subs = new Set<() => void>();

/**
 * Fetch GSAP (and its plugins) once the page has loaded and the main thread is idle, so the
 * animation code never delays the first paint. Until it arrives every element is already in its
 * final, readable state; the effects then play on top.
 */
export function loadMotionLib(): void {
  if (started) return;
  started = true;
  const go = () =>
    window.requestIdleCallback(
      () =>
        void import("./gsap").then((m) => {
          lib = m;
          subs.forEach((f) => f());
        }),
      { timeout: 2000 },
    );
  if (document.readyState === "complete") go();
  else window.addEventListener("load", go, { once: true });
}

/** The loaded GSAP library, or null before it arrives (and always null on the server). */
export function useGsapLib(): GsapLib | null {
  return useSyncExternalStore(
    (cb) => {
      subs.add(cb);
      return () => subs.delete(cb);
    },
    () => lib,
    () => null,
  );
}
