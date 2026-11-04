// Real recordings of the live site (https://caliper-sigma.vercel.app), one per scene, for the
// demo video. Recorded runs only: the backend's /api/* is blocked, so the site serves its recorded
// runs from its own static files and no live run (no spend) can start.
//
//   node --no-warnings scripts/record.mts [s3 s4 s4r s5 s7 s8]
//
// Capture: Chrome's screencast (CDP Page.startScreencast, JPEG quality 92) of a 2560 x 1440
// viewport at deviceScaleFactor 1. The page gets `html { zoom: 2 }`, so the site lays out like a
// 1280 x 720 laptop screen but renders text and vectors at twice the size: crisp frames with room
// for camera pushes (a screencast at deviceScaleFactor 2 only returns 1280 x 720 frames). Frames
// are written as they arrive, then resampled to a constant 30 fps and encoded with x264.
// Each recording also writes <name>.json: named marks (element boxes in frame pixels at a time
// in the recording) that the scenes use to aim the camera.
import { execFileSync, spawn } from "node:child_process";
import { mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { chromium, type BrowserContext, type Locator, type Page } from "playwright";

const BASE = "https://caliper-sigma.vercel.app";
const VIDEO = resolve(import.meta.dirname, "..");
const OUT = resolve(VIDEO, "public", "rec");
const TMP = resolve(VIDEO, "out", "rec_frames");
const W = 2560;
const H = 1440;
const FPS = 30;

type Box = { x: number; y: number; w: number; h: number };
type Mark = { name: string; t: number; box: Box | null };

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

/** A drawn arrow cursor (screencasts do not show the system one) and an eased page scroll. */
const PAGE_HELPERS = () => {
  const zoom = () => {
    const s = document.createElement("style");
    s.textContent = "html { zoom: 2 !important; }";
    document.head.appendChild(s);
  };
  const cursor = () => {
    const c = document.createElement("div");
    c.id = "__cursor";
    c.innerHTML =
      '<svg width="34" height="40" viewBox="0 0 17 20"><path d="M1 1 L1 15.5 L4.8 12 L7.4 18.2 L10 17.1 L7.5 11 L12.6 11 Z" fill="#F2F4F6" stroke="#0A0C0F" stroke-width="1.3" stroke-linejoin="round"/></svg>';
    Object.assign(c.style, {
      position: "fixed", left: "2300px", top: "1250px", zoom: "0.5", zIndex: "2147483647",
      pointerEvents: "none", transition: "transform 160ms ease", filter: "drop-shadow(0 2px 6px rgba(0,0,0,.5))",
    });
    document.body.appendChild(c);
  };
  const w = window as unknown as Record<string, unknown>;
  w.__glide = (x: number, y: number, ms: number) =>
    new Promise<void>((done) => {
      const c = document.getElementById("__cursor");
      if (!c) return done();
      const x0 = parseFloat(c.style.left);
      const y0 = parseFloat(c.style.top);
      const t0 = performance.now();
      const step = (t: number) => {
        const p = Math.min(1, (t - t0) / ms);
        const e = p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2;
        c.style.left = `${x0 + (x - x0) * e}px`;
        c.style.top = `${y0 + (y - y0) * e}px`;
        if (p < 1) requestAnimationFrame(step);
        else done();
      };
      requestAnimationFrame(step);
    });
  w.__press = () => {
    const c = document.getElementById("__cursor");
    if (!c) return;
    c.style.transform = "scale(0.82)";
    setTimeout(() => (c.style.transform = "scale(1)"), 170);
  };
  w.__scroll = (y: number, ms: number) =>
    new Promise<void>((done) => {
      const y0 = window.scrollY;
      const t0 = performance.now();
      const step = (t: number) => {
        const p = Math.min(1, (t - t0) / ms);
        const e = p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2;
        window.scrollTo(0, y0 + (y - y0) * e);
        if (p < 1) requestAnimationFrame(step);
        else done();
      };
      requestAnimationFrame(step);
    });
  const ready = () => {
    zoom();
    cursor();
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", ready);
  else ready();
};

class Recording {
  readonly marks: Mark[] = [];
  readonly name: string;
  readonly page: Page;
  private ctx: BrowserContext;
  private frames: { ts: number; file: string }[] = [];
  private t0 = 0;
  private stopped = false;
  private constructor(name: string, page: Page, ctx: BrowserContext) {
    this.name = name;
    this.page = page;
    this.ctx = ctx;
  }

  static async open(ctx: BrowserContext, name: string, path: string, ready: (p: Page) => Promise<void>) {
    const page = await ctx.newPage();
    await page.route("**/api/**", (r) => r.abort());
    await page.goto(BASE + path, { waitUntil: "networkidle" });
    await ready(page);
    return new Recording(name, page, ctx);
  }

  async start(): Promise<void> {
    rmSync(resolve(TMP, this.name), { recursive: true, force: true });
    mkdirSync(resolve(TMP, this.name), { recursive: true });
    const cdp = await this.ctx.newCDPSession(this.page);
    let i = 0;
    cdp.on("Page.screencastFrame", (f) => {
      if (this.stopped) return;
      const file = resolve(TMP, this.name, `${String(i++).padStart(6, "0")}.jpg`);
      writeFileSync(file, Buffer.from(f.data, "base64"));
      this.frames.push({ ts: f.metadata.timestamp ?? Date.now() / 1000, file });
      void cdp.send("Page.screencastFrameAck", { sessionId: f.sessionId }).catch(() => {});
    });
    await cdp.send("Page.startScreencast", { format: "jpeg", quality: 92, maxWidth: W, maxHeight: H, everyNthFrame: 1 });
    this.stop = async () => {
      this.stopped = true;
      await cdp.send("Page.stopScreencast").catch(() => {});
    };
    // Force a first frame even on a still page, then let it settle.
    await this.page.evaluate(() => window.scrollBy(0, 0));
    await sleep(400);
    this.t0 = this.frames[0]?.ts ?? Date.now() / 1000;
  }

  stop: () => Promise<void> = async () => {};

  private now(): number {
    return Date.now() / 1000 - this.t0;
  }

  async mark(name: string, target: Locator | null): Promise<void> {
    const b = target ? await target.boundingBox() : null;
    this.marks.push({ name, t: Math.max(0, this.now()), box: b && { x: b.x, y: b.y, w: b.width, h: b.height } });
  }

  async hold(ms: number): Promise<void> {
    await sleep(ms);
  }

  async glide(x: number, y: number, ms = 900): Promise<void> {
    await this.page.evaluate(([gx, gy, gm]) => (window as unknown as { __glide: (a: number, b: number, c: number) => Promise<void> }).__glide(gx, gy, gm), [x, y, ms] as const);
    await this.page.mouse.move(x, y);
  }

  async click(target: Locator, ms = 900): Promise<void> {
    await target.scrollIntoViewIfNeeded();
    const b = await target.boundingBox();
    if (!b) throw new Error(`${this.name}: nothing to click`);
    await this.glide(b.x + b.width / 2, b.y + b.height / 2, ms);
    await sleep(160);
    await this.page.evaluate(() => (window as unknown as { __press: () => void }).__press());
    await this.page.mouse.down();
    await sleep(70);
    await this.page.mouse.up();
  }

  /** Eased scroll so the target's top lands `top` frame pixels below the top of the viewport. */
  async scrollTo(target: Locator, top: number, ms = 1600): Promise<void> {
    const b = await target.boundingBox();
    if (!b) throw new Error(`${this.name}: nothing to scroll to`);
    const y = await this.page.evaluate(() => window.scrollY);
    const goal = Math.max(0, y + (b.y - top));
    await this.page.evaluate(([gy, gm]) => (window as unknown as { __scroll: (a: number, b: number) => Promise<void> }).__scroll(gy, gm), [goal, ms] as const);
    // Settle: a lazy chart or image above can shift the layout while scrolling.
    const after = await target.boundingBox();
    if (after && Math.abs(after.y - top) > 6) {
      const y2 = await this.page.evaluate(() => window.scrollY);
      await this.page.evaluate(([gy, gm]) => (window as unknown as { __scroll: (a: number, b: number) => Promise<void> }).__scroll(gy, gm), [Math.max(0, y2 + after.y - top), 400] as const);
    }
  }

  /** Resample the variable-rate screencast to constant 30 fps and encode it. */
  async save(): Promise<void> {
    // The screencast only sends a frame when the screen changes: a still hold ends with no new
    // frames, so the recording runs to now and repeats the last frame through it.
    const end = Math.max(this.frames[this.frames.length - 1].ts, Date.now() / 1000);
    await this.stop();
    const n = Math.floor((end - this.t0) * FPS) + 1;
    mkdirSync(OUT, { recursive: true });
    const dest = resolve(OUT, `${this.name}.mp4`);
    const ff = spawn("ffmpeg", [
      "-v", "error", "-y", "-f", "image2pipe", "-c:v", "mjpeg", "-framerate", String(FPS), "-i", "-",
      "-vf", `scale=${W}:${H}:flags=lanczos`, "-c:v", "libx264", "-preset", "slow", "-crf", "16",
      "-pix_fmt", "yuv420p", "-g", String(FPS), "-movflags", "+faststart", dest,
    ], { stdio: ["pipe", "inherit", "inherit"] }); // fmt: skip
    let j = 0;
    let last = "";
    let bytes: Buffer = Buffer.alloc(0);
    for (let k = 0; k < n; k++) {
      const t = this.t0 + k / FPS;
      while (j + 1 < this.frames.length && this.frames[j + 1].ts <= t) j++;
      if (this.frames[j].file !== last) {
        last = this.frames[j].file;
        bytes = readFileSync(last);
      }
      if (!ff.stdin.write(bytes)) await new Promise((r) => ff.stdin.once("drain", r));
    }
    ff.stdin.end();
    await new Promise<void>((ok, fail) => ff.on("close", (c) => (c === 0 ? ok() : fail(new Error(`ffmpeg ${c}`)))));
    const meta = { url: BASE, fps: FPS, width: W, height: H, frames: n, duration_s: n / FPS, captured_frames: this.frames.length, marks: this.marks };
    writeFileSync(resolve(OUT, `${this.name}.json`), JSON.stringify(meta, null, 1), "utf8");
    rmSync(resolve(TMP, this.name), { recursive: true, force: true });
    const probe = execFileSync("ffprobe", ["-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", dest]).toString().trim();
    console.log(`${this.name}: ${n} frames (${(n / FPS).toFixed(1)} s, ${this.frames.length} captured), ${probe} s on disk, ${this.marks.length} marks`);
    await this.page.close();
  }
}

const card = (p: Page, text: string) => p.locator('[data-slot="card"]', { hasText: text }).first();
const finding = (p: Page, title: string) => p.locator("li", { has: p.getByRole("heading", { name: title }) }).first();
const section = (p: Page, title: string) => p.locator("h3", { hasText: new RegExp(`^${title}$`) }).first().locator("xpath=..");

const SCENES: Record<string, (ctx: BrowserContext) => Promise<void>> = {
  // Scene 3: the A08 refusal as the site shows it: reason and fix.
  async s3(ctx) {
    const r = await Recording.open(ctx, "s3_refusal", "/workspace?run=field-a08", async (p) => {
      await p.getByText("I won't guess.").waitFor({ timeout: 60000 });
      await sleep(1500);
    });
    await r.start();
    await r.mark("stage", r.page.locator("video").first());
    await r.hold(1500);
    await r.scrollTo(card(r.page, "I won't guess."), 260, 1800);
    await r.hold(300);
    await r.mark("card", card(r.page, "I won't guess."));
    await r.glide(1900, 1150, 1200);
    await r.hold(5000);
    await r.save();
  },

  // Scene 4: the chain behind C07's number: spec, scale, fit, checks, audit.
  async s4(ctx) {
    const r = await Recording.open(ctx, "s4_chain", "/workspace?run=field-c07", async (p) => {
      await p.getByRole("button", { name: "Show the chain" }).waitFor({ timeout: 60000 });
      await sleep(1500);
    });
    await r.start();
    await r.mark("question", r.page.locator("textarea").first());
    await r.hold(1200);
    await r.mark("stage", r.page.locator("video").first());
    await r.click(r.page.getByRole("button", { name: "Play" }).first(), 1100);
    await r.hold(2500);
    await r.scrollTo(card(r.page, "90% range"), 160, 1600);
    await r.mark("result", card(r.page, "90% range"));
    await r.hold(1200);
    await r.click(r.page.getByRole("button", { name: "Show the chain" }), 900);
    await r.hold(900);
    for (const title of ["Spec", "Scale", "Fit", "Checks", "Audit"]) {
      await r.scrollTo(section(r.page, title), 140, 1500);
      await r.hold(250);
      await r.mark(title.toLowerCase(), section(r.page, title));
      await r.hold(2600);
    }
    await r.save();
  },

  // Scene 4, last line: the audit's record on the evidence page.
  async s4r(ctx) {
    const r = await Recording.open(ctx, "s4_audit", "/results", async (p) => {
      await p.getByText("both its vetoes were false alarms").first().waitFor({ timeout: 60000 });
      await sleep(1200);
    });
    await r.start();
    const audit = finding(r.page, "The audit is a cautious check: both its vetoes were false alarms");
    await r.scrollTo(r.page.getByText("What the numbers say"), 160, 1400);
    await r.hold(400);
    await r.mark("audit_card", audit);
    await r.glide(1500, 1180, 1000);
    await r.hold(4500);
    await r.save();
  },

  // Scene 5: the street study page on A14, then the six recorded passes.
  async s5(ctx) {
    const r = await Recording.open(ctx, "s5_study", "/study?run=study-a14", async (p) => {
      await p.getByRole("navigation", { name: "Recorded studies" }).waitFor({ timeout: 60000 });
      await sleep(1500);
    });
    await r.start();
    await r.mark("stage", r.page.locator("video").first());
    await r.page.evaluate(() => {
      const v = document.querySelector("video");
      if (v) {
        v.loop = true;
        void v.play();
      }
    });
    await r.hold(5200);
    await r.mark("summary", r.page.getByLabel("Study summary"));
    await r.hold(2500);
    for (const clip of ["A11", "A12", "A13", "A14", "A15", "A16"]) {
      await r.click(r.page.getByRole("button", { name: new RegExp(`\\(${clip}\\)`) }).last(), 700);
      await r.hold(700);
      await r.mark(`pass_${clip}`, r.page.getByLabel("Study summary"));
      await r.hold(900);
    }
    await r.hold(1500);
    await r.save();
  },

  // Scene 7: the evidence page: findings, MRA by variant, like for like.
  async s7(ctx) {
    const r = await Recording.open(ctx, "s7_results", "/results", async (p) => {
      await p.getByText("Claim H1 failed on holdout").first().waitFor({ timeout: 60000 });
      await sleep(1200);
    });
    await r.start();
    await r.hold(800);
    await r.scrollTo(r.page.getByText("What the numbers say"), 160, 1400);
    await r.hold(300);
    await r.mark("findings", r.page.getByText("What the numbers say").locator("xpath=.."));
    await r.mark("h1_card", finding(r.page, "Claim H1 failed on holdout"));
    await r.mark("closer_card", finding(r.page, "When it answers, it is closer"));
    await r.hold(3500);
    await r.scrollTo(r.page.getByRole("heading", { name: "MRA by variant" }), 140, 1600);
    await r.hold(2200);
    await r.mark("mra_chart", r.page.locator("figure", { hasText: "Official and answered-only MRA" }).first());
    await r.hold(2500);
    await r.scrollTo(r.page.getByRole("heading", { name: "Like for like" }), 140, 1600);
    await r.hold(400);
    await r.mark("like_for_like", r.page.locator("figure", { hasText: "Answered-only MRA: Caliper and Muse Spark alone" }).first());
    await r.hold(4000);
    await r.save();
  },

  // Scene 8: the landing page hero as it loads.
  async s8(ctx) {
    const r = await Recording.open(ctx, "s8_landing", "/", async (p) => {
      await p.getByRole("heading", { level: 1 }).waitFor({ timeout: 60000 });
    });
    await r.start();
    await r.mark("hero", r.page.getByRole("heading", { level: 1 }));
    await r.hold(9000);
    await r.save();
  },
};

async function main(): Promise<void> {
  const wanted = process.argv.slice(2);
  const names = wanted.length ? wanted : Object.keys(SCENES);
  const browser = await chromium.launch();
  try {
    for (const name of names) {
      const ctx = await browser.newContext({
        viewport: { width: W, height: H },
        deviceScaleFactor: 1,
        colorScheme: "dark",
        reducedMotion: "no-preference",
      });
      await ctx.addInitScript(PAGE_HELPERS);
      await SCENES[name](ctx);
      await ctx.close();
    }
  } finally {
    await browser.close();
  }
}

main().catch((e: unknown) => {
  console.error(e instanceof Error ? e.stack : e);
  process.exit(1);
});
