// Scene 6, an AI agent calling Caliper over MCP: the captured JSON-RPC session
// (data/mcp/session.json, scripts/mcp_capture.py) typed in and answered. Nothing here is typed by
// hand: requests and results are the captured messages, printed by code.
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
import session from "../../data/mcp/session.json";
import { Background } from "../components/Background.tsx";
import { Captions } from "../components/Captions.tsx";
import { cueMs, frames, type Narration } from "../lib/media.ts";
import { leadFrames } from "../timeline.ts";
import { CALM, COLOR, FONT } from "../theme.ts";

export type Scene6Props = { narration: Narration };

type Json = null | boolean | number | string | Json[] | { [k: string]: Json };
type Msg = {
  direction: string;
  message: {
    id?: number;
    method?: string;
    params?: { name?: string; arguments?: Json };
    result?: {
      structuredContent?: Record<string, Json>;
      tools?: { name: string }[];
    };
  };
};
type Line = { text: string; hl: boolean };

const MESSAGES = (session as unknown as { messages: Msg[] }).messages;
const HIGHLIGHT = new Set([
  "status",
  "value",
  "unit",
  "interval_90",
  "speed_kmh",
  "interval_90_kmh",
  "vehicles_measured",
]);

function call(name: string) {
  const req = MESSAGES.find(
    (m) => m.message.method === "tools/call" && m.message.params?.name === name,
  )?.message;
  const res = MESSAGES.find(
    (m) => m.direction === "server_to_client" && req && m.message.id === req.id,
  )?.message;
  if (!req || !res?.result?.structuredContent)
    throw new Error(`no captured ${name} call`);
  return {
    args: req.params?.arguments ?? null,
    out: res.result.structuredContent,
  };
}

/** JSON with short objects and arrays of plain values kept on one line. */
function lines(v: Json, pad = "", key?: string, comma = false): Line[] {
  const k = key === undefined ? "" : `${JSON.stringify(key)}: `;
  const hl = key !== undefined && HIGHLIGHT.has(key);
  const flat = JSON.stringify(v);
  const end = comma ? "," : "";
  if (
    v === null ||
    typeof v !== "object" ||
    flat.length <= 56 ||
    (Array.isArray(v) && v.every((x) => typeof x !== "object"))
  ) {
    return [
      {
        text: `${pad}${k}${flat.replace(/,(?=[[{"\d-])/g, ", ").replace(/":/g, '": ')}${end}`,
        hl,
      },
    ];
  }
  const entries: [string | undefined, Json][] = Array.isArray(v)
    ? v.map((x) => [undefined, x])
    : Object.entries(v);
  const [open, close] = Array.isArray(v) ? ["[", "]"] : ["{", "}"];
  return [
    { text: `${pad}${k}${open}`, hl: false },
    ...entries.flatMap(([kk, x], i) =>
      lines(x, `${pad}  `, kk, i < entries.length - 1),
    ),
    { text: `${pad}${close}${end}`, hl: false },
  ];
}

const pick = (o: Record<string, Json>, keys: string[]): Json =>
  Object.fromEntries(keys.filter((x) => x in o).map((x) => [x, o[x]]));

const Panel: React.FC<{
  x: number;
  tool: string;
  request: Line[];
  result: Line[];
  summary: string;
  tReq: number;
  tRes: number;
}> = ({ x, tool, request, result, summary, tReq, tRes }) => {
  const frame = useCurrentFrame();
  const total = request.reduce((n, l) => n + l.text.length, 0);
  const typed = Math.floor(
    interpolate(frame, [tReq, tReq + 36], [0, total], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    }),
  );
  const res = interpolate(frame, [tRes, tRes + 12], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  let left = typed;
  const row: React.CSSProperties = {
    fontFamily: FONT.mono,
    fontSize: 18,
    lineHeight: "25px",
    whiteSpace: "pre-wrap",
    wordBreak: "break-all",
  };
  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: 176,
        width: 880,
        height: 840, // fits the study call and its whole result, summary included
        boxSizing: "border-box",
        padding: "22px 26px",
        borderRadius: 16,
        border: `1px solid ${COLOR.border}`,
        backgroundColor: "#0D1014",
        boxShadow: "0 30px 80px rgba(0,0,0,0.5)",
        opacity: frame >= tReq - 10 ? 1 : 0.35,
        overflow: "hidden",
      }}
    >
      <div style={{ ...row, color: COLOR.primary, marginBottom: 8 }}>
        → tools/call {tool}
      </div>
      {request.map((l, i) => {
        const shown = l.text.slice(0, Math.max(0, left));
        left -= l.text.length;
        return (
          <div
            key={i}
            style={{ ...row, color: COLOR.foreground, minHeight: 25 }}
          >
            {shown}
          </div>
        );
      })}
      <div style={{ opacity: res, marginTop: 16 }}>
        <div style={{ ...row, color: COLOR.track, marginBottom: 8 }}>
          ← result
        </div>
        {result.map((l, i) => (
          <div
            key={i}
            style={{
              ...row,
              color: l.hl ? COLOR.primary : COLOR.mutedForeground,
            }}
          >
            {l.hl ? (
              <span
                style={{
                  backgroundColor: "rgba(255,178,36,0.14)",
                  borderRadius: 4,
                  padding: "0 4px",
                }}
              >
                {l.text}
              </span>
            ) : (
              l.text
            )}
          </div>
        ))}
        <div
          style={{
            ...row,
            color: COLOR.success,
            marginTop: 10,
            fontFamily: FONT.sans,
            fontSize: 22,
          }}
        >
          {summary}
        </div>
      </div>
    </div>
  );
};

