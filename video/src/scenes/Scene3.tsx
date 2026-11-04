// Scene 3, a refusal on A08: the car crosses with SAM's outline (from the cached masks of the run's
// own track) and the frame edges it is cut off by; "I won't guess."; then the site's own result
// card with the reason and the fix (a recording of the live site). variant "x": the 40 s cut.
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
import { Background } from "../components/Background.tsx";
import { Captions } from "../components/Captions.tsx";
import { ClipStage, type Shot } from "../components/ClipStage.tsx";
import {
  easeOutCubic,
  FULL,
  MappedVideo,
  RecSegment,
} from "../components/Footage.tsx";
import { KineticLine } from "../components/KineticLine.tsx";
import { GlowDefs, Outline } from "../components/Outline.tsx";
import { Pin, pill } from "../components/Pin.tsx";
import { FACTS, SOURCES } from "../data/index.ts";
import { rings } from "../lib/geometry.ts";
import {
  cueMs,
  frames,
  mark,
  type Footage,
  type Narration,
  type Outline as Shape,
  type Recording,
} from "../lib/media.ts";
import { leadFrames, sceneFrames } from "../timeline.ts";
import { CALM, COLOR, FONT } from "../theme.ts";

export type Scene3Props = {
  narration: Narration;
  footage: Footage;
  rec: Recording;
  variant?: "full" | "x";
};

const EDGE = 9; // px of the red edge bar, in clip pixels

const A08Overlay: React.FC<{
  z: number;
  map: (f: number) => number;
  outlines: Shape[];
  w: number;
  h: number;
}> = ({ z, map, outlines, w, h }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const k = Math.round(map(frame));
  const o = outlines.find((x) => Math.abs(x.frame - k) <= 1);
  let tIn = 0;
  while (tIn < 600 && map(tIn) < outlines[0].frame) tIn++;
  const p = spring({
    frame: frame - tIn,
    fps,
    config: CALM,
    durationInFrames: 24,
  });
  if (!o) return null;
  const pulse = 0.55 + 0.3 * Math.sin(frame / 5);
  const pts = rings(o.path).flat();
  const top = Math.min(...pts.map((q) => q[1]));
  const cx = pts.reduce((s, q) => s + q[0], 0) / pts.length;
  const bars: Record<string, [number, number, number, number]> = {
    left: [0, 0, EDGE, h],
    right: [w - EDGE, 0, EDGE, h],
    top: [0, 0, w, EDGE],
    bottom: [0, h - EDGE, w, EDGE],
  };
  const edge = o.touches.includes("bottom") ? "bottom" : o.touches[0];
  return (
    <>
      <svg
        width={w}
        height={h}
        style={{ position: "absolute", left: 0, top: 0, overflow: "visible" }}
      >
        <GlowDefs />
        <Outline
          d={o.path}
          color={COLOR.track}
          progress={p}
          width={3.2 / z}
          fill={0.08 * p}
        />
        {o.touches.map((t) => {
          const [x, y, bw, bh] = bars[t];
          return (
            <rect
              key={t}
              x={x}
              y={y}
              width={bw}
              height={bh}
              fill={COLOR.destructive}
              opacity={pulse * p}
              filter="url(#glow)"
            />
          );
        })}
      </svg>
      <Pin at={[cx, top]} z={z} anchor="above">
        <span style={{ ...pill(COLOR.track), opacity: p }}>
          target · {String(SOURCES.a08.result.spec.target_phrase)}
        </span>
      </Pin>
      {edge && (
        <Pin
          at={
            edge === "bottom"
              ? [cx, h - 150]
              : edge === "left"
                ? [30, h / 2]
                : [w - 30, h / 2]
          }
          z={z}
          anchor={
            edge === "bottom" ? "above" : edge === "left" ? "right" : "left"
          }
        >
          <span style={{ ...pill(COLOR.destructive), opacity: p }}>
            cut off by the frame edge
          </span>
        </Pin>
      )}
    </>
  );
};

