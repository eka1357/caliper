// Scene 5, the street speed study on the live site (/study, recorded runs), then the six scooter
// passes: the gate method's speed against GPS, read from the study runs and results.json.
// S02 slot: when a multi-vehicle street clip (S02) is filmed and run, put its study run here; it
// is not filmed yet, so the scene shows only the scooter passes.
import { Audio } from "@remotion/media";
import {
  AbsoluteFill,
  Sequence,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { Captions } from "../components/Captions.tsx";
import { CountUp } from "../components/CountUp.tsx";
import { type Cam, RecSegment } from "../components/Footage.tsx";
import { FACTS, SOURCES } from "../data/index.ts";
import {
  cueMs,
  frames,
  mark,
  wordMs,
  type Narration,
  type Recording,
} from "../lib/media.ts";
import { leadFrames, sceneFrames } from "../timeline.ts";
import { CALM, COLOR, FONT } from "../theme.ts";

export type Scene5Props = { narration: Narration; rec: Recording };

const STREET_STUDY = null; // S02, when it exists (docs/demo_agent.md section 3)

const PassTable: React.FC<{
  show: number;
  step: number;
  tMedian: number;
  tNarrow: number;
  tOne: number;
}> = ({ show, step, tMedian, tNarrow, tOne }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = FACTS.study;
  const covered = new Map(
    SOURCES.results.field
      .filter((r) => r.set === "scooter" && r.path === "study")
      .map((r) => [r.clip_id, r.covered]),
  );
  const p = spring({
    frame: frame - (show - 10),
    fps,
    config: CALM,
    durationInFrames: 20,
  });
  const hl = spring({
    frame: frame - tNarrow,
    fps,
    config: CALM,
    durationInFrames: 20,
  });
  const cell: React.CSSProperties = {
    fontFamily: FONT.mono,
    fontSize: 30,
    fontVariantNumeric: "tabular-nums",
  };
  const head: React.CSSProperties = {
    fontFamily: FONT.sans,
    fontSize: 22,
    color: COLOR.mutedForeground,
  };
  return (
    <div
      style={{
        position: "absolute",
        left: 64,
        top: 112,
        width: 840,
        padding: "28px 34px",
        boxSizing: "border-box",
        borderRadius: 16,
        border: `1px solid ${COLOR.border}`,
        backgroundColor: "rgba(12,15,19,0.95)",
        opacity: p,
        translate: `${(1 - p) * -40}px 0px`,
        display: "flex",
        flexDirection: "column",
        gap: 14,
      }}
    >
      <div
        style={{ fontFamily: FONT.sans, fontSize: 30, color: COLOR.foreground }}
      >
        {s.n} passes of our scooter: gate method against GPS
      </div>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "100px 1fr 140px 150px",
          rowGap: 10,
          alignItems: "baseline",
        }}
      >
        <span style={head}>Pass</span>
        <span style={head}>Gate method, 90% range</span>
        <span style={head}>GPS</span>
        <span
          style={{
            ...head,
            color: hl > 0.5 ? COLOR.foreground : COLOR.mutedForeground,
          }}
        >
          GPS inside
        </span>
        {s.passes.map((r, i) => {
          const o = frame >= show + i * step ? 1 : 0;
          const inside = covered.get(r.clip);
          return [
            <span
              key={`${r.clip}c`}
              style={{ ...cell, color: COLOR.mutedForeground, opacity: o }}
            >
              {r.clip}
            </span>,
            <span
              key={`${r.clip}s`}
              style={{ ...cell, color: COLOR.foreground, opacity: o }}
            >
              {r.speed}{" "}
              <span style={{ fontSize: 22, color: COLOR.mutedForeground }}>
                ({r.lo} to {r.hi}) km/h
              </span>
            </span>,
            <span
              key={`${r.clip}g`}
              style={{ ...cell, color: COLOR.foreground, opacity: o }}
            >
              {r.gps ?? ""}
            </span>,
            <span
              key={`${r.clip}i`}
              style={{
                ...cell,
                opacity: o,
                color: inside ? COLOR.success : COLOR.destructive,
                fontWeight: 500,
                scale: inside && hl > 0 ? String(1 + 0.15 * hl) : "1",
              }}
            >
              {inside ? "yes" : "no"}
            </span>,
          ];
        })}
      </div>
      <div style={{ display: "flex", gap: 40, marginTop: 10, minHeight: 120 }}>
        {frame >= tMedian - 4 && (
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <span style={head}>Median error against GPS</span>
            <span style={{ ...cell, fontSize: 64, color: COLOR.foreground }}>
              <CountUp
                value={Number(s.medianErr)}
                decimals={1}
                start={tMedian}
              />
              <span style={{ fontSize: 30, color: COLOR.mutedForeground }}>
                {" "}
                km/h
              </span>
            </span>
          </div>
        )}
        {frame >= tOne - 4 && (
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <span style={head}>GPS inside its 90% range</span>
            <span style={{ ...cell, fontSize: 64, color: COLOR.destructive }}>
              <CountUp
                value={Number(s.covered)}
                decimals={0}
                start={tOne}
                duration={12}
              />
              <span style={{ fontSize: 30, color: COLOR.mutedForeground }}>
                {" "}
                of {s.measured}
              </span>
            </span>
          </div>
        )}
      </div>
    </div>
  );
};

