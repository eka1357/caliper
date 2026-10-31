"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { PlaceholderTag } from "@/components/site/Placeholder";
import { decimalsFor, fmt } from "@/lib/format";
import type { CachedRun, OverlayFrame } from "@/lib/types";
import { Decrypt } from "./Decrypt";
import { gsap, useGSAP } from "./gsap";
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
  const [frame, setFrame] = useState(0);
  const o = run.overlay;
  const w = o.width ?? 640;
  const h = o.height ?? 360;
  const fps = o.fps ?? 30;
  const frames = useMemo(() => o.frames ?? [], [o.frames]);
  const trajectory = useMemo(() => {
    const pts = frames.filter((f) => f.target).map((f) => f.target!.centroid);
    return pts.length > 1 ? `M${pts.map((p) => `${p[0].toFixed(1)} ${p[1].toFixed(1)}`).join(" L")}` : "";
  }, [frames]);
  const current = frameAt(frames, frame);
  const r = run.result;
  const base = `/runs/${encodeURIComponent(r.run_id)}/`;

  // Outlines follow presented frames (requestVideoFrameCallback), never timeupdate.
  useEffect(() => {
    const v = video.current;
    if (!v) return;
    let id = 0;
    const tick = (_: number, meta: VideoFrameCallbackMetadata) => {
      setFrame(Math.round(meta.mediaTime * fps));
      id = v.requestVideoFrameCallback(tick);
    };
    id = v.requestVideoFrameCallback(tick);
    return () => v.cancelVideoFrameCallback(id);
  }, [fps]);

  // Reduced motion: no autoplay loop; the poster frame with the full trajectory stays put.
  useEffect(() => {
    const v = video.current;
    if (!v) return;
    if (allowed) void v.play().catch(() => undefined);
    else v.pause();
  }, [allowed]);

  useGSAP(
    () => {
      if (!allowed || !path.current || !box.current) return;
      gsap.fromTo(
        path.current,
        { drawSVG: "0% 15%" },
        {
          drawSVG: "0% 100%",
          ease: "none",
          scrollTrigger: { trigger: box.current, start: "top 70%", end: "bottom 20%", scrub: true },
        },
      );
    },
    { dependencies: [allowed, trajectory] },
  );

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
          preload="metadata"
          aria-label="Recorded run with the measured object outlined"
        />
        <svg viewBox={`0 0 ${w} ${h}`} className="absolute inset-0 h-full w-full" aria-hidden>
          {trajectory && (
            <path ref={path} d={trajectory} fill="none" stroke="var(--track)" strokeWidth={w / 320}
              strokeLinecap="round" opacity={0.8} />
          )}
          {current?.reference && (
            <path d={current.reference.path} fill="none" stroke="var(--primary)" strokeWidth={w / 260} />
          )}
          {current?.target && (
            <path d={current.target.path} fill="none" stroke="var(--track)" strokeWidth={w / 260} />
          )}
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
