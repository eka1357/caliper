import { Video } from "@remotion/media";
import {
  AbsoluteFill,
  Freeze,
  interpolate,
  Sequence,
  staticFile,
  useCurrentFrame,
} from "remotion";
import type { Pt } from "../lib/geometry.ts";
import type { Recording } from "../lib/media.ts";
import { ClipStage, type Rect, type Shot } from "./ClipStage.tsx";

/** A 30 fps file shown at any of its frames: map(frame of the scene) -> frame of the file. */
export const MappedVideo: React.FC<{
  file: string;
  map: (f: number) => number;
  width: number;
  height: number;
}> = ({ file, map, width, height }) => {
  const frame = useCurrentFrame();
  return (
    <Freeze frame={Math.max(0, Math.round(map(frame)))}>
      <Video src={staticFile(file)} muted style={{ width, height }} />
    </Freeze>
  );
};

export const FULL: Rect = [0, 0, 1920, 1080];

export type Cam = { focus: Pt; zoom: number };

const Faded: React.FC<{ fade: number; children: React.ReactNode }> = ({
  fade,
  children,
}) => {
  const frame = useCurrentFrame();
  const o =
    fade > 0
      ? interpolate(frame, [0, fade], [0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        })
      : 1;
  return <AbsoluteFill style={{ opacity: o }}>{children}</AbsoluteFill>;
};

/**
 * One stretch of a site recording: from scene frame `from` for `dur` frames the recording plays
 * (or holds) from `recT` seconds, the camera eases from `cam` to `camTo`, and it fades in.
 */
export const RecSegment: React.FC<{
  rec: Recording;
  from: number;
  dur: number;
  recT: number;
  hold?: boolean;
  /** Play a stretch of this many frames over and over (0: play straight through). */
  loop?: number;
  cam: Cam;
  camTo?: Cam;
  fade?: number;
  dim?: number;
  children?: React.ReactNode;
}> = ({
  rec,
  from,
  dur,
  recT,
  hold = false,
  loop = 0,
  cam,
  camTo,
  fade = 8,
  dim = 0,
  children,
}) => {
  const shots: Shot[] = [
    { at: 0, dur: 1, win: FULL, focus: cam.focus, zoom: cam.zoom, radius: 0 },
  ];
  if (camTo)
    shots.push({
      at: 0,
      dur: Math.max(2, dur),
      focus: camTo.focus,
      zoom: camTo.zoom,
    });
  return (
    <Sequence from={from} durationInFrames={dur} layout="none">
      <Faded fade={fade}>
        <ClipStage shots={shots} srcW={rec.width} srcH={rec.height}>
          {() => (
            <MappedVideo
              file={rec.file}
              map={(f) =>
                Math.min(
                  rec.frames - 1,
                  Math.round(recT * rec.fps) +
                    (hold ? 0 : loop > 0 ? f % loop : f),
                )
              }
              width={rec.width}
              height={rec.height}
            />
          )}
        </ClipStage>
        {dim > 0 && (
          <AbsoluteFill style={{ backgroundColor: `rgba(10,12,15,${dim})` }} />
        )}
        {children}
      </Faded>
    </Sequence>
  );
};

export const easeOutCubic = (p: number) =>
  1 - Math.pow(1 - Math.min(1, Math.max(0, p)), 3);

export const easeInOut = (p: number) => {
  const x = Math.min(1, Math.max(0, p));
  return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2;
};
