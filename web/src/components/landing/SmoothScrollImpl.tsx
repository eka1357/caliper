"use client";

import "lenis/dist/lenis.css";
import Lenis from "lenis";
import { useEffect } from "react";
import type { GsapLib } from "./motion-lib";

const HEARTBEAT_MS = 1000; // the GSAP ticker must tick at least this often while the tab is visible
const WHEEL_GRACE_MS = 700; // after a wheel event the page must have moved within this time

/**
 * Lenis on GSAP's clock (one animation clock, docs/TOOLS.md), with native scroll as the floor.
 * Lenis takes over the wheel, so if its clock ever stops, or a wheel event does not move the page,
 * it is destroyed and the browser scrolls natively again. The instance is created here, not with
 * ReactLenis + useLenis, so a remount can never leave the ticker driving a stale instance.
 */
export default function SmoothScrollImpl({ lib }: { lib: GsapLib }) {
  useEffect(() => {
    const { gsap, ScrollTrigger } = lib;
    let lenis: Lenis | null;
    try {
      lenis = new Lenis({ autoRaf: false });
    } catch {
      return; // native scroll
    }
    let lastTick = performance.now();
    let wheel: { at: number; y: number; down: boolean } | null = null;

    const update = (time: number) => {
      lastTick = performance.now();
      lenis?.raf(time * 1000);
    };
    const onScroll = () => ScrollTrigger.update();
    const onVisible = () => {
      if (document.visibilityState === "visible") lastTick = performance.now();
    };
    const onWheel = (e: WheelEvent) => {
      if (!wheel && e.deltaY !== 0) wheel = { at: performance.now(), y: window.scrollY, down: e.deltaY > 0 };
    };
    const giveUp = () => {
      if (!lenis) return;
      gsap.ticker.remove(update);
      lenis.off("scroll", onScroll);
      lenis.destroy();
      lenis = null;
      ScrollTrigger.refresh();
    };
    const watchdog = window.setInterval(() => {
      if (!lenis) return;
      const now = performance.now();
      if (document.visibilityState === "visible" && now - lastTick > HEARTBEAT_MS) {
        giveUp(); // the clock stopped: hand the wheel back to the browser
        return;
      }
      if (wheel && now - wheel.at > WHEEL_GRACE_MS) {
        const max = document.documentElement.scrollHeight - window.innerHeight;
        const room = wheel.down ? wheel.y < max - 1 : wheel.y > 1;
        if (room && Math.abs(window.scrollY - wheel.y) < 1) giveUp(); // wheel eaten, page did not move
        wheel = null;
      }
    }, 250);

    lenis.on("scroll", onScroll);
    gsap.ticker.add(update);
    gsap.ticker.lagSmoothing(0);
    document.addEventListener("visibilitychange", onVisible);
    window.addEventListener("wheel", onWheel, { passive: true });
    return () => {
      window.clearInterval(watchdog);
      document.removeEventListener("visibilitychange", onVisible);
      window.removeEventListener("wheel", onWheel);
      giveUp();
    };
  }, [lib]);
  return null;
}
