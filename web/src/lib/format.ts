// Number formatting for the readout. Precision follows the 90% interval, so the display never
// claims more digits than the measurement supports.

export function decimalsFor(interval: [number, number] | null, value: number): number {
  const half = interval ? Math.abs(interval[1] - interval[0]) / 2 : Math.abs(value) * 0.05;
  if (!Number.isFinite(half) || half <= 0) return 2;
  return Math.min(4, Math.max(0, -Math.floor(Math.log10(half))));
}

export function fmt(value: number, decimals: number): string {
  return value.toFixed(decimals);
}

export function fmtUsd(value: number): string {
  return `$${value.toFixed(value < 0.1 ? 4 : 2)}`;
}

export function fmtMs(ms: number): string {
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)} s` : `${Math.round(ms)} ms`;
}

/** Window width in seconds from the engine's method line ("local quadratic window 0.30 s"). */
export function fitWindowS(method: string): number | null {
  const m = /window ([\d.]+) s/.exec(method);
  return m ? Number(m[1]) : null;
}
