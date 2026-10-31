"use client";

import { useEffect, useRef } from "react";
import { useGsapLib } from "./motion-lib";
import { useMotionAllowed } from "./motion-pref";

/**
 * Decorative effect 1 of 3: the hero headline's words rise 12 px with a 0.03 s stagger, once
 * (GSAP SplitText, which arrives just after the first paint). The headline is fully painted from
 * the first frame, and words start from 0.6 opacity so the late start never blinks.
 * Reduced motion: the headline is simply there.
 */
export function HeroHeadline({ children }: { children: string }) {
  const ref = useRef<HTMLHeadingElement>(null);
  const allowed = useMotionAllowed();
  const lib = useGsapLib();

  useEffect(() => {
    if (!allowed || !lib || !ref.current) return;
    const { gsap, SplitText } = lib;
    const split = SplitText.create(ref.current, { type: "words" });
    const tween = gsap.from(split.words, {
      y: 12,
      opacity: 0.6,
      duration: 0.5,
      ease: "power2.out",
      stagger: 0.03,
      onComplete: () => split.revert(),
    });
    return () => {
      tween.kill();
      split.revert();
    };
  }, [allowed, lib]);

  return (
    <h1 ref={ref} className="font-display text-5xl leading-[1.05] sm:text-6xl lg:text-7xl">
      {children}
    </h1>
  );
}
