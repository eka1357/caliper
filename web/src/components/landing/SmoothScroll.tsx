"use client";

import dynamic from "next/dynamic";
import { useEffect } from "react";
import { loadMotionLib, useGsapLib } from "./motion-lib";
import { useMotionAllowed } from "./motion-pref";

const SmoothScrollImpl = dynamic(() => import("./SmoothScrollImpl"), { ssr: false });

/**
 * Starts the landing's motion after load: fetches GSAP, then mounts Lenis on GSAP's ticker.
 * With reduced motion nothing loads: native scrolling and no effects. The page content is a
 * sibling, not a child, so turning Lenis on never remounts it.
 */
export function SmoothScroll() {
  const allowed = useMotionAllowed();
  const lib = useGsapLib();
  useEffect(() => {
    if (allowed) loadMotionLib();
  }, [allowed]);
  if (!allowed || !lib) return null;
  return <SmoothScrollImpl lib={lib} />;
}
