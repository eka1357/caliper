"use client";

import { ChevronLeft, ChevronRight, Pause, Play } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { outlineFade } from "@/lib/motion";
import type { Overlay, OverlayFrame } from "@/lib/types";
import { cn } from "@/lib/utils";

interface VideoStageProps {
  src: string | null;
  poster: string | null;
  overlay: Overlay | null;
  /** Fit window in seconds, shaded on the scrubber. */
  fitWindow: [number, number] | null;
  /** Seek requests from outside (audit keyframes); `n` changes on every request. */
  seekTo: { frame: number; n: number } | null;
}

type Layer = "target" | "reference" | "trajectory";

/** Latest overlay frame at or before `frame` (outlines hold until the next sampled frame). */
function frameAt(frames: OverlayFrame[], frame: number): OverlayFrame | null {
  let lo = 0;
  let hi = frames.length - 1;
  let best: OverlayFrame | null = null;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    if (frames[mid].frame <= frame) {
      best = frames[mid];
      lo = mid + 1;
    } else hi = mid - 1;
  }
  return best;
}

export function VideoStage({ src, poster, overlay, fitWindow, seekTo }: VideoStageProps) {
  const video = useRef<HTMLVideoElement>(null);
  const [time, setTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [layers, setLayers] = useState<Record<Layer, boolean>>({
    target: true,
    reference: true,
    trajectory: true,
  });
  const fps = overlay?.fps ?? 30;
  const frames = useMemo(() => overlay?.frames ?? [], [overlay]);
  const current = frameAt(frames, Math.round(time * fps));

  // Sync to presented frames, not to timeupdate (ARCHITECTURE section 11).
  useEffect(() => {
    const v = video.current;
    if (!v || !("requestVideoFrameCallback" in v)) return;
    let handle = 0;
    const tick: VideoFrameRequestCallback = (_, meta) => {
      setTime(meta.mediaTime);
      handle = v.requestVideoFrameCallback(tick);
    };
    handle = v.requestVideoFrameCallback(tick);
    return () => v.cancelVideoFrameCallback(handle);
  }, [src]);

  const seek = useCallback((t: number) => {
    const v = video.current;
    if (!v) return;
    v.currentTime = Math.max(0, Math.min(t, v.duration || t));
    setTime(v.currentTime);
  }, []);

  const toggle = () => {
    const v = video.current;
    if (!v) return;
    if (v.paused) void v.play();
    else v.pause();
  };

  useEffect(() => {
    if (!seekTo) return;
    const v = video.current;
    v?.pause();
    seek((seekTo.frame + 0.5) / fps); // middle of the frame, so the browser shows that frame
  }, [seekTo, seek, fps]);

  const trajectory = useMemo(() => {
    const upTo = Math.round(time * fps);
    return frames
      .filter((f) => f.target && f.frame <= upTo)
      .map((f) => f.target!.centroid.join(","))
      .join(" ");
  }, [frames, time, fps]);

  const w = overlay?.width ?? 16;
  const h = overlay?.height ?? 9;

  return (
    <section aria-label="Video" className="flex flex-col gap-3">
      <div className="measure-grid relative aspect-video w-full overflow-hidden rounded-lg border bg-card">
        {src ? (
          <video
            ref={video}
            src={src}
            poster={poster ?? undefined}
            className="absolute inset-0 size-full object-contain"
            muted
            playsInline
            loop
            preload="metadata"
            onLoadedMetadata={(e) => setDuration(e.currentTarget.duration)}
            onPlay={() => setPlaying(true)}
            onPause={() => setPlaying(false)}
            onSeeked={(e) => setTime(e.currentTarget.currentTime)}
          />
        ) : null}
        {overlay && frames.length > 0 && (
          <svg
            viewBox={`0 0 ${w} ${h}`}
            preserveAspectRatio="xMidYMid meet"
            className="pointer-events-none absolute inset-0 size-full"
            aria-hidden
          >
            <AnimatePresence>
              {layers.trajectory && trajectory && (
                <motion.polyline
                  key="trajectory"
                  points={trajectory}
                  fill="none"
                  stroke="var(--track)"
                  strokeOpacity={0.6}
                  strokeWidth={1.5}
                  strokeDasharray="4 3"
                  vectorEffect="non-scaling-stroke"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={outlineFade}
                />
              )}
              {layers.reference && current?.reference && (
                <motion.path
                  key="reference"
                  d={current.reference.path}
                  fill="none"
                  stroke="var(--primary)"
                  strokeWidth={2}
                  vectorEffect="non-scaling-stroke"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={outlineFade}
                />
              )}
              {layers.target && current?.target && (
                <motion.path
                  key="target"
                  d={current.target.path}
                  fill="none"
                  stroke="var(--track)"
                  strokeWidth={2}
                  vectorEffect="non-scaling-stroke"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={outlineFade}
                />
              )}
            </AnimatePresence>
          </svg>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Button variant="outline" size="icon" onClick={toggle} disabled={!src}
          aria-label={playing ? "Pause" : "Play"}>
          {playing ? <Pause /> : <Play />}
        </Button>
        <Button variant="outline" size="icon" onClick={() => seek(time - 1 / fps)} disabled={!src}
          aria-label="Previous frame">
          <ChevronLeft />
        </Button>
        <Button variant="outline" size="icon" onClick={() => seek(time + 1 / fps)} disabled={!src}
          aria-label="Next frame">
          <ChevronRight />
        </Button>
        <Scrubber time={time} duration={duration} fps={fps} fitWindow={fitWindow} onSeek={seek} />
        <span className="font-mono tabular ml-auto w-20 text-right text-sm text-muted-foreground">
          {time.toFixed(2)} s
        </span>
      </div>

      <div className="flex flex-wrap gap-2" role="group" aria-label="Overlays">
        <LayerToggle label="Target" swatch="bg-track" on={layers.target}
          onClick={() => setLayers((l) => ({ ...l, target: !l.target }))} />
        <LayerToggle label="Reference" swatch="bg-primary" on={layers.reference}
          onClick={() => setLayers((l) => ({ ...l, reference: !l.reference }))} />
        <LayerToggle label="Trajectory" swatch="bg-track/60" on={layers.trajectory}
          onClick={() => setLayers((l) => ({ ...l, trajectory: !l.trajectory }))} />
      </div>
    </section>
  );
}

function Scrubber({
  time,
  duration,
  fps,
  fitWindow,
  onSeek,
}: {
  time: number;
  duration: number;
  fps: number;
  fitWindow: [number, number] | null;
  onSeek: (t: number) => void;
}) {
  const max = duration || 1;
  const pct = (t: number) => `${(Math.max(0, Math.min(t, max)) / max) * 100}%`;
  return (
    <div className="relative order-last basis-full py-2 sm:order-none sm:basis-0 sm:flex-1">
      {fitWindow && duration > 0 && (
        <div
          className="absolute top-1/2 h-3 -translate-y-1/2 rounded-sm bg-track/25"
          style={{ left: pct(fitWindow[0]), width: `calc(${pct(fitWindow[1])} - ${pct(fitWindow[0])})` }}
          title="Fit window"
          aria-hidden
        />
      )}
      <Slider
        value={[Math.min(time, max)]}
        max={max}
        step={1 / fps}
        onValueChange={([t]) => onSeek(t)}
        aria-label="Scrub through the clip"
        disabled={duration === 0}
      />
    </div>
  );
}

function LayerToggle({
  label,
  swatch,
  on,
  onClick,
}: {
  label: string;
  swatch: string;
  on: boolean;
  onClick: () => void;
}) {
  return (
    <Button variant="outline" size="sm" aria-pressed={on} onClick={onClick}
      className={cn(!on && "text-muted-foreground")}>
      <span className={cn("size-2 rounded-full", swatch, !on && "opacity-30")} aria-hidden />
      {label}
    </Button>
  );
}
