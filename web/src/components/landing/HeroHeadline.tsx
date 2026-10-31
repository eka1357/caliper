"use client";

import { useRef } from "react";
import { gsap, SplitText, useGSAP } from "./gsap";
import { useMotionAllowed } from "./motion-pref";

/**
 * Decorative effect 1 of 3: the hero headline's words rise 12 px with a 0.03 s stagger, once on
 * load (GSAP SplitText). Words start at 0.2 opacity rather than 0 so the headline is painted, and
 * counted for LCP, from the first frame. Reduced motion: the headline is simply there.
 */
export function HeroHeadline({ children }: { children: string }) {
  const ref = useRef<HTMLHeadingElement>(null);
  const allowed = useMotionAllowed();

  useGSAP(
    () => {
      if (!allowed || !ref.current) return;
      const split = SplitText.create(ref.current, { type: "words" });
      gsap.from(split.words, {
        y: 12,
        opacity: 0.2,
        duration: 0.5,
        ease: "power2.out",
        stagger: 0.03,
        onComplete: () => split.revert(),
      });
      return () => split.revert();
    },
    { dependencies: [allowed], scope: ref },
  );

  return (
    <h1 ref={ref} className="font-display text-5xl leading-[1.05] sm:text-6xl lg:text-7xl">
      {children}
    </h1>
  );
}
