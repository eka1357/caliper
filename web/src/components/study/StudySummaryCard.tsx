import { Placeholder } from "@/components/site/Placeholder";
import type { StudySummary } from "@/lib/types";
import { cn } from "@/lib/utils";
import { fmtKmh, fmtRange, STUDY_COPY } from "./copy";

/** Summary card: counts, median, the 85th percentile with its range, share over the limit. */
export function StudySummaryCard({ summary, className }: { summary: StudySummary | null; className?: string }) {
  if (!summary) {
    return (
      <Placeholder title="Study summary" className={className}>
        <p>{STUDY_COPY.noStudy}</p>
        <p className="mt-2">
          A study shows vehicles seen, measured and with no reading; the median speed; the
          85th-percentile speed with its 90% range; and the share over the limit you enter.
        </p>
      </Placeholder>
    );
  }
  const s = summary;
  const noReading = s.vehicles_seen - s.vehicles_measured;
  return (
    <section
      aria-label="Study summary"
      className={cn("flex flex-col gap-4 rounded-lg border bg-card p-5", className)}
    >
      <dl className="grid grid-cols-3 gap-3 text-sm">
        <Stat label="Vehicles seen" value={String(s.vehicles_seen)} />
        <Stat label="Measured" value={String(s.vehicles_measured)} />
        <Stat label="No reading" value={String(noReading)} />
      </dl>
      <div className="flex flex-col gap-1">
        <p className="text-sm text-muted-foreground">85th-percentile speed</p>
        <p className="font-mono text-[3.5rem] leading-none tabular-nums">
          {fmtKmh(s.p85_kmh)}
          <span className="ml-2 text-xl text-muted-foreground">km/h</span>
        </p>
        <p className="font-mono text-sm tabular-nums text-muted-foreground">
          90% range {fmtRange(s.p85_interval_90_kmh)} km/h
        </p>
      </div>
      <dl className="grid grid-cols-2 gap-3 text-sm">
        <Stat label="Median" value={`${fmtKmh(s.median_kmh)} km/h`} />
        <Stat
          label={s.speed_limit_kmh != null ? `Over ${fmtKmh(s.speed_limit_kmh)} km/h` : "Over the limit"}
          value={s.share_over_limit != null ? `${Math.round(s.share_over_limit * 100)}%` : "no limit given"}
        />
      </dl>
      <p className="text-xs text-muted-foreground">
        Gates {s.gate_distance_m} m apart · {Math.round(s.duration_s)} s of video
      </p>
    </section>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex min-w-0 flex-col gap-0.5">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="font-mono tabular-nums">{value}</dd>
    </div>
  );
}
