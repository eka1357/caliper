"use client";

import { useEffect, useRef, useState } from "react";
import { useMotionAllowed } from "./motion-pref";

const GLYPHS = "0123456789";
const DURATION_MS = 900;

/**
 * Decorative effect 3 of 3: the digits scramble, then lock left to right onto the measured value
 * ("a guess turns into a measurement"). Written in-house in the spirit of React Bits
 * DecryptedText. The final text is in the DOM from the first paint and for screen readers;
 * with reduced motion nothing scrambles.
 */
export function Decrypt({ text, className }: { text: string; className?: string }) {
  const allowed = useMotionAllowed();
  const [shown, setShown] = useState(text);
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (!allowed || !ref.current) return;
    let raf = 0;
    let start = 0;
    const run = (now: number) => {
      if (!start) start = now;
      const p = Math.min(1, (now - start) / DURATION_MS);
      const locked = Math.floor(p * text.length);
      setShown(
        text
          .split("")
          .map((c, i) =>
            i < locked || !/\d/.test(c) ? c : GLYPHS[Math.floor(Math.random() * GLYPHS.length)],
          )
          .join(""),
      );
      if (p < 1) raf = requestAnimationFrame(run);
    };
    const io = new IntersectionObserver(
      ([e]) => {
        if (e?.isIntersecting) {
          io.disconnect();
          raf = requestAnimationFrame(run);
        }
      },
      { threshold: 0.6 },
    );
    io.observe(ref.current);
    return () => {
      io.disconnect();
      cancelAnimationFrame(raf);
    };
  }, [allowed, text]);

  return (
    <span ref={ref} className={className}>
      <span aria-hidden>{shown}</span>
      <span className="sr-only">{text}</span>
    </span>
  );
}
