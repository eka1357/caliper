"use client";

import { animate, motion, useMotionValue, useReducedMotion, useTransform } from "motion/react";
import { useEffect } from "react";
import { decimalsFor, fmt } from "@/lib/format";
import { intervalGrow, readout, reducedFade } from "@/lib/motion";

interface ReadoutProps {
  value: number;
  unit: string;
  interval: [number, number] | null;
}

/** The number is the hero: 3.5rem mono, counts up over 600 ms, then the interval bar grows. */
export function Readout({ value, unit, interval }: ReadoutProps) {
  const reduce = useReducedMotion();
  const decimals = decimalsFor(interval, value);
  const shown = useMotionValue(reduce ? value : 0);
  const text = useTransform(shown, (v) => fmt(v, decimals));

  useEffect(() => {
    if (reduce) {
      shown.set(value);
      return;
    }
    shown.set(0);
    const controls = animate(shown, value, readout);
    return () => controls.stop();
  }, [value, reduce, shown]);

  return (
    <div className="flex flex-col gap-3">
      <p className="flex items-baseline gap-2" aria-live="polite">
        <motion.span
          className="font-mono tabular text-[3.5rem] leading-none text-foreground"
          aria-hidden
        >
          {text}
        </motion.span>
        <span className="font-mono text-xl text-muted-foreground">{unit}</span>
        <span className="sr-only">
          {fmt(value, decimals)} {unit}
          {interval && `, 90% range ${fmt(interval[0], decimals)} to ${fmt(interval[1], decimals)}`}
        </span>
      </p>
      {interval && <IntervalBar value={value} interval={interval} decimals={decimals} />}
      {interval && (
        <p className="font-mono tabular text-sm text-muted-foreground" aria-hidden>
          90% range {fmt(interval[0], decimals)} to {fmt(interval[1], decimals)} {unit}
        </p>
      )}
    </div>
  );
}

function IntervalBar({
  value,
  interval,
  decimals,
}: {
  value: number;
  interval: [number, number];
  decimals: number;
}) {
  const reduce = useReducedMotion();
  const [lo, hi] = interval;
  const pad = (hi - lo) * 0.6 || Math.abs(value) * 0.1 || 1;
  const min = Math.min(lo, value) - pad;
  const max = Math.max(hi, value) + pad;
  const pct = (x: number) => ((x - min) / (max - min)) * 100;
  return (
    <div className="relative h-2 w-full rounded-full bg-muted" aria-hidden>
      <motion.div
        className="absolute inset-y-0 rounded-full bg-primary/40"
        style={{ left: `${pct(lo)}%`, width: `${pct(hi) - pct(lo)}%`, originX: 0.5 }}
        initial={reduce ? false : { scaleX: 0 }}
        animate={{ scaleX: 1 }}
        transition={reduce ? reducedFade : intervalGrow}
        title={`${fmt(lo, decimals)} to ${fmt(hi, decimals)}`}
      />
      <div
        className="absolute -top-1 h-4 w-0.5 rounded bg-foreground"
        style={{ left: `${pct(value)}%` }}
      />
    </div>
  );
}
