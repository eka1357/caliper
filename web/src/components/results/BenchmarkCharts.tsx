"use client";

import { useId, useState } from "react";
import { Bar } from "@/components/charts/bar";
import { BarChart } from "@/components/charts/bar-chart";
import { BarXAxis } from "@/components/charts/bar-x-axis";
import { Grid } from "@/components/charts/grid";
import { ChartTooltip } from "@/components/charts/tooltip";
import {
  CATEGORY_NOTE,
  SPLIT_NOTE,
  splitLabel,
  VARIANT_COLOR,
  variantLabel,
  variantShort,
} from "@/lib/labels";
import type { PairedRow, ResultRow } from "@/lib/results";
import { cn } from "@/lib/utils";

const CATS = ["S2", "D2", "S3", "D3"] as const;
const pct = (v: number | null) => (v == null ? null : Math.round(v * 1000) / 10);
const label = (v: number) => v.toFixed(1);

/** Variant charts for one split at a time, with tabs over the splits that have rows. */
export function SplitCharts({
  rows,
  splits,
  initial,
}: {
  rows: ResultRow[];
  splits: string[];
  initial: string;
}) {
  const [split, setSplit] = useState(initial);
  const id = useId();
  const inSplit = rows.filter((r) => r.split === split);
  const hasCaliper = inSplit.some((r) => r.variant.startsWith("caliper"));

  return (
    <section aria-labelledby={`${id}-h`} className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <h2 id={`${id}-h`} className="text-xl font-medium">
          MRA by variant
        </h2>
        <p className="text-sm text-muted-foreground">
          Official MRA counts an abstention as a miss. Answered-only MRA scores just the questions a
          variant answered. Scale 0 to 100, higher is better.
        </p>
      </div>
      <div role="tablist" aria-label="Split" className="flex flex-wrap gap-1">
        {splits.map((s) => (
          <button
            key={s}
            role="tab"
            type="button"
            id={`${id}-tab-${s}`}
            aria-selected={s === split}
            aria-controls={`${id}-panel`}
            onClick={() => setSplit(s)}
            className={cn(
              "rounded-md border px-3 py-1.5 text-sm transition-colors focus-visible:outline-2 focus-visible:outline-ring",
              s === split ? "bg-muted text-foreground" : "text-muted-foreground hover:text-foreground",
            )}
          >
            {splitLabel(s)}
          </button>
        ))}
      </div>
      <div id={`${id}-panel`} role="tabpanel" aria-labelledby={`${id}-tab-${split}`}
        className="flex flex-col gap-6">
        <p className="text-sm">
          {SPLIT_NOTE[split] ?? ""}
          {!hasCaliper && (
            <span className="text-muted-foreground"> Caliper has no row on this split yet.</span>
          )}
        </p>
        <div className="grid min-w-0 grid-cols-1 gap-6 xl:grid-cols-2">
          <VariantChart rows={inSplit} />
          <CategoryChart rows={inSplit} />
        </div>
      </div>
    </section>
  );
}

function Legend({ items }: { items: { label: string; color: string; dashed?: boolean }[] }) {
  return (
    <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
      {items.map((i) => (
        <li key={i.label} className="flex items-center gap-1.5">
          <span
            aria-hidden
            className={cn("size-2.5 rounded-sm", i.dashed && "border border-dashed")}
            style={{ background: i.color }}
          />
          {i.label}
        </li>
      ))}
    </ul>
  );
}

function VariantChart({ rows }: { rows: ResultRow[] }) {
  // A blank value stays null: bklit skips non-numbers, so no bar is drawn and the label says n/a.
  const data = rows.map((r) => ({
    variant: [
      variantShort(r.variant),
      r.mra_average == null ? "(official n/a)" : "",
      r.mra_answered == null ? "(answered n/a)" : "",
    ].filter(Boolean).join(" "),
    official: pct(r.mra_average),
    answered: pct(r.mra_answered),
  }));
  const blanks = rows.filter((r) => r.mra_average == null || r.mra_answered == null);
  const usable = rows.filter((r) => r.mra_average != null || r.mra_answered != null);
  return (
    <figure className="flex min-w-0 flex-col gap-3 overflow-hidden rounded-lg border bg-card p-4">
      <figcaption className="flex flex-col gap-2">
        <span className="text-sm font-medium">Official and answered-only MRA</span>
        <span className="text-xs text-muted-foreground">
          {rows.map((r) => `${variantShort(r.variant)} = ${variantLabel(r.variant)}`).join("; ")}
        </span>
        <Legend
          items={[
            { label: "Official MRA", color: "var(--primary)" },
            { label: "Answered-only MRA", color: "var(--track)" },
          ]}
        />
      </figcaption>
      {usable.length === 0 ? (
        <p className="text-sm text-muted-foreground">No rows.</p>
      ) : (
        <BarChart data={data} xDataKey="variant" aspectRatio="16 / 9" barGap={0.3}>
          <Grid horizontal />
          <Bar dataKey="official" fill="var(--primary)" showValue valueLabelFormatter={label} />
          <Bar dataKey="answered" fill="var(--track)" showValue valueLabelFormatter={label} />
          <BarXAxis showAllLabels />
          <ChartTooltip />
        </BarChart>
      )}
      {blanks.length > 0 && (
        <p className="text-xs text-muted-foreground">
          n/a means the CSV has no value, so no bar is drawn. The 2D-only and 3D-only splits have no
          official all-category MRA.
        </p>
      )}
    </figure>
  );
}

