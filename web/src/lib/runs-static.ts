// Build-time reader for the recorded runs in web/public/runs (server only: node:fs). The landing
// page shows run values from these JSON files, never typed numbers (AGENTS.md rule 4).
import { readFile } from "node:fs/promises";
import path from "node:path";
import { buildTimeOnly } from "./results";
import type { CachedRun, RunIndexEntry } from "./types";

const RUNS = path.join(process.cwd(), "public", "runs");

export async function loadRunIndex(): Promise<RunIndexEntry[]> {
  "use cache";
  buildTimeOnly();
  try {
    return JSON.parse(await readFile(path.join(RUNS, "index.json"), "utf8")) as RunIndexEntry[];
  } catch {
    return [];
  }
}

export async function loadRun(runId: string): Promise<CachedRun | null> {
  "use cache";
  buildTimeOnly();
  try {
    return JSON.parse(await readFile(path.join(RUNS, runId, "run.json"), "utf8")) as CachedRun;
  } catch {
    return null;
  }
}

/** The recorded measure runs the landing uses (real field runs; placeholders only if none). */
export async function landingRuns() {
  const index = (await loadRunIndex()).filter((r) => r.kind === "measure");
  const runs = (await Promise.all(index.map((r) => loadRun(r.run_id)))).filter(
    (r): r is CachedRun => r != null,
  );
  const inside = (r: CachedRun) => {
    const iv = r.result.interval_90;
    const t = r.meta.instrument?.value;
    return iv != null && t != null && iv[0] <= t && t <= iv[1];
  };
  const done = runs.filter((r) => r.result.status === "measured");
  // Hero: a measured run whose instrument reading lies inside its 90% range; the miss is shown too.
  const measured = done.find(inside) ?? done[0] ?? null;
  const missed = done.find((r) => r !== measured && r.meta.instrument?.value != null && !inside(r)) ?? null;
  const vetoed = runs.find((r) => r.result.status === "abstained" && r.result.audit && !r.result.audit.approve) ?? null;
  const abstained = runs.filter((r) => r.result.status === "abstained");
  // Speed: the measured speed run whose GPS reading lies inside its range, smallest error first.
  const err = (r: CachedRun) => Math.abs((r.result.value ?? 0) - (r.meta.instrument?.value ?? 0)) / (r.meta.instrument?.value || 1);
  const speedRun = done.filter((r) => r.result.quantity === "speed" && inside(r)).sort((a, b) => err(a) - err(b))[0] ?? null;
  return { measured, missed, vetoed, abstained, speedRun };
}
