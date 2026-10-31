"use client";

import { useEffect, useRef, useState } from "react";

/**
 * Mounts its children only when they come near the viewport, so charts below the fold do not
 * render or animate during page load. The box keeps `minHeight` until then (no layout shift).
 */
export function LazyInView({ children, minHeight }: { children: React.ReactNode; minHeight: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const [show, setShow] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(
      ([e]) => {
        if (e?.isIntersecting) {
          setShow(true);
          io.disconnect();
        }
      },
      { rootMargin: "300px 0px" },
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);
  return (
    <div ref={ref} style={show ? undefined : { minHeight }} className="min-w-0">
      {show ? children : null}
    </div>
  );
}
