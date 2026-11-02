import type { FieldRow } from "@/lib/results";

// Set C per clip: Caliper's 90% range as a bar, the tape value as a tick, Muse Spark alone's guess
// as a hollow dot (a guess has no range). Rows come from results.json; nothing is typed. Static
// SVG: one row per clip, so it needs no interaction and no chart runtime.

const ROW = 26;
const LEFT = 40;
const RIGHT = 12;
const WIDTH = 420;

export function SetCRanges({ rows, unit }: { rows: FieldRow[]; unit: string }) {
  const usable = rows.filter((r) => r.lo != null && r.hi != null && r.truth != null);
  if (usable.length === 0) return null;
  const max = Math.max(...usable.flatMap((r) => [r.hi ?? 0, r.truth ?? 0, r.guess_pred ?? 0])) * 1.08;
  const x = (v: number) => LEFT + (v / max) * (WIDTH - LEFT - RIGHT);
  const height = usable.length * ROW + 28;
  const ticks = niceTicks(max);
  return (
    <figure className="flex min-w-0 flex-col gap-2">
      <svg viewBox={`0 0 ${WIDTH} ${height}`} className="h-auto w-full" role="img"
        aria-label={`Set C: Caliper's 90% range, the tape value and Muse Spark alone's guess for each clip, in ${unit}`}>
        {ticks.map((t) => (
          <g key={t}>
            <line x1={x(t)} x2={x(t)} y1={4} y2={height - 22} stroke="var(--border)" strokeWidth={1} />
            <text x={x(t)} y={height - 8} textAnchor="middle" fontSize={10} fill="var(--muted-foreground)">{t}</text>
          </g>
        ))}
        {usable.map((r, i) => {
          const cy = 8 + i * ROW + ROW / 2;
          const inside = r.covered === true;
          return (
            <g key={r.clip_id}>
              <text x={0} y={cy + 4} fontSize={11} fill="var(--muted-foreground)" fontFamily="var(--font-geist-mono)">{r.clip_id}</text>
              <rect x={x(r.lo!)} y={cy - 5} width={Math.max(1, x(r.hi!) - x(r.lo!))} height={10} rx={3}
                fill={inside ? "var(--track)" : "var(--destructive)"} opacity={0.45} />
              <line x1={x(r.truth!)} x2={x(r.truth!)} y1={cy - 9} y2={cy + 9} stroke="var(--foreground)" strokeWidth={2} />
              {r.guess_pred != null && (
                <circle cx={x(r.guess_pred)} cy={cy} r={4} fill="none" stroke="var(--muted-foreground)" strokeWidth={1.5} />
              )}
            </g>
          );
        })}
      </svg>
      <figcaption className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
        <span><span className="mr-1 inline-block h-2 w-4 rounded-sm bg-track/45 align-middle" />Caliper 90% range</span>
        <span><span className="mr-1 inline-block h-2 w-4 rounded-sm bg-destructive/45 align-middle" />range misses the tape</span>
        <span><span className="mr-1 inline-block h-3 w-0.5 bg-foreground align-middle" />tape measure</span>
        <span><span className="mr-1 inline-block size-2 rounded-full border border-muted-foreground align-middle" />Muse Spark alone</span>
        <span>({unit})</span>
      </figcaption>
    </figure>
  );
}

function niceTicks(max: number): number[] {
  const step = max > 20 ? 10 : max > 10 ? 5 : 2;
  const out = [];
  for (let t = 0; t <= max; t += step) out.push(t);
  return out;
}
