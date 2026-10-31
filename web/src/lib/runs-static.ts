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

/** The recorded measure runs the landing uses: real field runs first, placeholders otherwise. */
export async function landingRuns() {
  const index = (await loadRunIndex()).filter((r) => r.kind === "measure");
  const runs = (await Promise.all(index.map((r) => loadRun(r.run_id)))).filter(
    (r): r is CachedRun => r != null,
  );
  const measured = runs.find((r) => r.result.status === "measured") ?? null;
  const vetoed = runs.find((r) => r.result.status === "abstained" && r.result.audit && !r.result.audit.approve) ?? null;
  const abstained = runs.filter((r) => r.result.status === "abstained");
  return { measured, vetoed, abstained };
}