export const Scene3: React.FC<Scene3Props> = ({
  narration,
  footage,
  rec,
  variant = "full",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const x = variant === "x";
  const D = leadFrames(narration.id);
  const end = sceneFrames(narration);
  const outlines = footage.outlines ?? [];
  const midFrame =
    (outlines[0].frame + outlines[outlines.length - 1].frame) / 2;
  const cut = outlines.filter((o) => o.touches.length >= 2);
  const ff = (cut.length ? cut : outlines).reduce((b, o) =>
    Math.abs(o.frame - midFrame) < Math.abs(b.frame - midFrame) ? o : b,
  ).frame;
  const s0 = x ? 150 : 120;
  const ramp = 36;
  const dist = ramp / 3;
  const p1 = ff - dist - s0;
  const map = (f: number) =>
    f < p1
      ? s0 + f
      : f < p1 + ramp
        ? ff - dist + dist * easeOutCubic((f - p1) / ramp)
        : ff;
  const key = narration.keys.find((k) => k.name === "k_refuse");
  const tKey = key ? D + frames(key.startMs, fps) : end;
  const tFix = D + frames(cueMs(narration, "fix"), fps);
  const tBadge = x ? tKey - 30 : D + frames(cueMs(narration, "refuse"), fps);
  const srcW = footage.overlay_width;
  const srcH = footage.overlay_height;
  const z = 1920 / srcW;
  const shots: Shot[] = [
    {
      at: 0,
      dur: 1,
      win: FULL,
      focus: [srcW / 2, srcH / 2],
      zoom: z,
      radius: 0,
    },
    {
      at: p1,
      dur: Math.max(30, tKey - p1),
      focus: [srcW * 0.42, srcH * 0.58],
      zoom: z * 1.08,
    },
  ];
  const badge = spring({
    frame: frame - tBadge,
    fps,
    config: CALM,
    durationInFrames: 18,
  });
  const card = mark(rec, "card");
  const c = [card.box.x + card.box.w / 2, card.box.y + card.box.h / 2] as [
    number,
    number,
  ];
  const fadeOut = x ? 1 : interpolate(frame, [end - 1, end], [1, 1]);
  return (
    <AbsoluteFill style={{ opacity: fadeOut }}>
      <Background />
      <ClipStage shots={shots} srcW={srcW} srcH={srcH}>
        {(zz) => (
          <>
            <MappedVideo
              file={footage.file}
              map={map}
              width={srcW}
              height={srcH}
            />
            <A08Overlay
              z={zz}
              map={map}
              outlines={outlines}
              w={srcW}
              h={srcH}
            />
          </>
        )}
      </ClipStage>
      {frame >= tBadge && (
        <div
          style={{
            position: "absolute",
            left: 64,
            top: 40,
            opacity: badge,
            display: "flex",
            alignItems: "center",
            gap: 12,
            padding: "8px 18px",
            borderRadius: 999,
            border: `1px solid ${COLOR.destructive}99`,
            backgroundColor: "rgba(10,12,15,0.85)",
            fontFamily: FONT.sans,
            fontSize: 30,
            color: COLOR.foreground,
          }}
        >
          <span
            style={{
              width: 12,
              height: 12,
              borderRadius: 6,
              backgroundColor: COLOR.destructive,
            }}
          />
          {SOURCES.a08.result.status === "abstained" ? "Abstained" : ""}
        </div>
      )}
      {key && (
        <KineticLine
          lines={[FACTS.a08.refusal]}
          start={tKey}
          end={tFix + 10}
          size={150}
        />
      )}
      <RecSegment
        rec={rec}
        from={tFix}
        dur={Math.max(1, end - tFix)}
        recT={card.t + 0.2}
        hold
        cam={{ focus: c, zoom: 1.32 }}
        camTo={{ focus: c, zoom: 1.38 }}
        fade={12}
      />
      <Sequence from={D} layout="none">
        <Audio src={staticFile(narration.file)} />
      </Sequence>
      <Captions narration={narration} delay={D} />
    </AbsoluteFill>
  );
};
