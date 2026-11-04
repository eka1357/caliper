// Copies what the scenes need from elsewhere in the repo into public/ ($0, no network): the audit
// keyframes of the C07 run (web/public/runs, blurred as published) and, only if it exists,
// video/assets/music.mp3 (the demo has music only when that file is there).
import { copyFileSync, existsSync, mkdirSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

const VIDEO = resolve(import.meta.dirname, "..");
const RUNS = resolve(VIDEO, "..", "web", "public", "runs");
const RUN = "field-c07";

const meta = JSON.parse(readFileSync(resolve(RUNS, RUN, "run.json"), "utf8")).meta as {
  keyframes: string[];
};
mkdirSync(resolve(VIDEO, "public", "keyframes", RUN), { recursive: true });
for (const k of meta.keyframes) {
  copyFileSync(resolve(RUNS, RUN, k), resolve(VIDEO, "public", "keyframes", RUN, k));
}
console.log(`copied ${meta.keyframes.length} keyframes of ${RUN}`);

const music = resolve(VIDEO, "assets", "music.mp3");
if (existsSync(music)) {
  copyFileSync(music, resolve(VIDEO, "public", "audio", "music.mp3"));
  console.log("music: copied assets/music.mp3");
} else {
  console.log("music: none (no assets/music.mp3)");
}
