// Narration: video/narration.md -> spoken text with every {token} filled from the data, then
// ElevenLabs audio with character timings (captions and cue times).
//
//   node --no-warnings scripts/narration.mts resolve            fill tokens, rewrite the "Spoken
//                                                               text" block of narration.md ($0)
//   node --no-warnings scripts/narration.mts generate s1 s2 ... one MP3 + timings per scene into
//                                                               public/audio/ (costs characters)
import { execFileSync } from "node:child_process";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { buildFacts, token, type Sources } from "../src/data/facts.ts";
import { tts, type Alignment, type TtsSettings } from "./elevenlabs.mts";

const VIDEO = resolve(import.meta.dirname, "..");
const ROOT = resolve(VIDEO, "..");
const NARRATION = resolve(VIDEO, "narration.md");
const AUDIO = resolve(VIDEO, "public", "audio");
const RAW = resolve(AUDIO, "raw"); // ElevenLabs takes as returned

// River: relaxed, neutral, calm (ElevenLabs premade voice).
export const VOICE: TtsSettings = {
  voiceId: "SAz9YHcvj6GT2YYXdXww",
  modelId: "eleven_multilingual_v2",
  stability: 0.5,
  similarityBoost: 0.75,
  style: 0,
  seed: 1104,
};

// The voice reads plain prose much faster than lines full of numbers (first takes, 2026-11-04:
// s1, s2 and s7 near 145 words a minute without pauses, s6 near 210). ElevenLabs' own speed
// setting slows the prose scenes toward the same calm pace; nothing is time-stretched afterwards.
const PACE: Record<string, number> = { s3: 0.8, s4: 0.88, s5: 0.82, s6: 0.8, s8: 0.7, x3: 0.85 };
// The closing line stands alone (no neighbouring text), so it is read as an ending.
const STANDALONE = new Set(["s8"]);

const SEQUENCES = [
  ["s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8"],
  ["x1", "x3", "x7"],
];

function json<T>(rel: string): T {
  return JSON.parse(readFileSync(resolve(ROOT, rel), "utf8")) as T;
}

export function loadSources(): Sources {
  const study: Sources["study"] = {};
  for (const n of [11, 12, 13, 14, 15, 16]) study[`A${n}`] = json(`web/public/runs/study-a${n}/run.json`);
  return {
    results: json("web/public/results.json"),
    c07: json("web/public/runs/field-c07/run.json"),
    a14: json("web/public/runs/field-a14/run.json"),
    a08: json("web/public/runs/field-a08/run.json"),
    study,
  };
}

type Scene = {
  id: string;
  spoken: string; // what the voice reads
  display: string; // what the captions show (same words; aliases differ)
  cues: Record<string, number>; // cue -> character index in `spoken`
  keys: { name: string; start: number; end: number }[]; // key lines, character ranges in `spoken`
};

/** Template lines of each "## id · title" section (the lines that start with "> "). */
function templates(md: string): Map<string, string> {
  const out = new Map<string, string>();
  let id: string | null = null;
  for (const line of md.split(/\r?\n/)) {
    const h = /^## (\w+) ·/.exec(line);
    if (h) {
      id = h[1];
      continue;
    }
    if (line.startsWith("## ")) id = null;
    if (id && line.startsWith("> ")) out.set(id, `${out.get(id) ?? ""} ${line.slice(2).trim()}`.trim());
  }
  return out;
}

function parse(id: string, template: string, facts: ReturnType<typeof buildFacts>): Scene {
  const filled = template.replace(/\{([\w.]+)\}/g, (_, path: string) => token(facts, path));
  let spoken = "";
  let display = "";
  const cues: Scene["cues"] = {};
  const open: Record<string, number> = {};
  const keys: Scene["keys"] = [];
  const re = /\[@(\/?)(\w+)\]|\[\[([^|\]]+)\|([^\]]+)\]\]/g;
  let last = 0;
  for (let m = re.exec(filled); m; m = re.exec(filled)) {
    const text = filled.slice(last, m.index);
    spoken += text;
    display += text;
    last = re.lastIndex;
    if (m[3] !== undefined) {
      if (/\s/.test(m[3]) || /\s/.test(m[4])) throw new Error(`${id}: an alias must be one word`);
      display += m[3];
      spoken += m[4];
    } else if (m[1] === "/") {
      keys.push({ name: m[2], start: open[m[2]], end: spoken.length });
    } else if (m[2].startsWith("k_")) {
      open[m[2]] = spoken.length;
      cues[m[2]] = spoken.length;
    } else {
      cues[m[2]] = spoken.length;
    }
  }
  spoken += filled.slice(last);
  display += filled.slice(last);
  const squash = (s: string) => s.replace(/\s+/g, " ");
  // Positions were taken before squashing; squash only runs of spaces after them, so shift them.
  const shift = (i: number) => squash(spoken.slice(0, i)).length;
  for (const k of Object.keys(cues)) cues[k] = shift(cues[k]);
  for (const k of keys) {
    k.start = shift(k.start);
    k.end = shift(k.end);
  }
  spoken = squash(spoken).trim();
  display = squash(display).trim();
  if (spoken.split(" ").length !== display.split(" ").length) throw new Error(`${id}: word counts differ`);
  return { id, spoken, display, cues, keys };
}

