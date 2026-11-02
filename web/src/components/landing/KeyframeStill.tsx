import { runAssetUrl } from "@/lib/run-assets";
import type { CachedRun, OverlayFrame } from "@/lib/types";

const MAX_H = 420; // px: portrait clips stay a sensible height in a card

/** A recorded run's poster with the target and reference outlines of one frame (static). */
export function KeyframeStill({ run, className }: { run: CachedRun; className?: string }) {
  const o = run.overlay;
  const w = o.width ?? 640;
  const h = o.height ?? 360;
  const frames: OverlayFrame[] = o.frames ?? [];
  const f = frames.filter((x) => x.target)[Math.floor(frames.length / 2)] ?? frames[0] ?? null;
  return (
    <div className={`relative mx-auto overflow-hidden rounded-md border bg-muted ${className ?? ""}`}
      style={{ aspectRatio: `${w} / ${h}`, width: `min(100%, ${Math.round((MAX_H * w) / h)}px)` }}>
      {run.meta.poster && (
        // eslint-disable-next-line @next/next/no-img-element -- recorded run asset, sized by its box
        <img src={runAssetUrl(run.result.run_id, run.meta.poster) ?? undefined} alt=""
          className="absolute inset-0 h-full w-full" loading="lazy" />
      )}
      <svg viewBox={`0 0 ${w} ${h}`} className="absolute inset-0 h-full w-full" aria-hidden>
        {f?.reference && <path d={f.reference.path} fill="none" stroke="var(--primary)" strokeWidth={w / 260} />}
        {f?.target && <path d={f.target.path} fill="none" stroke="var(--track)" strokeWidth={w / 260} />}
      </svg>
    </div>
  );
}