export const Scene6: React.FC<Scene6Props> = ({ narration }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const D = leadFrames(narration.id);
  const at = (c: string) => D + frames(cueMs(narration, c), fps);
  const m = call("measure");
  const s = call("study");
  const tools =
    MESSAGES.find((x) => x.message.result?.tools)?.message.result?.tools?.map(
      (t) => t.name,
    ) ?? [];
  const checks = (m.out.checks as { passed: boolean }[] | undefined) ?? [];
  const audit = m.out.audit as { approve?: boolean } | null;
  const readings = (
    (s.out.readings as Record<string, Json>[] | undefined) ?? []
  ).map((r) =>
    pick(
      r,
      r.status === "measured"
        ? ["vehicle_id", "status", "speed_kmh", "interval_90_kmh"]
        : ["vehicle_id", "status", "reason"],
    ),
  );
  const tM = at("measure");
  const tS = at("studycall");
  const tR = at("result");
  const sp = (t: number) => spring({ frame: frame - t, fps, config: CALM, durationInFrames: 30 });
  const [L, R, Z] = [504, 1416, 1.28]; // centres of the two panels, and the push
  let fx = 960 + (L - 960) * sp(tM);
  fx += (R - fx) * sp(tS);
  fx += (L - fx) * sp(tR);
  fx += (R - fx) * sp(tR + 75);
  const zc = 1 + (Z - 1) * sp(tM);
  // Vertical focus: the top of the panels, then lower for the study's longer result so its
  // readings and summary sit above the captions.
  const fy = 576 + (724 - 576) * sp(tR + 75);
  const camStyle: React.CSSProperties = { transformOrigin: "0 0", translate: `${960 - fx * zc}px ${600 - fy * zc}px`, scale: String(zc) };
  const title = interpolate(frame, [0, 14], [0, 1], {
    extrapolateRight: "clamp",
  });
  const toolsIn = interpolate(frame, [D + 30, D + 44], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <AbsoluteFill>
      <Background />
      <div style={{ position: "absolute", left: 64, top: 50, opacity: title * (1 - 0.85 * sp(tM)) }}>
        <div
          style={{
            fontFamily: FONT.display,
            fontSize: 72,
            color: COLOR.foreground,
            lineHeight: 1,
          }}
        >
          An AI agent calling Caliper over MCP
        </div>
        <div
          style={{
            fontFamily: FONT.mono,
            fontSize: 22,
            color: COLOR.mutedForeground,
            marginTop: 14,
            opacity: toolsIn,
          }}
        >
          JSON-RPC over stdio, as captured · tools/list → {tools.join(", ")}
        </div>
      </div>
      <AbsoluteFill style={camStyle}>
      <Panel
        x={64}
        tool="measure"
        request={lines(m.args)}
        result={lines(pick(m.out, ["status", "value", "unit", "interval_90"]))}
        summary={`${checks.filter((c) => c.passed).length} of ${checks.length} checks passed · audit ${audit?.approve ? "approved" : "vetoed"}`}
        tReq={at("measure")}
        tRes={at("result")}
      />
      <Panel
        x={976}
        tool="study"
        request={lines(s.args)}
        result={lines({
          ...(pick(s.out, ["vehicles_seen", "vehicles_measured"]) as Record<
            string,
            Json
          >),
          readings,
        })}
        summary={`${String(s.out.vehicles_measured)} of ${String(s.out.vehicles_seen)} vehicles measured · the other says why`}
        tReq={at("studycall")}
        tRes={at("result") + 20}
      />
      </AbsoluteFill>
      <Sequence from={D} layout="none">
        <Audio src={staticFile(narration.file)} />
      </Sequence>
      <Captions narration={narration} delay={D} />
    </AbsoluteFill>
  );
};
