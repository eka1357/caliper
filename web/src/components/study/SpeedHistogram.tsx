"use client";

import { Bar } from "@/components/charts/bar";
import { BarChart } from "@/components/charts/bar-chart";
import { BarXAxis } from "@/components/charts/bar-x-axis";
import { Grid } from "@/components/charts/grid";
import { ChartTooltip } from "@/components/charts/tooltip";
import { Placeholder } from "@/components/site/Placeholder";
import type { StudySummary } from "@/lib/types";
import { fmtKmh, fmtRange } from "./copy";

const BIN_KMH = 5;

/**
 * Histogram of measured speeds in 5 km/h bins. Bars at or above the limit are drawn in the
 * destructive colour (stacked series); the 85th percentile and the limit are labelled under it.
 */
export function SpeedHistogram({ summary }: { summary: StudySummary | null }) {
  if (!summary) {
    return (
      <Placeholder title="Speed histogram">
        Measured speeds in 5 km/h bins, with the 85th percentile and the speed limit marked. No
        study has been recorded yet.
      </Placeholder>
    );
  }
  const speeds = summary.readings
    .filter((r) => r.status === "measured" && r.speed_kmh != null)
    .map((r) => r.speed_kmh as number);
  if (speeds.length === 0) {
    return <p className="text-sm text-muted-foreground">No vehicle was measured.</p>;
  }
  const lo = Math.floor(Math.min(...speeds) / BIN_KMH) * BIN_KMH;
  const hi = Math.ceil((Math.max(...speeds) + 1e-9) / BIN_KMH) * BIN_KMH;
  const limit = summary.speed_limit_kmh;
  const data: Record<string, unknown>[] = [];
  for (let b = lo; b < hi; b += BIN_KMH) {
    const n = speeds.filter((s) => s >= b && s < b + BIN_KMH).length;
    const over = limit != null && b >= limit;
    data.push({ bin: `${b}–${b + BIN_KMH}`, under: over ? null : n, over: over ? n : null });
  }
  return (
    <figure className="flex min-w-0 flex-col gap-3 overflow-hidden rounded-lg border bg-card p-4">
      <figcaption className="text-sm font-medium">Measured speeds (km/h), vehicles per bin</figcaption>
      <BarChart data={data} xDataKey="bin" aspectRatio="5 / 2" stacked>
        <Grid horizontal />
        <Bar dataKey="under" fill="var(--track)" />
        <Bar dataKey="over" fill="var(--destructive)" />
        <BarXAxis showAllLabels />
        <ChartTooltip />
      </BarChart>
      <p className="font-mono text-xs tabular-nums text-muted-foreground">
        85th percentile {fmtKmh(summary.p85_kmh)} km/h (range {fmtRange(summary.p85_interval_90_kmh)})
        {limit != null && ` · limit ${fmtKmh(limit)} km/h, bins at or above it in red`}
      </p>
    </figure>
  );
}
