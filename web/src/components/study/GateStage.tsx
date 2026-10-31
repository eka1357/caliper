"use client";

import { useEffect, useRef, useState } from "react";
import type { GateLine, StudyOverlay, VehicleReading } from "@/lib/types";
import { fmtKmh, fmtRange, STUDY_COPY } from "./copy";

export type Gates = [GateLine, GateLine];

export function defaultGates(w: number, h: number): Gates {
  return [
    [[w * 0.35, h * 0.15], [w * 0.35, h * 0.85]],
    [[w * 0.65, h * 0.15], [w * 0.65, h * 0.85]],
  ];
}

const LABEL_WINDOW_S = 0.4;

interface GateStageProps {
  src: string | null;
  poster: string | null;
  gates: Gates | null;
  onGates?: (g: Gates) => void;
  onSize?: (w: number, h: number) => void;
  overlay: StudyOverlay | null;
  readings: VehicleReading[];
}

/**
 * Video stage for the study: the first frame with two draggable gate lines while setting up,
 * then playback with each vehicle outlined as it crosses a gate, with its speed label.
 */
export function GateStage({ src, poster, gates, onGates, onSize, overlay, readings }: GateStageProps) {
  const video = useRef<HTMLVideoElement>(null);
  const box = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState<[number, number]>([
    overlay?.width ?? 1280,
    overlay?.height ?? 720,
  ]);
  const [t, setT] = useState(0);
  const editable = !!onGates;
  const [w, h] = size;

  useEffect(() => {
    const v = video.current;
    if (!v || editable) return;
    let id = 0;
    const tick = (_: number, meta: VideoFrameCallbackMetadata) => {
      setT(meta.mediaTime);
      id = v.requestVideoFrameCallback(tick);
    };
    id = v.requestVideoFrameCallback(tick);
    return () => v.cancelVideoFrameCallback(id);
  }, [editable, src]);

  const toVideo = (clientX: number, clientY: number): [number, number] => {
    const r = box.current!.getBoundingClientRect();
    const x = ((clientX - r.left) / r.width) * w;
    const y = ((clientY - r.top) / r.height) * h;
    return [Math.min(w, Math.max(0, x)), Math.min(h, Math.max(0, y))];
  };

  const move = (gi: 0 | 1, pi: 0 | 1, p: [number, number]) => {
    if (!gates || !onGates) return;
    const next: Gates = [
      [[...gates[0][0]], [...gates[0][1]]],
      [[...gates[1][0]], [...gates[1][1]]],
    ];
    next[gi][pi] = p;
    onGates(next);
  };

  const fps = overlay?.fps ?? 30;
  const byId = new Map(readings.map((r) => [r.vehicle_id, r]));
  const visible = editable
    ? []
    : (overlay?.vehicles ?? []).flatMap((v) =>
        v.crossings
          .filter((c) => Math.abs(c.frame / fps - t) <= LABEL_WINDOW_S)
          .slice(0, 1)
          .map((c) => ({ c, r: byId.get(v.vehicle_id) ?? null, id: v.vehicle_id })),
      );
  const recorded: Gates | null =
    overlay?.gate_a && overlay.gate_b ? [overlay.gate_a, overlay.gate_b] : null;
  const shown = editable ? gates : (recorded ?? gates);
  const unit = w / 100;

  return (
    <div
      ref={box}
      className="relative w-full overflow-hidden rounded-lg border bg-muted [background-image:linear-gradient(var(--border)_1px,transparent_1px),linear-gradient(90deg,var(--border)_1px,transparent_1px)] [background-size:24px_24px]"
      style={{ aspectRatio: `${w} / ${h}` }}
    >
      {src ? (
        <video
          ref={video}
          src={src}
          poster={poster ?? undefined}
          className="absolute inset-0 h-full w-full"
          muted
          playsInline
          preload="auto"
          controls={!editable}
          onLoadedMetadata={(e) => {
            const v = e.currentTarget;
            if (v.videoWidth && v.videoHeight) {
              setSize([v.videoWidth, v.videoHeight]);
              onSize?.(v.videoWidth, v.videoHeight);
            }
            if (editable) v.currentTime = 0;
          }}
        />
      ) : (
        <p className="absolute inset-0 flex items-center justify-center p-6 text-center text-sm text-muted-foreground">
          {STUDY_COPY.guide}
        </p>
      )}
      {src && (
        <svg
          viewBox={`0 0 ${w} ${h}`}
          preserveAspectRatio="none"
          className="pointer-events-none absolute inset-0 h-full w-full"
        >
          {visible.map(({ c, r, id }) => {
            const measured = r?.status === "measured";
            const color = measured ? "var(--track)" : "var(--muted-foreground)";
            return (
              <g key={id} className="pointer-events-auto">
                {r?.reason && <title>{r.reason}</title>}
                <path d={c.path} fill="none" stroke={color} strokeWidth={unit * 0.25} />
                <text
                  x={c.anchor[0]}
                  y={c.anchor[1]}
                  fill={color}
                  fontSize={unit * 1.6}
                  className="font-mono"
                  paintOrder="stroke"
                  stroke="var(--background)"
                  strokeWidth={unit * 0.25}
                >
                  {measured && r
                    ? `${fmtKmh(r.speed_kmh)} km/h (${fmtRange(r.interval_90_kmh)})`
                    : STUDY_COPY.noReading}
                </text>
              </g>
            );
          })}
          {shown?.map((g, gi) => (
            <g key={gi}>
              <line
                x1={g[0][0]}
                y1={g[0][1]}
                x2={g[1][0]}
                y2={g[1][1]}
                stroke="var(--primary)"
                strokeWidth={unit * 0.3}
                strokeDasharray={`${unit} ${unit * 0.6}`}
              />
              <text
                x={g[0][0] + unit}
                y={Math.max(unit * 2, g[0][1] - unit)}
                fill="var(--primary)"
                fontSize={unit * 1.8}
                className="font-mono"
                paintOrder="stroke"
                stroke="var(--background)"
                strokeWidth={unit * 0.25}
              >
                {gi === 0 ? "A" : "B"}
              </text>
              {editable &&
                g.map((p, pi) => (
                  <circle
                    key={pi}
                    cx={p[0]}
                    cy={p[1]}
                    r={unit * 1.4}
                    fill="var(--primary)"
                    stroke="var(--background)"
                    strokeWidth={unit * 0.3}
                    tabIndex={0}
                    role="button"
                    aria-label={`Gate ${gi === 0 ? "A" : "B"}, ${pi === 0 ? "first" : "second"} end. Drag it, or use the arrow keys.`}
                    className="pointer-events-auto cursor-grab touch-none outline-none focus-visible:stroke-foreground"
                    onPointerDown={(e) => e.currentTarget.setPointerCapture(e.pointerId)}
                    onPointerMove={(e) => {
                      if (e.currentTarget.hasPointerCapture(e.pointerId))
                        move(gi as 0 | 1, pi as 0 | 1, toVideo(e.clientX, e.clientY));
                    }}
                    onKeyDown={(e) => {
                      const step = (e.shiftKey ? 5 : 1) * unit;
                      const d: Record<string, [number, number]> = {
                        ArrowLeft: [-step, 0],
                        ArrowRight: [step, 0],
                        ArrowUp: [0, -step],
                        ArrowDown: [0, step],
                      };
                      const dd = d[e.key];
                      if (!dd) return;
                      e.preventDefault();
                      move(gi as 0 | 1, pi as 0 | 1, [
                        Math.min(w, Math.max(0, p[0] + dd[0])),
                        Math.min(h, Math.max(0, p[1] + dd[1])),
                      ]);
                    }}
                  />
                ))}
            </g>
          ))}
        </svg>
      )}
    </div>
  );
}