function CategoryChart({ rows }: { rows: ResultRow[] }) {
  const cats = CATS.filter((c) => rows.some((r) => r[`mra_${c}`] != null));
  const variants = rows.filter((r) => cats.some((c) => r[`mra_${c}`] != null));
  const data = cats.map((c) => {
    const d: Record<string, unknown> = { category: c };
    for (const r of variants) d[r.variant] = pct(r[`mra_${c}`]);
    return d;
  });
  const naCats = variants.flatMap((r) =>
    cats.filter((c) => r[`mra_${c}`] == null).map((c) => `${variantLabel(r.variant)} ${c}`),
  );
  return (
    <figure className="flex min-w-0 flex-col gap-3 overflow-hidden rounded-lg border bg-card p-4">
      <figcaption className="flex flex-col gap-2">
        <span className="text-sm font-medium">Official MRA by category</span>
        <Legend
          items={variants.map((r) => ({
            label: variantLabel(r.variant),
            color: VARIANT_COLOR[r.variant] ?? "var(--chart-5)",
          }))}
        />
      </figcaption>
      {cats.length === 0 ? (
        <p className="text-sm text-muted-foreground">No per-category rows on this split.</p>
      ) : (
        <BarChart data={data} xDataKey="category" aspectRatio="16 / 9" barGap={0.25}>
          <Grid horizontal />
          {variants.map((r) => (
            <Bar key={r.variant} dataKey={r.variant}
              fill={VARIANT_COLOR[r.variant] ?? "var(--chart-5)"} />
          ))}
          <BarXAxis showAllLabels />
          <ChartTooltip />
        </BarChart>
      )}
      <p className="text-xs text-muted-foreground">
        {cats.map((c) => `${c}: ${CATEGORY_NOTE[c]}`).join(". ")}.
        {naCats.length > 0 && ` No bar (n/a): ${naCats.join("; ")}.`}
      </p>
    </figure>
  );
}

/** Like-for-like: each Caliper variant against Muse Spark alone on exactly the questions it answered. */
export function PairedChart({ rows }: { rows: PairedRow[] }) {
  const usable = rows.filter((r) => r.category === "all" && r.n_answered > 0);
  const data = usable.map((r) => ({
    pair: `${variantShort(r.variant)} · ${splitLabel(r.split)}`,
    caliper: pct(r.mra_variant),
    muse: pct(r.mra_muse),
  }));
  return (
    <figure className="flex min-w-0 flex-col gap-3 overflow-hidden rounded-lg border bg-card p-4">
      <figcaption className="flex flex-col gap-2">
        <span className="text-sm font-medium">
          Answered-only MRA: Caliper and Muse Spark alone on the same questions
        </span>
        <Legend
          items={[
            { label: "Caliper variant", color: "var(--primary)" },
            { label: "Muse Spark alone, same questions", color: "var(--muted-foreground)", dashed: true },
          ]}
        />
      </figcaption>
      <BarChart data={data} xDataKey="pair" aspectRatio="3 / 1" barGap={0.3}>
        <Grid horizontal />
        <Bar dataKey="caliper" fill="var(--primary)" showValue valueLabelFormatter={label} />
        <Bar dataKey="muse" fill="var(--muted-foreground)" fadedOpacity={0.6} showValue
          valueLabelFormatter={label} />
        <BarXAxis showAllLabels />
        <ChartTooltip />
      </BarChart>
      <p className="text-xs text-muted-foreground">
        Questions answered (n): {usable.map((r) => `${variantShort(r.variant)} · ${splitLabel(r.split)} n=${r.n_answered}`).join("; ")}.
        Small n means a wide margin of error. {usable.map((r) => `${variantShort(r.variant)} = ${variantLabel(r.variant)}`).filter((v, i, a) => a.indexOf(v) === i).join("; ")}.
      </p>
    </figure>
  );
}
