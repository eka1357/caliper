"use client";

import { Grid } from "@/components/charts/grid";
import { Line } from "@/components/charts/line";
import { LineChart } from "@/components/charts/line-chart";
import { XAxis } from "@/components/charts/x-axis";
import type { FitRow, SpeedRow } from "@/lib/types";

// bklit's line chart is a time-series chart: x must be a Date. Clip seconds are passed as
// epoch milliseconds and the axis gets explicit "x.xx s" labels instead of dates.
const toDate = (t: number) => new Date(Math.round(t * 1000));

function labels(ts: number[]): string[] {
  return ts.map((t) => `${t.toFixed(2)} s`);
}

export function PositionChart({ rows }: { rows: FitRow[] }) {
  if (rows.length < 2) return <Empty />;
  const data = rows.map((r) => ({ date: toDate(r.t_s), pos: r.pos_m, fit: r.fit_m }));
  return (
    <figure className="flex min-w-0 flex-col gap-2 overflow-hidden">
      <figcaption className="text-sm text-muted-foreground">
        Position along the motion (m): <span className="text-track">measured</span>,{" "}
        <span className="text-primary">local fit</span>
      </figcaption>
      <LineChart data={data} aspectRatio="5 / 2">
        <Grid horizontal />
        <Line dataKey="pos" stroke="var(--track)" strokeWidth={1.5} fadeEdges={false} />
        <Line dataKey="fit" stroke="var(--primary)" strokeWidth={2} fadeEdges={false} />
        <XAxis numTicks={4} labels={labels(rows.map((r) => r.t_s))} />
      </LineChart>
    </figure>
  );
}

export function SpeedChart({ rows }: { rows: SpeedRow[] }) {
  if (rows.length < 2) return <Empty />;
  const data = rows.map((r) => ({ date: toDate(r.t_s), speed: r.speed_m_s }));
  return (
    <figure className="flex min-w-0 flex-col gap-2 overflow-hidden">
      <figcaption className="text-sm text-muted-foreground">Speed over time (m/s)</figcaption>
      <LineChart data={data} aspectRatio="5 / 2">
        <Grid horizontal />
        <Line dataKey="speed" stroke="var(--track)" strokeWidth={2} fadeEdges={false} />
        <XAxis numTicks={4} labels={labels(rows.map((r) => r.t_s))} />
      </LineChart>
    </figure>
  );
}

function Empty() {
  return <p className="text-sm text-muted-foreground">No fit for this run.</p>;
}
