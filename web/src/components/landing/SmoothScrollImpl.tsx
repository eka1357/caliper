"use client";

import "lenis/dist/lenis.css";
import { ReactLenis, useLenis } from "lenis/react";
import { useEffect } from "react";
import type { GsapLib } from "./motion-lib";

/** Drives the root Lenis instance from gsap.ticker and feeds ScrollTrigger (docs/TOOLS.md). */
function TickerBridge({ lib }: { lib: GsapLib }) {
  const lenis = useLenis();
  useEffect(() => {
    if (!lenis) return;
    const { gsap, ScrollTrigger } = lib;
    lenis.on("scroll", ScrollTrigger.update);
    const update = (time: number) => lenis.raf(time * 1000);
    gsap.ticker.add(update);
    gsap.ticker.lagSmoothing(0);
    return () => {
      lenis.off("scroll", ScrollTrigger.update);
      gsap.ticker.remove(update);
    };
  }, [lenis, lib]);
  return null;
}

/** Lenis via lenis/react with root and autoRaf false, on GSAP's clock. */
export default function SmoothScrollImpl({ lib }: { lib: GsapLib }) {
  return (
    <ReactLenis root options={{ autoRaf: false }}>
      <TickerBridge lib={lib} />
    </ReactLenis>
  );
}
