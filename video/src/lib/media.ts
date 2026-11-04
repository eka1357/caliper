// Narration timings (scripts/narration.mts), footage maps (scripts/export_footage.py) and site
// recordings (scripts/record.mts), read from public/ at metadata time so the bundle compiles
// without them.
import { staticFile } from "remotion";

export type Word = { text: string; startMs: number; endMs: number };

export type Narration = {
  id: string;
  file: string;
  text: string;
  durationMs: number;
  words: Word[];
  cues: Record<string, number>;
  keys: { name: string; startMs: number; endMs: number }[];
};

export type Outline = { frame: number; path: string; touches: string[] };

export type Footage = {
  clip: string;
  file: string;
  fps: number;
  width: number;
  height: number;
  source_frames: number;
  overlay_width: number;
  overlay_height: number;
  order: "pingpong" | "forward";
  frames: number;
  outlines?: Outline[];
};

export type Box = { x: number; y: number; w: number; h: number };

export type Recording = {
  name: string;
  file: string;
  fps: number;
  width: number;
  height: number;
  frames: number;
  marks: { name: string; t: number; box: Box | null }[];
};

async function json<T>(
  file: string,
  hint: string,
  signal?: AbortSignal,
): Promise<T> {
  const res = await fetch(staticFile(file), { signal });
  if (!res.ok) throw new Error(`public/${file} is missing: ${hint}`);
  return (await res.json()) as T;
}

export const loadNarration = (id: string, signal?: AbortSignal) =>
  json<Narration>(
    `audio/${id}.json`,
    `node --no-warnings scripts/narration.mts generate ${id}`,
    signal,
  );

export const loadFootage = (clip: string, signal?: AbortSignal) =>
  json<Footage>(
    `footage/${clip}.json`,
    `backend/.venv/Scripts/python.exe video/scripts/export_footage.py ${clip.toUpperCase()}`,
    signal,
  );

export async function loadRecording(
  name: string,
  signal?: AbortSignal,
): Promise<Recording> {
  const r = await json<Omit<Recording, "name" | "file">>(
    `rec/${name}.json`,
    "node --no-warnings scripts/record.mts",
    signal,
  );
  return { ...r, name, file: `rec/${name}.mp4` };
}

export function cueMs(n: Narration, name: string): number {
  const v = n.cues[name];
  if (v === undefined)
    throw new Error(`${n.id}: no cue [@${name}] in narration.md`);
  return v;
}

const bare = (s: string) =>
  s.replace(/[^\p{L}\p{N}%.]/gu, "").replace(/\.$/, "");

/** When the voice starts saying `text` (the first such word at or after `afterMs`). */
export function wordMs(n: Narration, text: string, afterMs = 0): number {
  const w = n.words.find(
    (x) => x.startMs >= afterMs && bare(x.text) === bare(text),
  );
  if (!w)
    throw new Error(`${n.id}: "${text}" is not spoken after ${afterMs} ms`);
  return w.startMs;
}

export const frames = (ms: number, fps: number) =>
  Math.round((ms / 1000) * fps);

/** The source frame on screen at output frame f of a footage file (see export_footage.py). */
export function sourceFrame(f: Footage, outFrame: number): number {
  const k = ((outFrame % f.frames) + f.frames) % f.frames;
  if (f.order === "pingpong")
    return k < f.source_frames ? k : 2 * f.source_frames - 2 - k;
  return Math.min(k, f.source_frames - 1);
}

/** A named mark of a recording: when it was taken and the element's box in frame pixels. */
export function mark(r: Recording, name: string): { t: number; box: Box } {
  const m = r.marks.find((x) => x.name === name);
  if (!m || !m.box) throw new Error(`${r.name}: no mark "${name}"`);
  return { t: m.t, box: m.box };
}
