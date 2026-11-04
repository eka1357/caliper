// X cut, last part: how often Caliper answers on held-out benchmark videos, how close it is when it
// does, and the closing line. Values from results.json through src/data/facts.ts.
import { Audio } from "@remotion/media";
import {
  AbsoluteFill,
  Sequence,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { Background } from "../components/Background.tsx";
import { Captions } from "../components/Captions.tsx";
import { CountUp } from "../components/CountUp.tsx";
import { KineticLine } from "../components/KineticLine.tsx";
import { Squares } from "../components/Squares.tsx";
import { FACTS } from "../data/index.ts";
import { frames, wordMs, type Narration } from "../lib/media.ts";
import { leadFrames } from "../timeline.ts";
import { CALM, COLOR, FONT } from "../theme.ts";
import { Urls } from "./Scene8.tsx";

export type SceneX7Props = { narration: Narration };

export const SceneX7: React.FC<SceneX7Props> = ({ narration }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const h = FACTS.holdout;
  const D = leadFrames(narration.id);
  const word = (w: string, after = 0) =>
    D + frames(wordMs(narration, w, after), fps);
  const tAns = word(h.answered);
  const afterWhen = wordMs(narration, "When");
  const tCal = word(h.within10Cal, afterWhen);
  const tMuse = word(h.within10Muse, afterWhen);
  const key = narration.keys.find((k) => k.name === "k_line");
  const tKey = key ? D + frames(key.startMs, fps) : 100000;
  const p = spring({ frame, fps, config: CALM, durationInFrames: 18 });
  return (
    <AbsoluteFill>
      <Background />
      <AbsoluteFill
        style={{
          justifyContent: "center",
          paddingLeft: 200,
          gap: 50,
          opacity: p,
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "baseline",
            gap: 24,
            fontFamily: FONT.sans,
          }}
        >
          <span style={{ fontSize: 40, color: COLOR.foreground }}>
            On held-out benchmark videos it answers
          </span>
          <span
            style={{
              fontFamily: FONT.mono,
              fontSize: 96,
              color: COLOR.foreground,
              fontVariantNumeric: "tabular-nums",
            }}
          >
            <CountUp value={Number(h.answered)} decimals={0} start={tAns} />
            <span style={{ fontSize: 44, color: COLOR.mutedForeground }}>
              {" "}
              of {h.n}
            </span>
          </span>
        </div>
        <Squares
          n={Number(h.nAnswered)}
          k={Number(h.within10Cal)}
          start={tCal}
          color={COLOR.track}
          label="of its answers within 10%"
        />
        <Squares
          n={Number(h.nAnswered)}
          k={Number(h.within10Muse)}
          start={tMuse}
          color={COLOR.mutedForeground}
          label="Muse Spark alone, same questions"
        />
      </AbsoluteFill>
      {key && (
        <KineticLine
          lines={["It would rather", "say no than guess."]}
          start={tKey}
          size={132}
          lift={80}
          dim={0.93}
        />
      )}
      <Urls start={tKey + 40} repo={false} />
      <Sequence from={D} layout="none">
        <Audio src={staticFile(narration.file)} />
      </Sequence>
      <Captions narration={narration} delay={D} />
    </AbsoluteFill>
  );
};
