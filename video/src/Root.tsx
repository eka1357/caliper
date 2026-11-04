import { Composition } from "remotion";
import { Demo, demoFrames, type Media, XCut, xFrames } from "./Demo.tsx";
import {
  loadFootage,
  loadNarration,
  loadRecording,
  type Footage,
  type Narration,
  type Recording,
} from "./lib/media.ts";

async function load(
  ids: string[],
  clips: string[],
  recs: string[],
  signal?: AbortSignal,
) {
  const n: Record<string, Narration> = {};
  const f: Record<string, Footage> = {};
  const r: Record<string, Recording> = {};
  await Promise.all([
    ...ids.map(async (id) => (n[id] = await loadNarration(id, signal))),
    ...clips.map(async (c) => (f[c] = await loadFootage(c, signal))),
    ...recs.map(async (x) => (r[x] = await loadRecording(x, signal))),
  ]);
  return { n, f, r } satisfies Media;
}

export const RemotionRoot: React.FC = () => (
  <>
    <Composition
      id="Demo"
      component={Demo}
      width={1920}
      height={1080}
      fps={30}
      durationInFrames={5340}
      defaultProps={{ n: null, f: null, r: null }}
      calculateMetadata={async ({ abortSignal }) => {
        const m = await load(
          ["s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8"],
          ["c07", "a14", "a08"],
          [
            "s3_refusal",
            "s4_chain",
            "s4_audit",
            "s5_study",
            "s7_results",
            "s8_landing",
          ],
          abortSignal,
        );
        return {
          props: m,
          durationInFrames: demoFrames(m.n),
          defaultOutName: "caliper_demo",
        };
      }}
    />
    <Composition
      id="XCut"
      component={XCut}
      width={1920}
      height={1080}
      fps={30}
      durationInFrames={1200}
      defaultProps={{ n: null, f: null, r: null }}
      calculateMetadata={async ({ abortSignal }) => {
        const m = await load(
          ["x1", "x3", "x7"],
          ["c07", "a08"],
          ["s3_refusal"],
          abortSignal,
        );
        return {
          props: m,
          durationInFrames: xFrames(m.n),
          defaultOutName: "caliper_x_cut",
        };
      }}
    />
  </>
);
