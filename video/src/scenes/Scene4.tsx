// Scene 4, how it works, on the live site's recording of C07's chain: the question, Muse Spark's
// spec, SAM's outlines playing, the number and its range, the checks, the audit's keyframes and
// verdict (the run's own files), and the audit's record on the evidence page.
import { Audio } from "@remotion/media";
import {
  AbsoluteFill,
  Img,
  Sequence,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { Captions } from "../components/Captions.tsx";
import { type Cam, RecSegment } from "../components/Footage.tsx";
import { KineticLine } from "../components/KineticLine.tsx";
import { SOURCES } from "../data/index.ts";
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

export type Scene4Props = {
  narration: Narration;
  chain: Recording;
  audit: Recording;
};

const center = (b: Box): [number, number] => [b.x + b.w / 2, b.y + b.h / 2];
const cam = (focus: [number, number], zoom: number): Cam => ({ focus, zoom });

/** The four frames Muse Spark audited (the run's keyframe files) and its verdict. */
const AuditFrames: React.FC<{ start: number }> = ({ start }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const run = SOURCES.c07;
  const names = run.meta.keyframes ?? [];
  const seen = (
    (run.result.artifacts.audit_call as { keyframes?: number[] } | undefined)
      ?.keyframes ?? []
  ).map(String);
  const audit = run.result.audit;
  const verdict = spring({
    frame: frame - start - 34,
    fps,
    config: CALM,
    durationInFrames: 22,
  });
  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
        gap: 44,
        paddingBottom: 90,
      }}
    >
      <div style={{ display: "flex", gap: 24 }}>
        {names.map((n, i) => {
          const p = spring({
            frame: frame - start - 6 * i,
            fps,
            config: CALM,
            durationInFrames: 22,
          });
          return (
            <div
              key={n}
              style={{
                display: "flex",
                flexDirection: "column",
                gap: 12,
                opacity: p,
                translate: `0px ${(1 - p) * 40}px`,
              }}
            >
              <Img
                src={staticFile(`keyframes/${run.result.run_id}/${n}`)}
                style={{
                  width: 400,
                  borderRadius: 12,
                  border: `1px solid ${COLOR.border}`,
                }}
              />
              <span
                style={{
                  fontFamily: FONT.mono,
                  fontSize: 24,
                  color: COLOR.mutedForeground,
                }}
              >
                frame {seen[i] ?? ""}
              </span>
            </div>
          );
        })}
      </div>
      {audit && (
        <div
          style={{
            display: "flex",
            alignItems: "baseline",
            gap: 18,
            maxWidth: 1500,
            opacity: verdict,
            fontFamily: FONT.sans,
          }}
        >
          <span
            style={{
              fontSize: 28,
              color: audit.approve ? COLOR.success : COLOR.destructive,
              border: `1px solid ${audit.approve ? COLOR.success : COLOR.destructive}88`,
              borderRadius: 8,
              padding: "4px 14px",
              whiteSpace: "nowrap",
            }}
          >
            {audit.approve ? "Approved" : "Vetoed"}
          </span>
          <span
            style={{ fontSize: 32, color: COLOR.foreground, lineHeight: 1.35 }}
          >
            {audit.reason}
          </span>
        </div>
      )}
    </AbsoluteFill>
  );
};

export const Scene4: React.FC<Scene4Props> = ({ narration, chain, audit }) => {
  const { fps } = useVideoConfig();
  const D = leadFrames(narration.id);
  const end = sceneFrames(narration);
  const at = (c: string) => D + frames(cueMs(narration, c), fps);
  const tPlans = D + frames(wordMs(narration, "plans"), fps);
  const [tSam, tPy, tChecks, tAudit, tVeto] = [
    "sam",
    "python",
    "checks",
    "audit",
    "veto",
  ].map(at);
  const key = narration.keys.find((k) => k.name === "k_rule");
  const q = mark(chain, "question");
  const stage = mark(chain, "stage");
  const spec = mark(chain, "spec");
  const result = mark(chain, "result");
  const checks = mark(chain, "checks");
  const aud = mark(chain, "audit");
  const card = mark(audit, "audit_card");
  const qc = center(q.box);
  const sc = center(stage.box);
  const both: [number, number] = [(qc[0] + sc[0]) / 2, (qc[1] + sc[1]) / 2];
  const specTop: [number, number] = [
    spec.box.x + spec.box.w / 2,
    spec.box.y + 260,
  ];
  const checksTop: [number, number] = [
    checks.box.x + checks.box.w / 2,
    checks.box.y + 420,
  ];
  const audTop: [number, number] = [aud.box.x + aud.box.w / 2, aud.box.y + 120];
  // The C07 clip plays on the stage between the Play click and the scroll: loop that stretch.
  const playFrom = stage.t + 1.4;
  const loop = Math.round((result.t - 2.2 - playFrom) * chain.fps);
  return (
    <AbsoluteFill style={{ backgroundColor: COLOR.background }}>
      <RecSegment
        rec={chain}
        from={0}
        dur={tPlans}
        recT={q.t + 0.5}
        hold
        cam={cam(qc, 1.25)}
        camTo={cam(both, 0.82)}
        fade={0}
      />
      <RecSegment
        rec={chain}
        from={tPlans}
        dur={tSam - tPlans}
        recT={spec.t + 0.3}
        hold
        cam={cam(specTop, 1.25)}
        camTo={cam(specTop, 1.33)}
      />
      <RecSegment
        rec={chain}
        from={tSam}
        dur={tPy - tSam}
        recT={playFrom}
        loop={loop}
        cam={cam(sc, 1.2)}
        camTo={cam(sc, 1.27)}
      />
      <RecSegment
        rec={chain}
        from={tPy}
        dur={tChecks - tPy}
        recT={result.t + 0.4}
        hold
        cam={cam(center(result.box), 1.3)}
        camTo={cam(center(result.box), 1.38)}
      />
      {key && (
        <KineticLine
          lines={["The model never", "writes the number."]}
          start={D + frames(key.startMs, fps)}
          end={tChecks - 2}
          size={130}
        />
      )}
      <RecSegment
        rec={chain}
        from={tChecks}
        dur={tAudit - tChecks}
        recT={checks.t + 0.3}
        hold
        cam={cam(checksTop, 1.12)}
        camTo={cam(checksTop, 1.18)}
      />
      <RecSegment
        rec={chain}
        from={tAudit}
        dur={tVeto - tAudit}
        recT={aud.t + 0.3}
        hold
        cam={cam(audTop, 1.2)}
        camTo={cam(audTop, 1.24)}
        dim={0.82}
      >
        <AuditFrames start={8} />
      </RecSegment>
      <RecSegment
        rec={audit}
        from={tVeto}
        dur={end - tVeto}
        recT={card.t + 0.2}
        hold
        cam={cam(center(card.box), 1.34)}
        camTo={cam(center(card.box), 1.4)}
      />
      <Sequence from={D} layout="none">
        <Audio src={staticFile(narration.file)} />
      </Sequence>
      <Captions narration={narration} delay={D} />
    </AbsoluteFill>
  );
};
