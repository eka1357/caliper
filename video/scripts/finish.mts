// Final audio of a rendered cut: music ducked under the voice (only if public/audio/music.mp3
// exists, copied there by scripts/prep.mts from assets/music.mp3), then loudness normalized to
// -16 LUFS with two-pass loudnorm. The video stream is copied untouched.
//
//   node --no-warnings scripts/finish.mts out/demo_raw.mp4 out/caliper_demo.mp4
import { spawnSync } from "node:child_process";
import { existsSync, statSync } from "node:fs";

const [src, dst] = process.argv.slice(2);
if (!src || !dst) throw new Error("usage: finish.mts <rendered.mp4> <final.mp4>");
const MUSIC = "public/audio/music.mp3";
const music = existsSync(MUSIC);
const inputs = music ? ["-i", src, "-stream_loop", "-1", "-i", MUSIC] : ["-i", src];
// About -20 dB under the voice, pressed down further while the voice speaks (sidechain).
const pre = music
  ? "[1:a]volume=-20dB[m];[m][0:a]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=400[d];" +
    "[0:a][d]amix=inputs=2:duration=first:normalize=0[mix];[mix]"
  : "[0:a]";
const TARGET = "I=-16:TP=-1.5:LRA=11";

function ff(args: string[]): string {
  const r = spawnSync("ffmpeg", ["-hide_banner", "-nostats", ...args], { encoding: "utf8", maxBuffer: 64 << 20 });
  if (r.status !== 0) throw new Error(r.stderr.slice(-2000));
  return r.stderr;
}

const pass1 = ff([...inputs, "-filter_complex", `${pre}loudnorm=${TARGET}:print_format=json[out]`, "-map", "[out]", "-f", "null", "-"]);
const m = JSON.parse(pass1.slice(pass1.lastIndexOf("{"), pass1.lastIndexOf("}") + 1)) as Record<string, string>;
ff([
  "-y", ...inputs,
  "-filter_complex",
  `${pre}loudnorm=${TARGET}:measured_I=${m.input_i}:measured_TP=${m.input_tp}:measured_LRA=${m.input_lra}:measured_thresh=${m.input_thresh}:offset=${m.target_offset}:linear=true[out]`,
  "-map", "0:v", "-map", "[out]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
  "-movflags", "+faststart", dst,
]); // fmt: skip
const check = ff(["-i", dst, "-af", "ebur128=framelog=quiet", "-f", "null", "-"]);
const lufs = /I:\s+(-?[\d.]+) LUFS/.exec(check.slice(check.lastIndexOf("Summary")))?.[1];
const probe = spawnSync("ffprobe", [
  "-v", "error", "-show_entries", "stream=codec_type,codec_name,width,height,r_frame_rate,sample_rate,channels:format=duration,bit_rate",
  "-of", "compact=p=0", dst,
], { encoding: "utf8" }).stdout.trim(); // fmt: skip
console.log(`music: ${music ? "yes" : "none"}; loudness before ${m.input_i} LUFS, after ${lufs} LUFS`);
console.log(probe);
console.log(`size ${(statSync(dst).size / 1e6).toFixed(1)} MB`);
