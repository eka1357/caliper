"use client";

import { useEffect, useMemo, useRef } from "react";
import { PlaceholderTag } from "@/components/site/Placeholder";
import { decimalsFor, fmt } from "@/lib/format";
import type { CachedRun, OverlayFrame } from "@/lib/types";
import { Decrypt } from "./Decrypt";
import { useGsapLib } from "./motion-lib";
import { useMotionAllowed } from "./motion-pref";

function frameAt(frames: OverlayFrame[], frame: number): OverlayFrame | null {
  let best: OverlayFrame | null = null;
  for (const f of frames) {
    if (f.frame <= frame) best = f;
    else break;
  }
  return best;
}

/**
 * Hero visual: a looping muted clip from a recorded run, with the cyan target outline, the amber
 * reference outline, the trajectory and a small readout card, all from the run JSON.
 * Decorative effect 2 of 3: the trajectory draws as the hero scrolls away (DrawSVG + ScrollTrigger).
 */
export function HeroVisual({ run }: { run: CachedRun }) {
  const allowed = useMotionAllowed();
  const box = useRef<HTMLDivElement>(null);
  const video = useRef<HTMLVideoElement>(null);
  const path = useRef<SVGPathElement>(null);
  const targetPath = useRef<SVGPathElement>(null);
  const refPath = useRef<SVGPathElement>(null);
  const o = run.overlay;
  const w = o.width ?? 640;
  const h = o.height ?? 360;
  const fps = o.fps ?? 30;
  const frames = useMemo(() => o.frames ?? [], [o.frames]);
  const trajectory = useMemo(() => {
    const pts = frames.filter((f) => f.target).map((f) => f.target!.centroid);
    return pts.length > 1 ? `M${pts.map((p) => `${p[0].toFixed(1)} ${p[1].toFixed(1)}`).join(" L")}` : "";
  }, [frames]);
  const first = frameAt(frames, 0) ?? frames[0] ?? null;
  const r = run.result;
  const base = `/runs/${encodeURIComponent(r.run_id)}/`;

  // Outlines follow presented frames (requestVideoFrameCallback), never timeupdate. The paths
  // are updated on the DOM directly, so playback costs no React render per frame.
  useEffect(() => {
    const v = video.current;
    if (!v) return;
    let id = 0;
    let shown: OverlayFrame | null = null;
    const tick = (_: number, meta: VideoFrameCallbackMetadata) => {
      const f = frameAt(frames, Math.round(meta.mediaTime * fps));
      if (f !== shown) {
        shown = f;
        targetPath.current?.setAttribute("d", f?.target?.path ?? "");
        refPath.current?.setAttribute("d", f?.reference?.path ?? "");
      }
      id = v.requestVideoFrameCallback(tick);
    };
    id = v.requestVideoFrameCallback(tick);
    return () => v.cancelVideoFrameCallback(id);
  }, [fps, frames]);

  // The loop starts once the page has loaded and the main thread is idle, so it never competes
  // with the first paint. Reduced motion: no loop; the poster with the full trajectory stays.
  useEffect(() => {
    const v = video.current;
    if (!v) return;
    if (!allowed) {
      v.pause();
      return;
    }
    let idle = 0;
    const start = () => {
      idle = window.requestIdleCallback(() => void v.play().catch(() => undefined), { timeout: 3000 });
    };
    if (document.readyState === "complete") start();
    else window.addEventListener("load", start, { once: true });
    return () => {
      window.removeEventListener("load", start);
      window.cancelIdleCallback(idle);
    };
  }, [allowed]);

  const lib = useGsapLib();
  useEffect(() => {
    if (!allowed || !lib || !path.current || !box.current) return;
    const { gsap } = lib;
    const ctx = gsap.context(() => {
      gsap.fromTo(
        path.current,
        { drawSVG: "0% 15%" },
        {
          drawSVG: "0% 100%",
          ease: "none",
          scrollTrigger: { trigger: box.current, start: "top 70%", end: "bottom 20%", scrub: true },
        },
      );
    });
    return () => ctx.revert();
  }, [allowed, lib, trajectory]);

  const decimals = r.value != null ? decimalsFor(r.interval_90, r.value) : 2;
  return (
    <figure className="relative flex flex-col gap-3">
      <div
        ref={box}
        className="relative w-full overflow-hidden rounded-lg border bg-muted"
        style={{ aspectRatio: `${w} / ${h}` }}
      >
        <video
          ref={video}
          src={run.meta.clip ? base + run.meta.clip : undefined}
          poster={run.meta.poster ? base + run.meta.poster : undefined}
          className="absolute inset-0 h-full w-full"
          muted
          loop
          playsInline
          preload="none"
          aria-label="Recorded run with the measured object outlined"
        />
        <svg viewBox={`0 0 ${w} ${h}`} className="absolute inset-0 h-full w-full" aria-hidden>
          {trajectory && (
            <path ref={path} d={trajectory} fill="none" stroke="var(--track)" strokeWidth={w / 320}
              strokeLinecap="round" opacity={0.8} />
          )}
          <path ref={refPath} d={first?.reference?.path ?? ""} fill="none" stroke="var(--primary)" strokeWidth={w / 260} />
          <path ref={targetPath} d={first?.target?.path ?? ""} fill="none" stroke="var(--track)" strokeWidth={w / 260} />
        </svg>
        {run.meta.placeholder && <PlaceholderTag className="absolute left-3 top-3 bg-background/80" />}
        {r.status === "measured" && r.value != null && (
          <div className="absolute bottom-3 right-3 flex max-w-[70%] flex-col gap-0.5 rounded-lg border bg-card/95 px-3 py-2 sm:px-4 sm:py-3">
            <p className="text-xs text-primary">Measured</p>
            <p className="flex items-baseline gap-2">
              <Decrypt text={fmt(r.value, decimals)} className="font-mono text-2xl sm:text-3xl tabular-nums" />
              <span className="font-mono text-sm text-muted-foreground">{r.unit}</span>
            </p>
            {r.interval_90 && (
              <p className="font-mono text-xs tabular-nums text-muted-foreground">
                90% range {fmt(r.interval_90[0], decimals)} to {fmt(r.interval_90[1], decimals)}
              </p>
            )}
          </div>
        )}
      </div>
      <figcaption className="text-xs text-muted-foreground">
        {run.meta.placeholder
          ? "Placeholder: a synthetic test scene drawn by our own script. Our filmed field clip replaces it once it is measured."
          : run.meta.title}
      </figcaption>
    </figure>
  );
}