export const Scene5: React.FC<Scene5Props> = ({ narration, rec }) => {
  const { fps } = useVideoConfig();
  const D = leadFrames(narration.id);
  const end = sceneFrames(narration);
  const at = (c: string) => D + frames(cueMs(narration, c), fps);
  const word = (w: string, c: string) =>
    D + frames(wordMs(narration, w, cueMs(narration, c)), fps);
  const tGates = at("gates");
  const tSays = word("says", "gates");
  const tPasses = at("passes");
  const tNarrow = at("narrow");
  const tMedian = word(FACTS.study.medianErr, "passes");
  const tOne = word(FACTS.study.covered, "narrow");
  const step = Math.round(0.7 * fps);
  const stage = mark(rec, "stage");
  const summary = mark(rec, "summary");
  const passes = FACTS.study.passes.map((p) => mark(rec, `pass_${p.clip}`));
  const sc: [number, number] = [
    stage.box.x + stage.box.w / 2,
    stage.box.y + stage.box.h / 2,
  ];
  const counts: [number, number] = [
    summary.box.x + summary.box.w / 2,
    summary.box.y + 90,
  ];
  const right: Cam = {
    focus: [1552, passes[0].box.y + passes[0].box.h / 2],
    zoom: 0.95,
  };
  const t0 = 0.3;
  const last = passes[passes.length - 1];
  void STREET_STUDY;
  return (
    <AbsoluteFill style={{ backgroundColor: COLOR.background }}>
      <RecSegment
        rec={rec}
        from={0}
        dur={tGates}
        recT={t0}
        cam={{ focus: [1280, 720], zoom: 0.75 }}
        camTo={{ focus: [1120, 620], zoom: 0.92 }}
        fade={0}
      />
      <RecSegment
        rec={rec}
        from={tGates}
        dur={tSays - tGates}
        recT={t0 + tGates / fps}
        cam={{ focus: sc, zoom: 1.22 }}
        camTo={{ focus: sc, zoom: 1.28 }}
      />
      <RecSegment
        rec={rec}
        from={tSays}
        dur={tPasses - tSays}
        recT={t0 + tSays / fps}
        cam={{ focus: counts, zoom: 1.3 }}
        camTo={{ focus: counts, zoom: 1.34 }}
      />
      {passes.map((m, i) => (
        <RecSegment
          key={i}
          rec={rec}
          from={tPasses + i * step}
          dur={step}
          recT={m.t + 0.05}
          hold
          cam={right}
          fade={i === 0 ? 8 : 4}
        />
      ))}
      <RecSegment
        rec={rec}
        from={tPasses + passes.length * step}
        dur={Math.max(1, end - tPasses - passes.length * step)}
        recT={last.t + 0.6}
        hold
        cam={right}
        fade={0}
      />
      <Sequence from={tPasses} layout="none">
        <AbsoluteFill style={{ background: "linear-gradient(90deg, rgba(10,12,15,0.97) 0%, rgba(10,12,15,0.92) 46%, rgba(10,12,15,0) 50%)" }} />
        <PassTable
          show={0}
          step={step}
          tMedian={tMedian - tPasses}
          tNarrow={tNarrow - tPasses}
          tOne={tOne - tPasses}
        />
      </Sequence>
      <Sequence from={D} layout="none">
        <Audio src={staticFile(narration.file)} />
      </Sequence>
      {/* The site's list of recorded studies runs along the bottom: darken it under the captions. */}
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(0deg, rgba(10,12,15,0.9) 0px, rgba(10,12,15,0) 230px)",
        }}
      />
      <Captions narration={narration} delay={D} />
    </AbsoluteFill>
  );
};
