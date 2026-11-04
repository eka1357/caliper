// Geometry of SAM's outlines (SVG paths in video pixels, web/public/runs/*/run.json overlay).
import type { OverlayFrame } from "../../../web/src/lib/types.ts";

export type Pt = [number, number];

/** The closed rings of an outline path ("M x y L x y ... Z", one ring per M). */
export function rings(path: string): Pt[][] {
  return path
    .split(/(?=M)/)
    .map((sub) => {
      const nums = sub.match(/-?\d+(?:\.\d+)?/g)?.map(Number) ?? [];
      const pts: Pt[] = [];
      for (let i = 0; i + 1 < nums.length; i += 2)
        pts.push([nums[i], nums[i + 1]]);
      return pts;
    })
    .filter((r) => r.length >= 3);
}

/** Area moments of the filled outline (Green's theorem), like the mask pixels the engine uses. */
function moments(rs: Pt[][]) {
  let a = 0;
  let sx = 0;
  let sy = 0;
  let sxx = 0;
  let syy = 0;
  let sxy = 0;
  for (const r of rs) {
    for (let i = 0; i < r.length; i++) {
      const [x0, y0] = r[i];
      const [x1, y1] = r[(i + 1) % r.length];
      const c = x0 * y1 - x1 * y0;
      a += c / 2;
      sx += ((x0 + x1) * c) / 6;
      sy += ((y0 + y1) * c) / 6;
      sxx += ((x0 * x0 + x0 * x1 + x1 * x1) * c) / 12;
      syy += ((y0 * y0 + y0 * y1 + y1 * y1) * c) / 12;
      sxy += ((x0 * y1 + 2 * x0 * y0 + 2 * x1 * y1 + x1 * y0) * c) / 24;
    }
  }
  const cx = sx / a;
  const cy = sy / a;
  return {
    area: Math.abs(a),
    cx,
    cy,
    vxx: sxx / a - cx * cx,
    vyy: syy / a - cy * cy,
    vxy: sxy / a - cx * cy,
  };
}

/**
 * The outline's span along its principal (longest) axis: the "longest" extent of
 * backend/caliper/segment.py mask_geometry, which takes the principal axes of the mask pixels.
 * Returns the two ends, offset sideways by `offset` pixels toward +y (below the object).
 */
export function longestSpan(
  path: string,
  offset: number,
): { a: Pt; b: Pt; n: Pt } {
  const rs = rings(path);
  const m = moments(rs);
  const th = 0.5 * Math.atan2(2 * m.vxy, m.vxx - m.vyy);
  const u: Pt = [Math.cos(th), Math.sin(th)];
  let n: Pt = [-u[1], u[0]];
  if (n[1] < 0) n = [-n[0], -n[1]];
  let lo = Infinity;
  let hi = -Infinity;
  let side = -Infinity;
  for (const r of rs) {
    for (const [x, y] of r) {
      const t = (x - m.cx) * u[0] + (y - m.cy) * u[1];
      lo = Math.min(lo, t);
      hi = Math.max(hi, t);
      side = Math.max(side, (x - m.cx) * n[0] + (y - m.cy) * n[1]);
    }
  }
  const at = (t: number): Pt => [
    m.cx + u[0] * t + n[0] * (side + offset),
    m.cy + u[1] * t + n[1] * (side + offset),
  ];
  const [a, b] = u[0] >= 0 ? [at(lo), at(hi)] : [at(hi), at(lo)];
  return { a, b, n };
}

/** Centre and "disc" diameter (the circle with the same area), as the engine measures a coin. */
export function disc(path: string): { c: Pt; d: number } {
  const m = moments(rings(path));
  return { c: [m.cx, m.cy], d: 2 * Math.sqrt(m.area / Math.PI) };
}

/** The overlay frame shown at source frame k: the last one at or before k (SAM skips some). */
export function overlayAt(frames: OverlayFrame[], k: number): OverlayFrame {
  let lo = 0;
  let hi = frames.length - 1;
  if (k <= frames[0].frame) return frames[0];
  while (lo < hi) {
    const mid = (lo + hi + 1) >> 1;
    if (frames[mid].frame <= k) lo = mid;
    else hi = mid - 1;
  }
  return frames[lo];
}
