"use client";

import "lenis/dist/lenis.css";
import { ReactLenis, useLenis } from "lenis/react";
import { useEffect } from "react";
import { gsap, ScrollTrigger } from "./gsap";
import { useMotionAllowed } from "./motion-pref";

/** Drives the root Lenis instance from gsap.ticker and feeds ScrollTrigger (docs/TOOLS.md). */
function TickerBridge() {
  const lenis = useLenis();
  useEffect(() => {
    if (!lenis) return;
    lenis.on("scroll", ScrollTrigger.update);
    const update = (time: number) => lenis.raf(time * 1000);
    gsap.ticker.add(update);
    gsap.ticker.lagSmoothing(0);
    return () => {
      lenis.off("scroll", ScrollTrigger.update);
      gsap.ticker.remove(update);
    };
  }, [lenis]);
  return null;
}

/**
 * Lenis on the landing only, with root and autoRaf false, so Lenis and ScrollTrigger share
 * GSAP's clock. With reduced motion there is no Lenis: native scrolling. The page content is a
 * sibling, not a child, so turning Lenis on after hydration never remounts it.
 */
export function SmoothScroll() {
  const allowed = useMotionAllowed();
  if (!allowed) return null;
  return (
    <ReactLenis root options={{ autoRaf: false }}>
      <TickerBridge />
    </ReactLenis>
  );
}
