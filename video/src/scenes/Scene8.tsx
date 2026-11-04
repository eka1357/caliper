// Scene 8, the close: the key line over the live site's landing page, then the live URL and repo.
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
import { RecSegment } from "../components/Footage.tsx";
import { KineticLine } from "../components/KineticLine.tsx";
import { LIVE_URL, REPO_URL } from "../data/index.ts";
import { frames, mark, type Narration, type Recording } from "../lib/media.ts";
import { leadFrames, sceneFrames } from "../timeline.ts";
import { CALM, COLOR, FONT } from "../theme.ts";

export type Scene8Props = { narration: Narration; rec: Recording | null };

export const Urls: React.FC<{ start: number; repo?: boolean }> = ({
  start,
  repo = true,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = spring({
    frame: frame - start,
    fps,
    config: CALM,
    durationInFrames: 24,
  });
  if (frame < start) return null;
  return (
    <AbsoluteFill
      style={{
        justifyContent: "flex-end",
        alignItems: "center",
        paddingBottom: 190,
      }}
    >
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 18,
          opacity: p,
          translate: `0px ${(1 - p) * 20}px`,
        }}
      >
        <span
          style={{
            fontFamily: FONT.mono,
            fontSize: 52,
            color: COLOR.foreground,
          }}
        >
          {LIVE_URL}
        </span>
        {repo && (
          <span
            style={{
              fontFamily: FONT.mono,
              fontSize: 36,
              color: COLOR.mutedForeground,
            }}
          >
            {REPO_URL}
          </span>
        )}
      </div>
    </AbsoluteFill>
  );
};

export const Scene8: React.FC<Scene8Props> = ({ narration, rec }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const D = leadFrames(narration.id);
  const end = sceneFrames(narration);
  const key = narration.keys.find((k) => k.name === "k_line");
  const out = interpolate(frame, [end - 24, end - 1], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const hero = rec ? mark(rec, "hero") : null;
  return (
    <AbsoluteFill style={{ backgroundColor: COLOR.background }}>
      {rec && hero && (
        <RecSegment
          rec={rec}
          from={0}
          dur={end}
          recT={hero.t + 1.0}
          hold
          cam={{ focus: [1280, 720], zoom: 0.75 }}
          camTo={{ focus: [1280, 700], zoom: 0.8 }}
          fade={0}
          dim={0.45}
        />
      )}
      {key && (
        <KineticLine
          lines={["It would rather", "say no than guess."]}
          start={D + frames(key.startMs, fps)}
          size={132}
          lift={80}
          dim={0.9}
        />
      )}
      <Urls start={D + frames(narration.durationMs, fps) + 8} />
      <Sequence from={D} layout="none">
        <Audio src={staticFile(narration.file)} />
      </Sequence>
      <AbsoluteFill style={{ backgroundColor: "#000", opacity: out }} />
    </AbsoluteFill>
  );
};
