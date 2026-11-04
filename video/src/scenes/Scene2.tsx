// Scene 2, speed on A14: our scooter's pass with its SAM outline, slowing to a stop mid-frame;
// Caliper's value and range, the gate method (replayed between its two gate lines), GPS, and
// Muse Spark alone. Every value is read from the A14 runs (field-a14, study-a14) through src/data.
import { Audio } from "@remotion/media";
import {
  AbsoluteFill,
  interpolate,
  Sequence,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { fmt } from "../../../web/src/lib/format.ts";
import { Background } from "../components/Background.tsx";
import { Captions } from "../components/Captions.tsx";
import {
  GuessCard,
  InstrumentCard,
  MeasuredCard,
} from "../components/Cards.tsx";
import { ClipStage, type Rect, type Shot } from "../components/ClipStage.tsx";
import { decimalsOf } from "../components/CountUp.tsx";
import {
  easeInOut,
  easeOutCubic,
  FULL,
  MappedVideo,
} from "../components/Footage.tsx";
import { GlowDefs, Outline } from "../components/Outline.tsx";
import { Pin, pill } from "../components/Pin.tsx";
import { FACTS, SOURCES } from "../data/index.ts";
import { rings } from "../lib/geometry.ts";
import {
  cueMs,
  frames,
  wordMs,
  type Footage,
  type Narration,
} from "../lib/media.ts";
import { leadFrames } from "../timeline.ts";
import { CALM, COLOR, FONT } from "../theme.ts";

export type Scene2Props = { narration: Narration; footage: Footage };

const REPLAY_FROM = 14; // footage frames of the replay between the gates
const REPLAY_TO = 70;

/** Footage frame shown at each scene frame: the pass, a slow stop mid-frame, then a replay. */
function plan(fc: number, tGate: number, tExpand: number, last: number) {
  const ramp = 36;
  const dist = ramp / 3; // easeOutCubic starts at full speed: 3 x dist / ramp = 1 frame a frame
  const rampStart = fc - dist;
  const s0 = Math.max(0, rampStart - 33);
  const p1 = rampStart - s0;
  const scrub = 15;
  return (f: number) => {
    if (f < p1) return s0 + f;
    if (f < p1 + ramp) return rampStart + dist * easeOutCubic((f - p1) / ramp);
    if (f < tGate) return fc;
    if (f < tGate + scrub)
      return fc + (REPLAY_FROM - fc) * easeInOut((f - tGate) / scrub);
    const g = tGate + scrub;
    if (f < g + (REPLAY_TO - REPLAY_FROM)) return REPLAY_FROM + (f - g);
    if (f < tExpand) return REPLAY_TO;
    return Math.min(last, REPLAY_TO + (f - tExpand));
  };
}

const A14Overlay: React.FC<{
  z: number;
  map: (f: number) => number;
  tGate: number;
  tVis: number;
}> = ({ z, map, tGate, tVis }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const run = SOURCES.a14;
  const study = SOURCES.study.A14;
  const k = Math.round(map(frame));
  const ov = (run.overlay.frames ?? []).find((o) => Math.abs(o.frame - k) <= 1);
  const tgt = ov?.target?.path;
  const pTgt = spring({
    frame: frame - tVis,
    fps,
    config: CALM,
    durationInFrames: 30,
  });
  const gates = interpolate(frame, [tGate, tGate + 12], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const reading = study.result.readings.find((r) => r.status === "measured");
  const srcFps = study.overlay.fps ?? 60;
  const replaying = frame >= tGate + 15;
  const lines = [
    { name: "B", g: study.overlay.gate_b, t: reading?.t_gate_b_s ?? null },
    { name: "A", g: study.overlay.gate_a, t: reading?.t_gate_a_s ?? null },
  ];
  const pts = tgt ? rings(tgt).flat() : [];
  const top = pts.length ? Math.min(...pts.map((p) => p[1])) : 0;
  const right = pts.length ? Math.max(...pts.map((p) => p[0])) : 0;
  const [ga, gb] = [study.overlay.gate_a, study.overlay.gate_b];
  const dimY = (run.overlay.height ?? 720) - 40;
  // The target's label sits right-aligned over it, kept inside the clip as the scooter leaves
  // frame left (screen width: Geist Mono advances 0.6 em at 24 px, plus the pill's padding).
  const tgtLabel = `target · ${String(run.result.spec.target_phrase)}`;
  const tgtW = tgtLabel.length * 0.6 * 24 + 26;
  return (
    <>
      <svg
        width={run.overlay.width}
        height={run.overlay.height}
        style={{ position: "absolute", left: 0, top: 0, overflow: "visible" }}
      >
        <GlowDefs />
        {tgt && (
          <Outline
            d={tgt}
            color={COLOR.track}
            progress={pTgt}
            width={3.2 / z}
            fill={0.08 * pTgt}
          />
        )}
        {gates > 0 &&
          lines.map(({ name, g, t }) => {
            if (!g) return null;
            const crossed = replaying && t !== null && k >= t * srcFps;
            return (
              <line
                key={name}
                x1={g[0][0]}
                y1={g[0][1]}
                x2={g[1][0]}
                y2={g[1][1]}
                stroke={COLOR.primary}
                strokeWidth={(crossed ? 4 : 2.4) / z}
                strokeDasharray={crossed ? undefined : `${10 / z} ${8 / z}`}
                opacity={gates * (crossed ? 1 : 0.75)}
                filter={crossed ? "url(#glow)" : undefined}
              />
            );
          })}
        {gates > 0 && ga && gb && (
          <g stroke={COLOR.primary} strokeWidth={2.4 / z} opacity={gates}>
            <line x1={ga[0][0]} y1={dimY} x2={gb[0][0]} y2={dimY} />
            <line
              x1={ga[0][0]}
              y1={dimY - 12 / z}
              x2={ga[0][0]}
              y2={dimY + 12 / z}
            />
            <line
              x1={gb[0][0]}
              y1={dimY - 12 / z}
              x2={gb[0][0]}
              y2={dimY + 12 / z}
            />
          </g>
        )}
      </svg>
      {tgt && (
        <Pin
          at={[Math.max(right - tgtW / z, 8 / z), top]}
          z={z}
          anchor="above-left"
        >
          <span style={{ ...pill(COLOR.track), opacity: pTgt }}>
            {tgtLabel}
          </span>
        </Pin>
      )}
      {gates > 0 &&
        lines.map(({ name, g, t }) =>
          g ? (
            <Pin key={name} at={[g[0][0], 40]} z={z} anchor="right">
              <span style={{ ...pill(COLOR.primary), opacity: gates }}>
                gate {name}
                {replaying && t !== null && k >= t * srcFps
                  ? ` · ${fmt(t, 2)} s`
                  : ""}
              </span>
            </Pin>
          ) : null,
        )}
      {gates > 0 && ga && gb && (
        <Pin at={[(ga[0][0] + gb[0][0]) / 2, dimY]} z={z} anchor="above">
          <span style={{ ...pill(COLOR.primary), opacity: gates }}>
            {FACTS.a14.gateM} m between the gates
          </span>
        </Pin>
      )}
    </>
  );
};

export const Scene2: React.FC<Scene2Props> = ({ narration, footage }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const f = FACTS.a14;
  const run = SOURCES.a14;
  const reading = SOURCES.study.A14.result.readings.find(
    (r) => r.status === "measured",
  );
  const D = leadFrames(narration.id);
  const at = (cue: string) => D + frames(cueMs(narration, cue), fps);
  const word = (w: string, cue: string) =>
    D + frames(wordMs(narration, w, cueMs(narration, cue)), fps);
  const tCal = at("caliper");
  const tGate = at("gate");
  const tExpand = D + frames(narration.durationMs, fps) + 4;
  const ov = run.overlay.frames ?? [];
  const mid = (run.overlay.width ?? 1280) / 2;
  const off = (o: (typeof ov)[number]) =>
    Math.abs((o.target?.centroid[0] ?? 1e9) - mid);
  const fc = ov.reduce((b, o) => (off(o) < off(b) ? o : b), ov[0]).frame;
  const map = plan(fc, tGate, tExpand, footage.frames - 1);
  let tVis = 0;
  while (tVis < 300 && map(tVis) < ov[0].frame) tVis++;
  const srcW = footage.overlay_width;
  const srcH = footage.overlay_height;
  const side: Rect = [64, 188, 1140, 641];
  const zFull = 1920 / srcW;
  const zSide = side[2] / srcW;
  const middle: [number, number] = [srcW / 2, srcH / 2];
  const shots: Shot[] = [
    { at: 0, dur: 1, win: FULL, focus: middle, zoom: zFull, radius: 0 },
    { at: 0, dur: Math.round(fps * 4), zoom: zFull * 1.04 },
    {
      at: tCal - 8,
      dur: 40,
      win: side,
      focus: middle,
      zoom: zSide,
      radius: 18,
    },
    { at: tExpand, dur: 26, win: FULL, focus: middle, zoom: zFull, radius: 0 },
  ];
  const iv = run.result.interval_90 ?? [0, 0];
  const clamp = {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  } as const;
  const cards = interpolate(frame, [tExpand, tExpand + 12], [1, 0], clamp);
  const title = interpolate(
    frame,
    [6, 18, tCal - 12, tCal],
    [0, 1, 1, 0],
    clamp,
  );
  const col = { x: 1264, w: 592 };
  return (
    <AbsoluteFill>
      <Background />
      <ClipStage shots={shots} srcW={srcW} srcH={srcH}>
        {(z) => (
          <>
            <MappedVideo
              file={footage.file}
              map={map}
              width={srcW}
              height={srcH}
            />
            <A14Overlay z={z} map={map} tGate={tGate} tVis={tVis} />
          </>
        )}
      </ClipStage>
      <div
        style={{
          position: "absolute",
          left: 64,
          top: 40,
          opacity: title,
          ...pill(COLOR.foreground, 28),
          fontFamily: FONT.sans,
        }}
      >
        {run.meta.title}
      </div>
      <AbsoluteFill style={{ opacity: cards }}>
        <MeasuredCard
          x={col.x}
          y={112}
          w={col.w}
          h={262}
          start={word(f.cal, "caliper") - 8}
          countAt={word(f.cal, "caliper")}
          rangeAt={word("range", "caliper")}
          value={f.calNum}
          decimals={1}
          unit="km/h"
          interval={[iv[0] * 3.6, iv[1] * 3.6]}
          size={88}
          note={`Ruler: its own taped length, ${f.scooterLength} m, given`}
        />
        <MeasuredCard
          x={col.x}
          y={392}
          w={col.w}
          h={190}
          start={word(f.gate, "gate") - 8}
          countAt={word(f.gate, "gate")}
          rangeAt={word(f.gate, "gate")}
          value={f.gateNum}
          decimals={1}
          unit="km/h"
          interval={reading?.interval_90_kmh ?? [0, 0]}
          size={76}
          title="Gate method"
          badge=""
          bar={false}
        />
        <InstrumentCard
          x={col.x}
          y={600}
          w={col.w}
          h={142}
          start={word(f.gps, "gps") - 8}
          countAt={word(f.gps, "gps")}
          instrument="GPS app"
          value={f.gpsNum}
          decimals={decimalsOf(f.gps)}
          unit="km/h"
          size={72}
        />
        <GuessCard
          x={col.x}
          y={760}
          w={col.w}
          h={160}
          start={word(f.guess, "guess") - 8}
          countAt={word(f.guess, "guess")}
          value={f.guessNum}
          decimals={decimalsOf(f.guess)}
          unit="km/h"
          size={72}
        />
      </AbsoluteFill>
      <Sequence from={D} layout="none">
        <Audio src={staticFile(narration.file)} />
      </Sequence>
      <Captions narration={narration} delay={D} />
    </AbsoluteFill>
  );
};