export function scenes(): Map<string, Scene> {
  const facts = buildFacts(loadSources());
  const out = new Map<string, Scene>();
  for (const [id, t] of templates(readFileSync(NARRATION, "utf8"))) out.set(id, parse(id, t, facts));
  return out;
}

/** Start and end time of each character of `spoken`, from the alignment. */
function charTimes(spoken: string, a: Alignment): { start: number[]; end: number[] } {
  const chars = a.characters.join("");
  if (chars === spoken) return { start: a.character_start_times_seconds, end: a.character_end_times_seconds };
  // Fall back to matching non-space characters in order (the service may normalise spacing).
  const start: number[] = new Array(spoken.length).fill(NaN);
  const end: number[] = new Array(spoken.length).fill(NaN);
  let j = 0;
  for (let i = 0; i < spoken.length; i++) {
    if (spoken[i] === " ") continue;
    while (j < a.characters.length && a.characters[j] !== spoken[i]) j++;
    if (j >= a.characters.length) throw new Error("alignment does not match the text");
    start[i] = a.character_start_times_seconds[j];
    end[i] = a.character_end_times_seconds[j];
    j++;
  }
  for (let i = 0; i < spoken.length; i++) {
    if (Number.isNaN(start[i])) {
      start[i] = i > 0 ? end[i - 1] : 0;
      end[i] = start[i];
    }
  }
  return { start, end };
}

function timings(scene: Scene, a: Alignment, durationS: number, voice: TtsSettings) {
  const t = charTimes(scene.spoken, a);
  const ms = (s: number) => Math.round(s * 1000);
  const words: { text: string; startMs: number; endMs: number }[] = [];
  const shown = scene.display.split(" ");
  let i = 0;
  let w = 0;
  for (const word of scene.spoken.split(" ")) {
    words.push({ text: shown[w], startMs: ms(t.start[i]), endMs: ms(t.end[i + word.length - 1]) });
    i += word.length + 1;
    w++;
  }
  const at = (idx: number) => {
    let k = Math.min(idx, scene.spoken.length - 1);
    while (k < scene.spoken.length - 1 && scene.spoken[k] === " ") k++;
    return ms(t.start[k]);
  };
  return {
    id: scene.id,
    text: scene.display,
    spoken: scene.spoken,
    durationMs: ms(durationS),
    words,
    cues: Object.fromEntries(Object.entries(scene.cues).map(([k, v]) => [k, at(v)])),
    keys: scene.keys.map((k) => ({ name: k.name, startMs: at(k.start), endMs: ms(t.end[k.end - 1]) })),
    voice,
    characters: scene.spoken.length,
  };
}

// "Extend pauses, never speed up speech": the least silence after a sentence, after a colon, and
// before a key line (the large-type beat). Silence is only inserted, at the middle of the gap
// between two words, so speech itself is never cut or stretched.
const GAP_SENTENCE_MS = 650;
const GAP_COLON_MS = 450;
const GAP_KEY_MS = 600;

type Timings = ReturnType<typeof timings>;

/** Raw take (raw/<id>.mp3 + raw/<id>.json) -> <id>.wav and <id>.json with the longer pauses. */
function breathe(id: string): Timings & { file: string; insertedMs: number } {
  const raw = JSON.parse(readFileSync(resolve(RAW, `${id}.json`), "utf8")) as Timings;
  const w = raw.words;
  const keyStarts = new Set(raw.keys.map((k) => k.startMs));
  const cuts: { atMs: number; addMs: number }[] = [];
  for (let i = 0; i < w.length - 1; i++) {
    const gap = w[i + 1].startMs - w[i].endMs;
    const last = w[i].text.slice(-1);
    let want = ".?!".includes(last) ? GAP_SENTENCE_MS : last === ":" ? GAP_COLON_MS : 0;
    if (keyStarts.has(w[i + 1].startMs)) want = Math.max(want, GAP_KEY_MS);
    if (want > gap) cuts.push({ atMs: Math.round((w[i].endMs + w[i + 1].startMs) / 2), addMs: want - gap });
  }
  const shift = (t: number) => t + cuts.filter((c) => c.atMs <= t).reduce((s, c) => s + c.addMs, 0);
  const wav = resolve(AUDIO, `${id}.wav`);
  const src = resolve(RAW, `${id}.mp3`);
  if (cuts.length === 0) {
    execFileSync("ffmpeg", ["-v", "error", "-y", "-i", src, "-ar", "44100", "-c:a", "pcm_s16le", wav]);
  } else {
    const n = cuts.length;
    const sec = (ms: number) => (ms / 1000).toFixed(3);
    const parts: string[] = [`[0:a]asplit=${n + 1}${Array.from({ length: n + 1 }, (_, i) => `[i${i}]`).join("")}`];
    const order: string[] = [];
    for (let i = 0; i <= n; i++) {
      const from = i === 0 ? "" : `start=${sec(cuts[i - 1].atMs)}`;
      const to = i === n ? "" : `end=${sec(cuts[i].atMs)}`;
      parts.push(`[i${i}]atrim=${[from, to].filter(Boolean).join(":")},asetpts=N/SR/TB[a${i}]`);
      order.push(`[a${i}]`);
      if (i < n) {
        parts.push(`aevalsrc=0:d=${sec(cuts[i].addMs)}:s=44100[z${i}]`);
        order.push(`[z${i}]`);
      }
    }
    parts.push(`${order.join("")}concat=n=${2 * n + 1}:v=0:a=1[out]`);
    execFileSync("ffmpeg", [
      "-v", "error", "-y", "-i", src, "-filter_complex", parts.join(";"), "-map", "[out]",
      "-ar", "44100", "-c:a", "pcm_s16le", wav,
    ]); // fmt: skip
  }
  const insertedMs = cuts.reduce((s, c) => s + c.addMs, 0);
  const paced = {
    ...raw,
    file: `audio/${id}.wav`,
    durationMs: Math.round(durationOf(wav) * 1000),
    words: w.map((x) => ({ ...x, startMs: shift(x.startMs), endMs: shift(x.endMs) })),
    cues: Object.fromEntries(Object.entries(raw.cues).map(([k, v]) => [k, shift(v)])),
    keys: raw.keys.map((k) => ({ ...k, startMs: shift(k.startMs), endMs: shift(k.endMs) })),
    insertedMs,
  };
  writeFileSync(resolve(AUDIO, `${id}.json`), JSON.stringify(paced, null, 1), "utf8");
  return paced;
}

