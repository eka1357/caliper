// Scene 7, the honest numbers on the holdout split: official MRA (refusals count as misses, claim
// H1 failed), then, on the questions Caliper answered, within 10% and the 90% range held. Values
// from results.json through src/data/facts.ts; the backdrop is the live site's evidence page.
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
import { RecSegment } from "../components/Footage.tsx";
import { Squares } from "../components/Squares.tsx";
import { FACTS } from "../data/index.ts";
import {
  cueMs,
  frames,
  mark,
  wordMs,
  type Box,
  type Narration,
  type Recording,
} from "../lib/media.ts";
import { leadFrames, sceneFrames } from "../timeline.ts";
import { CALM, COLOR, FONT } from "../theme.ts";

export type Scene7Props = { narration: Narration; rec: Recording };

const center = (b: Box): [number, number] => [b.x + b.w / 2, b.y + b.h / 2];

const Official: React.FC<{ tCal: number; tMuse: number }> = ({
  tCal,
  tMuse,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const h = FACTS.holdout;
  const p = spring({ frame, fps, config: CALM, durationInFrames: 20 });
  const big: React.CSSProperties = {
    fontFamily: FONT.mono,
    fontSize: 120,
    lineHeight: 1,
    fontVariantNumeric: "tabular-nums",
  };
  const label: React.CSSProperties = {
    fontFamily: FONT.sans,
    fontSize: 30,
    color: COLOR.mutedForeground,
  };
  return (
    <div
      style={{
        position: "absolute",
        right: 64,
        top: 150,
        width: 560,
        padding: "30px 36px",
        boxSizing: "border-box",
        borderRadius: 16,
        border: `1px solid ${COLOR.border}`,
        backgroundColor: "rgba(12,15,19,0.95)",
        display: "flex",
        flexDirection: "column",
        gap: 26,
        opacity: p,
      }}
    >
      <div
        style={{ fontFamily: FONT.sans, fontSize: 32, color: COLOR.foreground }}
      >
        Official MRA, holdout
      </div>
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 6,
          opacity: frame >= tCal - 6 ? 1 : 0,
        }}
      >
        <span style={label}>Caliper</span>
        <span style={{ ...big, color: COLOR.primary }}>
          <CountUp value={h.calMraNum} decimals={1} start={tCal} />
        </span>
      </div>
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 6,
          opacity: frame >= tMuse - 6 ? 1 : 0,
        }}
      >
        <span style={label}>Muse Spark alone</span>
        <span style={{ ...big, color: COLOR.mutedForeground }}>
          <CountUp value={h.museMraNum} decimals={1} start={tMuse} />
        </span>
      </div>
      <div style={{ ...label, fontSize: 26 }}>A refusal counts as a miss.</div>
    </div>
  );
};

export const Scene7: React.FC<Scene7Props> = ({ narration, rec }) => {
  const { fps } = useVideoConfig();
  const D = leadFrames(narration.id);
  const end = sceneFrames(narration);
  const h = FACTS.holdout;
  const at = (c: string) => D + frames(cueMs(narration, c), fps);
  const word = (w: string, c: string) =>
    D + frames(wordMs(narration, w, cueMs(narration, c)), fps);
  const tH1 = at("h1");
  const tWithin = at("within");
  const chart = mark(rec, "mra_chart");
  const h1 = mark(rec, "h1_card");
  const closer = mark(rec, "closer_card");
  return (
    <AbsoluteFill style={{ backgroundColor: COLOR.background }}>
      <RecSegment
        rec={rec}
        from={0}
        dur={tH1}
        recT={chart.t + 0.8}
        hold
        cam={{ focus: center(chart.box), zoom: 1.0 }}
        camTo={{ focus: center(chart.box), zoom: 1.05 }}
        fade={0}
      >
        <Official
          tCal={word(h.calMra, "official")}
          tMuse={word(h.museMra, "official")}
        />
      </RecSegment>
      <RecSegment
        rec={rec}
        from={tH1}
        dur={tWithin - tH1}
        recT={h1.t + 0.3}
        hold
        cam={{ focus: center(h1.box), zoom: 1.4 }}
        camTo={{ focus: center(h1.box), zoom: 1.46 }}
      />
      <RecSegment
        rec={rec}
        from={tWithin}
        dur={end - tWithin}
        recT={closer.t + 0.3}
        hold
        cam={{ focus: center(closer.box), zoom: 1.2 }}
        dim={0.88}
      >
        <AbsoluteFill
          style={{ justifyContent: "center", paddingLeft: 200, gap: 46 }}
        >
          <div
            style={{
              fontFamily: FONT.sans,
              fontSize: 36,
              color: COLOR.foreground,
            }}
          >
            When Caliper answers: {h.nAnswered} holdout questions
          </div>
          <Squares
            n={Number(h.nAnswered)}
            k={Number(h.within10Cal)}
            start={word(h.within10Cal, "within") - tWithin}
            color={COLOR.track}
            label="Caliper within 10%"
          />
          <Squares
            n={Number(h.nAnswered)}
            k={Number(h.within10Muse)}
            start={word(h.within10Muse, "within") - tWithin}
            color={COLOR.mutedForeground}
            label="Muse Spark alone within 10%, same questions"
          />
          <Squares
            n={Number(h.rangeAnswered)}
            k={Number(h.rangeHeld)}
            start={word(h.rangeHeld, "range") - tWithin}
            color={COLOR.primary}
            label="Caliper's 90% range held"
          />
        </AbsoluteFill>
      </RecSegment>
      <Sequence from={D} layout="none">
        <Audio src={staticFile(narration.file)} />
      </Sequence>
      <Captions narration={narration} delay={D} />
    </AbsoluteFill>
  );
};
