"use client";

import { Check, X } from "lucide-react";
import { useEffect, useRef } from "react";
import { PlaceholderTag } from "@/components/site/Placeholder";
import type { CachedRun, OverlayFrame } from "@/lib/types";
import { cn } from "@/lib/utils";
import { LazyInView } from "./LazyInView";
import { LazyPositionChart } from "./lazy-charts";
import { useGsapLib } from "./motion-lib";
import { useMedia, useMotionAllowed } from "./motion-pref";

const SPEC_KEYS = [
  "target_phrase", "reference_phrase", "reference_value_si", "quantity", "statistic",
  "timestamp_s", "output_unit",
] as const;

function midFrame(frames: OverlayFrame[]): OverlayFrame | null {
  const withBoth = frames.filter((f) => f.target && f.reference);
  return withBoth[Math.floor(withBoth.length / 2)] ?? frames[0] ?? null;
}

/**
 * "How it works": four steps with real artifacts from one recorded run. On wide screens with
 * motion allowed the section pins and the steps advance with scroll (ScrollTrigger, scrub 0.6).
 * Otherwise the four steps are a plain grid: same content, no scroll scene.
 */
export function HowItWorks({ run }: { run: CachedRun }) {
  const allowed = useMotionAllowed();
  const root = useRef<HTMLDivElement>(null);
  const wide = useMedia("(min-width: 1024px)");
  const lib = useGsapLib();
  const scene = allowed && wide && lib != null;
  const r = run.result;
  const o = run.overlay;
  const f = midFrame(o.frames ?? []);
  const w = o.width ?? 640;
  const h = o.height ?? 360;
  const spec = Object.fromEntries(SPEC_KEYS.map((k) => [k, r.spec[k]]));

  const steps = [
    {
      name: "Read",
      line: "Muse Spark reads the question and writes a measurement spec. It never writes the number.",
      art: (
        <pre className="max-h-72 overflow-auto rounded-md bg-muted p-4 font-mono text-xs leading-relaxed" data-lenis-prevent>
          {JSON.stringify(spec, null, 2)}
        </pre>
      ),
    },
    {
      name: "Find",
      line: "SAM 3.1 tracks the target (cyan) and the scale reference (amber) in every frame.",
      art: (
        <div className="relative w-full overflow-hidden rounded-md border bg-muted" style={{ aspectRatio: `${w} / ${h}` }}>
          {run.meta.poster && (
            // eslint-disable-next-line @next/next/no-img-element -- recorded run asset, sized by its box
            <img src={`/runs/${encodeURIComponent(r.run_id)}/${run.meta.poster}`} alt="" className="absolute inset-0 h-full w-full" loading="lazy" />
          )}
          <svg viewBox={`0 0 ${w} ${h}`} className="absolute inset-0 h-full w-full" aria-hidden>
            {f?.reference && <path d={f.reference.path} fill="none" stroke="var(--primary)" strokeWidth={w / 260} />}
            {f?.target && <path d={f.target.path} fill="none" stroke="var(--track)" strokeWidth={w / 260} />}
          </svg>
        </div>
      ),
    },
    {
      name: "Measure",
      line: `Python sets the scale, fits the motion locally and bootstraps a 90% range. Method: ${r.method}.`,
      art: (
        <LazyInView minHeight={240}>
          <LazyPositionChart rows={o.fit ?? []} />
        </LazyInView>
      ),
    },
    {
      name: "Check",
      line: "Deterministic checks, then a visual audit. If any fails, Caliper refuses instead of guessing.",
      art: (
        <ul className="flex flex-col gap-2 text-sm">
          {r.checks.map((c) => (
            <li key={c.name} className="flex items-center gap-2">
              {c.passed ? (
                <Check className="size-4 shrink-0 text-success" aria-label="passed" />
              ) : (
                <X className="size-4 shrink-0 text-destructive" aria-label="failed" />
              )}
              <span className="min-w-0 break-words font-mono text-xs">{c.name}</span>
            </li>
          ))}
        </ul>
      ),
    },
  ];

  useEffect(() => {
    if (!scene || !lib || !root.current) return;
    const { gsap, ScrollTrigger } = lib;
    const ctx = gsap.context(() => {
        const panels = gsap.utils.toArray<HTMLElement>("[data-step]", root.current);
        const marks = gsap.utils.toArray<HTMLElement>("[data-mark]", root.current);
        gsap.set(panels.slice(1), { autoAlpha: 0, y: 16 });
        const tl = gsap.timeline({
          scrollTrigger: {
            trigger: root.current,
            pin: true,
            pinSpacing: true, // the parent is flex, where ScrollTrigger defaults it to false
            scrub: 0.6,
            start: "top top+=64",
            end: `+=${panels.length * 500}`,
          },
        });
        panels.forEach((p, i) => {
          if (i === 0) return;
          tl.to(panels[i - 1], { autoAlpha: 0, y: -16, duration: 1 })
            .to(marks[i - 1], { color: "var(--muted-foreground)", duration: 0.2 }, "<")
            .to(p, { autoAlpha: 1, y: 0, duration: 1 }, "<0.3")
            .to(marks[i], { color: "var(--foreground)", duration: 0.2 }, "<");
        });
      });
    ScrollTrigger.refresh();
    return () => ctx.revert();
  }, [scene, lib]);

  return (
    <div ref={root} className="flex flex-col gap-8">
      <div className="flex flex-wrap items-center gap-3">
        <ol className="flex flex-wrap gap-x-6 gap-y-2 font-mono text-sm" aria-label="Steps">
          {steps.map((s, i) => (
            <li key={s.name} data-mark className={cn(scene && i > 0 ? "text-muted-foreground" : "text-foreground")}>
              {i + 1}. {s.name}
            </li>
          ))}
        </ol>
        {run.meta.placeholder && <PlaceholderTag />}
      </div>
      <div className={cn("grid gap-6", scene ? "grid-cols-1" : "grid-cols-1 md:grid-cols-2")}>
        {steps.map((s, i) => (
          <article
            key={s.name}
            data-step
            className={cn(
              "grid min-w-0 grid-cols-1 gap-4 rounded-lg border bg-card p-5",
              scene && "[grid-area:1/1] lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)] lg:items-center",
            )}
          >
            <div className="flex flex-col gap-2">
              <h3 className="text-xl font-medium">
                <span className="font-mono text-muted-foreground">{i + 1}.</span> {s.name}
              </h3>
              <p className="text-muted-foreground">{s.line}</p>
            </div>
            <div className="min-w-0">{s.art}</div>
          </article>
        ))}
      </div>
    </div>
  );
}