function durationOf(file: string): number {
  const out = execFileSync("ffprobe", [
    "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", file,
  ]).toString(); // fmt: skip
  return Number(out.trim());
}

function rewriteSpokenBlock(all: Map<string, Scene>): void {
  const md = readFileSync(NARRATION, "utf8");
  const start = md.indexOf("<!-- spoken:start");
  const end = md.indexOf("<!-- spoken:end -->");
  if (start < 0 || end < 0) throw new Error("narration.md has no spoken block");
  const head = md.slice(0, md.indexOf("\n", start) + 1);
  let words = 0;
  const lines: string[] = [];
  for (const s of all.values()) {
    const n = s.display.split(" ").length;
    if (s.id.startsWith("s")) words += n;
    lines.push(`**${s.id}** (${n} words, ${s.spoken.length} characters): ${s.display}`, "");
  }
  const facts = buildFacts(loadSources());
  lines.push(`Main cut: ${words} words. Data generated ${facts.generatedUtc}.`, "");
  writeFileSync(NARRATION, `${head}\n${lines.join("\n")}${md.slice(end)}`, "utf8");
}

async function main(): Promise<void> {
  const [cmd, ...ids] = process.argv.slice(2);
  const all = scenes();
  if (cmd === "resolve") {
    rewriteSpokenBlock(all);
    for (const s of all.values()) console.log(`${s.id}: ${s.display}\n   cues ${JSON.stringify(s.cues)}`);
    return;
  }
  if (cmd === "breathe") {
    for (const id of ids) {
      const p = breathe(id);
      console.log(`${id}: ${(p.durationMs / 1000).toFixed(2)} s (+${(p.insertedMs / 1000).toFixed(2)} s of pauses)`);
    }
    return;
  }
  if (cmd !== "generate" || ids.length === 0) {
    console.log("usage: resolve | generate <scene ids> | breathe <scene ids>");
    return;
  }
  mkdirSync(RAW, { recursive: true });
  let total = 0;
  for (const id of ids) {
    const s = all.get(id);
    if (!s) throw new Error(`no scene ${id} in narration.md`);
    const seq = SEQUENCES.find((q) => q.includes(id)) ?? [id];
    const k = seq.indexOf(id);
    const alone = STANDALONE.has(id);
    const prev = !alone && k > 0 ? all.get(seq[k - 1])?.spoken : undefined;
    const next = !alone && k < seq.length - 1 ? all.get(seq[k + 1])?.spoken : undefined;
    const voice: TtsSettings = { ...VOICE, ...(PACE[id] ? { speed: PACE[id] } : {}) };
    const { audio, alignment } = await tts(s.spoken, voice, prev, next);
    const mp3 = resolve(RAW, `${id}.mp3`);
    writeFileSync(mp3, audio);
    const t = timings(s, alignment, durationOf(mp3), voice);
    writeFileSync(resolve(RAW, `${id}.json`), JSON.stringify(t, null, 1), "utf8");
    const p = breathe(id);
    total += s.spoken.length;
    console.log(`${id}: ${(p.durationMs / 1000).toFixed(2)} s with pauses, ${s.spoken.length} characters`);
  }
  console.log(`characters sent this run: ${total}`);
}

main().catch((e: unknown) => {
  console.error(e instanceof Error ? e.message : e);
  process.exit(1);
});
