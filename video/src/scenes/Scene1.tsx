// Scene 1, cold open on C07: the clip, SAM's outlines drawing on, then the guess, Caliper's value
// with its 90% range, and the tape. Every value is read from the run JSON through src/data.
// variant "x": the same shot for the 40-second cut (shorter narration, no coin push, no fade in).
import { Audio, Video } from "@remotion/media";
import {
  AbsoluteFill,
  interpolate,
  Sequence,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { Background } from "../components/Background.tsx";
import { Captions } from "../components/Captions.tsx";
import {
  GuessCard,
  InstrumentCard,
  MeasuredCard,
} from "../components/Cards.tsx";
import { ClipStage, type Rect, type Shot } from "../components/ClipStage.tsx";
import { CountUp, decimalsOf } from "../components/CountUp.tsx";
import { KineticLine } from "../components/KineticLine.tsx";
import { GlowDefs, Outline } from "../components/Outline.tsx";
import { Pin, pill } from "../components/Pin.tsx";
import { FACTS, SOURCES } from "../data/index.ts";
import {
  disc,
  longestSpan,
  overlayAt,
  rings,
  type Pt,
} from "../lib/geometry.ts";
import {
  cueMs,
  frames,
  sourceFrame,
  wordMs,
  type Footage,
  type Narration,
} from "../lib/media.ts";
import { leadFrames } from "../timeline.ts";
import { CALM, COLOR, FONT } from "../theme.ts";

export type Scene1Props = {
  narration: Narration;
  footage: Footage;
  variant?: "full" | "x";
};

const C07Overlay: React.FC<{
  z: number;
  footage: Footage;
  tCoin: number;
  tValue: number;
}> = ({ z, footage, tCoin, tValue }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const f = FACTS.c07;
  const ov = overlayAt(
    SOURCES.c07.overlay.frames ?? [],
    sourceFrame(footage, frame),
  );
  const pRef = spring({
    frame: frame - 10,
    fps,
    config: CALM,
    durationInFrames: 34,
  });
  const pTgt = spring({
    frame: frame - 20,
    fps,
    config: CALM,
    durationInFrames: 46,
  });
  const pCoin = spring({
    frame: frame - tCoin,
    fps,
    config: CALM,
    durationInFrames: 22,
  });
  const pDim = spring({
    frame: frame - tValue,
    fps,
    config: CALM,
    durationInFrames: 30,
  });
  const labels = interpolate(frame, [44, 58], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const sw = 3.4 / z;
  const tick = 13 / z;
  const tgt = ov.target?.path;
  const ref = ov.reference?.path;
  const span = tgt ? longestSpan(tgt, 12) : null;
  const coin = ref ? disc(ref) : null;
  const pts = tgt ? rings(tgt).flat() : [];
  const top = pts.length ? Math.min(...pts.map((p) => p[1])) : 0;
  const right = pts.length ? Math.max(...pts.map((p) => p[0])) : 0;
  return (
    <>
      <svg
        width={footage.overlay_width}
        height={footage.overlay_height}
        style={{ position: "absolute", left: 0, top: 0, overflow: "visible" }}
      >
        <GlowDefs />
        {ref && (
          <Outline
            d={ref}
            color={COLOR.primary}
            progress={pRef}
            width={sw}
            fill={0.1 * pRef}
          />
        )}
        {tgt && (
          <Outline
            d={tgt}
            color={COLOR.track}
            progress={pTgt}
            width={sw}
            fill={0.06 * pTgt}
          />
        )}
        {coin && pCoin > 0 && (
          <g stroke={COLOR.primary} strokeWidth={2.6 / z} strokeLinecap="round">
            <line
              x1={coin.c[0] - coin.d / 2}
              y1={coin.c[1]}
              x2={coin.c[0] - coin.d / 2 + coin.d * pCoin}
              y2={coin.c[1]}
            />
            <line
              x1={coin.c[0] - coin.d / 2}
              y1={coin.c[1] - tick}
              x2={coin.c[0] - coin.d / 2}
              y2={coin.c[1] + tick}
            />
            {pCoin > 0.97 && (
              <line
                x1={coin.c[0] + coin.d / 2}
                y1={coin.c[1] - tick}
                x2={coin.c[0] + coin.d / 2}
                y2={coin.c[1] + tick}
              />
            )}
          </g>
        )}
        {span && pDim > 0 && (
          <g
            stroke={COLOR.foreground}
            strokeWidth={2.6 / z}
            strokeLinecap="round"
            filter="url(#glow)"
          >
            <line
              x1={span.a[0]}
              y1={span.a[1]}
              x2={span.a[0] + (span.b[0] - span.a[0]) * pDim}
              y2={span.a[1] + (span.b[1] - span.a[1]) * pDim}
            />
            <line
              x1={span.a[0] - span.n[0] * tick}
              y1={span.a[1] - span.n[1] * tick}
              x2={span.a[0] + span.n[0] * tick}
              y2={span.a[1] + span.n[1] * tick}
            />
            {pDim > 0.97 && (
              <line
                x1={span.b[0] - span.n[0] * tick}
                y1={span.b[1] - span.n[1] * tick}
                x2={span.b[0] + span.n[0] * tick}
                y2={span.b[1] + span.n[1] * tick}
              />
            )}
          </g>
        )}
      </svg>
      {tgt && (
        <Pin at={[right, top]} z={z} anchor="above-right">
          <span style={{ ...pill(COLOR.track), opacity: labels }}>
            target · {f.target}
          </span>
        </Pin>
      )}
      {coin && (
        <Pin at={[coin.c[0] + coin.d / 2, coin.c[1]]} z={z} anchor="right">
          <span
            style={{
              ...pill(COLOR.primary),
              opacity: labels,
              display: "inline-flex",
              alignItems: "baseline",
            }}
          >
            ruler · {f.reference}
            <span
              style={{
                display: "inline-block",
                overflow: "hidden",
                whiteSpace: "pre",
                maxWidth: pCoin * 360,
                opacity: pCoin,
              }}
            >
              {" · "}
              {f.referenceSize} {f.unit}, given
            </span>
          </span>
        </Pin>
      )}
      {span && pDim > 0 && (
        <Pin
          at={[(span.a[0] + span.b[0]) / 2, (span.a[1] + span.b[1]) / 2]}
          z={z}
          anchor="above"
        >
          <span
            style={{ ...pill(COLOR.foreground), fontSize: 30, opacity: pDim }}
          >
            <CountUp value={f.valueNum} decimals={f.decimals} start={tValue} />{" "}
            {f.unit}
          </span>
        </Pin>
      )}
    </>
  );
};

export const Scene1: React.FC<Scene1Props> = ({
  narration,
  footage,
  variant = "full",
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const f = FACTS.c07;
  const x = variant === "x";
  const D = leadFrames(narration.id);
  const at = (cue: string) => D + frames(cueMs(narration, cue), fps);
  const tGuess = at("guess");
  const tCaliper = at("caliper");
  const valueAfter = cueMs(narration, x ? "caliper" : "coin");
  const tCoin = x ? tCaliper : at("coin");
  const tValue = D + frames(wordMs(narration, f.value, valueAfter), fps);
  const tRange = D + frames(wordMs(narration, "range", valueAfter), fps);
  const tTape = at("tape");
  const key = narration.keys.find((k) => k.name === "k_title");

  const srcW = footage.overlay_width;
  const srcH = footage.overlay_height;
  const fitZ = height / srcH;
  const full: Rect = [(width - srcW * fitZ) / 2, 0, srcW * fitZ, height];
  const side: Rect = [64, 112, 1140, Math.round((1140 * srcH) / srcW)];
  const zSide = side[2] / srcW;
  const first = (SOURCES.c07.overlay.frames ?? [])[0];
  const coinAt: Pt = first?.reference?.centroid ?? [srcW / 2, srcH / 2];
  const middle: Pt = [srcW / 2, srcH / 2];
  const shots: Shot[] = [
    { at: 0, dur: 1, win: full, focus: middle, zoom: fitZ, radius: 0 },
    { at: 0, dur: Math.round(fps * 5), zoom: fitZ * 1.05 },
    {
      at: tGuess - 10,
      dur: 40,
      win: side,
      focus: middle,
      zoom: zSide,
      radius: 18,
    },
    ...(x
      ? []
      : [
          { at: tCaliper, dur: 56, focus: coinAt, zoom: zSide * 1.7 },
          { at: tValue - 8, dur: 44, focus: middle, zoom: zSide },
        ]),
    { at: tTape, dur: Math.round(fps * 4), zoom: zSide * 1.04 },
  ];
  const fadeIn = x
    ? 0
    : interpolate(frame, [0, 14], [1, 0], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      });
  const question = x
    ? 1
    : interpolate(frame, [6, 20], [0, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      });
  const col = { x: 1264, w: 592 };
  return (
    <AbsoluteFill>
      <Background />
      <ClipStage shots={shots} srcW={srcW} srcH={srcH}>
        {(z) => (
          <>
            <Video
              src={staticFile(footage.file)}
              loop
              muted
              style={{ width: srcW, height: srcH }}
            />
            <C07Overlay z={z} footage={footage} tCoin={tCoin} tValue={tValue} />
          </>
        )}
      </ClipStage>
      <div
        style={{
          position: "absolute",
          left: 64,
          top: 34,
          opacity: question,
          display: "flex",
          alignItems: "baseline",
          gap: 16,
          padding: "10px 20px",
          borderRadius: 10,
          backgroundColor: "rgba(10,12,15,0.82)",
          border: `1px solid ${COLOR.border}`,
          fontFamily: FONT.sans,
        }}
      >
        <span
          style={{
            fontSize: 19,
            letterSpacing: "0.14em",
            textTransform: "uppercase",
            color: COLOR.mutedForeground,
          }}
        >
          Question
        </span>
        <span style={{ fontSize: 30, color: COLOR.foreground }}>
          {f.question}
        </span>
      </div>
      <GuessCard
        x={col.x}
        y={112}
        w={col.w}
        h={226}
        start={tGuess}
        countAt={tGuess + 6}
        value={f.guessNum}
        decimals={decimalsOf(f.guess)}
        unit={f.unit}
      />
      <MeasuredCard
        x={col.x}
        y={360}
        w={col.w}
        h={300}
        start={tValue - 10}
        countAt={tValue}
        rangeAt={tRange}
        value={f.valueNum}
        decimals={f.decimals}
        unit={f.unit}
        interval={f.interval}
      />
      <InstrumentCard
        x={col.x}
        y={682}
        w={col.w}
        h={180}
        start={tTape}
        countAt={tTape + 4}
        instrument={f.instrument}
        value={f.tapeNum}
        decimals={decimalsOf(f.tape)}
        unit={f.unit}
      />
      {key && (
        <KineticLine
          lines={["AI guesses.", "Caliper measures."]}
          start={D + frames(key.startMs, fps)}
          underline="measures."
        />
      )}
      <Sequence from={D} layout="none">
        <Audio src={staticFile(narration.file)} />
      </Sequence>
      <Captions narration={narration} delay={D} />
      {fadeIn > 0 && (
        <AbsoluteFill
          style={{
            backgroundColor: "#000",
            opacity: fadeIn,
            pointerEvents: "none",
          }}
        />
      )}
    </AbsoluteFill>
  );
};
