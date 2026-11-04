// The site's readout cards (web/src/app/page.tsx GuessCard, MeasuredCard, InstrumentCard), sized
// for video. Values arrive formatted by src/data/facts.ts or read from the runs; none is typed here.
import type { CSSProperties, ReactNode } from "react";
import { spring, useCurrentFrame, useVideoConfig } from "remotion";
import { fmt } from "../../../web/src/lib/format.ts";
import { CALM, COLOR, FONT } from "../theme.ts";
import { CountUp } from "./CountUp.tsx";

type Box = { x: number; y: number; w: number; h: number; start: number };

const Shell: React.FC<Box & { style?: CSSProperties; children: ReactNode }> = ({
  x,
  y,
  w,
  h,
  start,
  style,
  children,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = spring({
    frame: frame - start,
    fps,
    config: CALM,
    durationInFrames: 26,
  });
  if (frame < start) return null;
  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y,
        width: w,
        height: h,
        boxSizing: "border-box",
        borderRadius: 16,
        padding: "22px 30px",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        gap: 10,
        fontFamily: FONT.sans,
        opacity: p,
        translate: `${(1 - p) * 64}px 0px`,
        ...style,
      }}
    >
      {children}
    </div>
  );
};

const Header: React.FC<{ children: ReactNode; color?: string }> = ({
  children,
  color = COLOR.mutedForeground,
}) => (
  <div
    style={{
      fontSize: 27,
      fontWeight: 500,
      color,
      display: "flex",
      alignItems: "center",
      gap: 14,
    }}
  >
    {children}
  </div>
);

const Value: React.FC<{
  children: ReactNode;
  unit: string;
  size: number;
  color: string;
}> = ({ children, unit, size, color }) => (
  <div
    style={{
      display: "flex",
      alignItems: "baseline",
      gap: 16,
      fontFamily: FONT.mono,
      fontVariantNumeric: "tabular-nums",
    }}
  >
    <span
      style={{ fontSize: size, lineHeight: 1, color, letterSpacing: "-0.02em" }}
    >
      {children}
    </span>
    <span style={{ fontSize: size * 0.36, color: COLOR.mutedForeground }}>
      {unit}
    </span>
  </div>
);

const Note: React.FC<{
  children: ReactNode;
  mono?: boolean;
  opacity?: number;
}> = ({ children, mono, opacity = 1 }) => (
  <div
    style={{
      fontSize: mono ? 25 : 23,
      fontFamily: mono ? FONT.mono : FONT.sans,
      color: COLOR.mutedForeground,
      lineHeight: 1.3,
      opacity,
      fontVariantNumeric: "tabular-nums",
    }}
  >
    {children}
  </div>
);

type Count = {
  value: number;
  decimals: number;
  unit: string;
  countAt: number;
  size?: number;
};

/** Muse Spark alone: dimmed, dashed, labelled a guess (DESIGN principle 4). */
export const GuessCard: React.FC<Box & Count> = (p) => (
  <Shell
    {...p}
    style={{
      border: `2px dashed ${COLOR.border}`,
      backgroundColor: "rgba(18,22,27,0.55)",
      color: COLOR.mutedForeground,
    }}
  >
    <Header>Muse Spark alone · guess</Header>
    <Value unit={p.unit} size={p.size ?? 96} color={COLOR.mutedForeground}>
      <CountUp
        value={p.value}
        decimals={p.decimals}
        start={p.countAt}
        duration={18}
      />
    </Value>
    <Note>No range: a guess has none.</Note>
  </Shell>
);

/** A measured value with its 90% range (web Readout.tsx): the number is the hero. */
export const MeasuredCard: React.FC<
  Box &
    Count & {
      interval: [number, number];
      rangeAt: number;
      title?: string;
      badge?: string;
      bar?: boolean;
      note?: string;
    }
> = (p) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const [lo, hi] = p.interval;
  const pad = (hi - lo) * 0.6 || Math.abs(p.value) * 0.1 || 1;
  const min = Math.min(lo, p.value) - pad;
  const max = Math.max(hi, p.value) + pad;
  const pct = (v: number) => ((v - min) / (max - min)) * 100;
  const grow = spring({
    frame: frame - p.rangeAt,
    fps,
    config: CALM,
    durationInFrames: 30,
  });
  return (
    <Shell
      {...p}
      style={{
        border: `1px solid ${COLOR.border}`,
        backgroundColor: COLOR.card,
        boxShadow: "0 24px 60px rgba(0,0,0,0.45)",
      }}
    >
      <Header color={COLOR.foreground}>
        {p.title ?? "Caliper"}
        {p.badge !== "" && (
          <span
            style={{
              fontSize: 21,
              color: COLOR.primary,
              border: "1px solid rgba(255,178,36,0.45)",
              backgroundColor: "rgba(255,178,36,0.12)",
              borderRadius: 7,
              padding: "3px 12px",
            }}
          >
            {p.badge ?? "Measured"}
          </span>
        )}
      </Header>
      <Value unit={p.unit} size={p.size ?? 116} color={COLOR.foreground}>
        <CountUp value={p.value} decimals={p.decimals} start={p.countAt} />
      </Value>
      {p.bar !== false && (
        <div
          style={{
            position: "relative",
            height: 12,
            borderRadius: 6,
            backgroundColor: COLOR.muted,
            marginTop: 6,
          }}
        >
          <div
            style={{
              position: "absolute",
              top: 0,
              bottom: 0,
              left: `${pct(lo)}%`,
              width: `${pct(hi) - pct(lo)}%`,
              borderRadius: 6,
              backgroundColor: "rgba(255,178,36,0.45)",
              scale: `${grow} 1`,
            }}
          />
          <div
            style={{
              position: "absolute",
              top: -6,
              height: 24,
              width: 3,
              borderRadius: 2,
              left: `${pct(p.value)}%`,
              backgroundColor: COLOR.foreground,
              opacity: grow,
            }}
          />
        </div>
      )}
      <Note mono opacity={grow}>
        90% range {fmt(lo, p.decimals)} to {fmt(hi, p.decimals)} {p.unit}
      </Note>
      {p.note && <Note>{p.note}</Note>}
    </Shell>
  );
};

/** The instrument: tape measure or GPS app, printed as the site does. */
export const InstrumentCard: React.FC<Box & Count & { instrument: string }> = (
  p,
) => (
  <Shell
    {...p}
    style={{ border: `1px solid ${COLOR.border}`, backgroundColor: COLOR.card }}
  >
    <Header>Instrument · {p.instrument}</Header>
    <Value unit={p.unit} size={p.size ?? 96} color={COLOR.foreground}>
      <CountUp
        value={p.value}
        decimals={p.decimals}
        start={p.countAt}
        duration={18}
      />
    </Value>
  </Shell>
);
