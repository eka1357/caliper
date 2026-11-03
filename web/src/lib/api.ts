import { runAssetUrl } from "./run-assets";
// The only place the web app talks to the backend (AGENTS.md section 8).
// Cached runs also load straight from /runs/ (web/public) when the backend is unreachable,
// so the recorded runs work with no backend at all (ARCHITECTURE section 12).

import type {
  ApiErrorBody,
  CachedRun,
  CachedStudyRun,
  GateLine,
  Guess,
  Health,
  RunIndexEntry,
} from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly body: ApiErrorBody,
  ) {
    super(body.message);
  }

  /** A live-run cap or live runs switched off: the UI offers the cached runs. */
  get isCap(): boolean {
    return this.status === 429 || this.status === 503;
  }
}

async function parse<T>(res: Response): Promise<T> {
  if (res.ok) return (await res.json()) as T;
  let body: ApiErrorBody = { code: "error", message: "Something broke on our side." };
  try {
    body = (await res.json()) as ApiErrorBody;
  } catch {
    // keep the generic body: never show a fake number
  }
  throw new ApiError(res.status, body);
}

async function getJson<T>(url: string): Promise<T> {
  return parse<T>(await fetch(url, { cache: "no-store" }));
}

export async function health(): Promise<Health | null> {
  try {
    return await getJson<Health>(`${API_URL}/api/health`);
  } catch {
    return null; // no backend: cached runs only
  }
}

export async function listRuns(): Promise<RunIndexEntry[]> {
  try {
    return await getJson<RunIndexEntry[]>(`${API_URL}/api/runs`);
  } catch {
    return getJson<RunIndexEntry[]>("/runs/index.json");
  }
}

export async function getRun(runId: string): Promise<CachedRun> {
  return fetchRun<CachedRun>(runId);
}

export async function getStudyRun(runId: string): Promise<CachedStudyRun> {
  return fetchRun<CachedStudyRun>(runId);
}

async function fetchRun<T>(runId: string): Promise<T> {
  try {
    return await getJson<T>(`${API_URL}/api/runs/${encodeURIComponent(runId)}`);
  } catch {
    return getJson<T>(runAssetUrl(runId, "run.json") as string);
  }
}

/** URL of a cached run's clip or poster, served by the web app from public/runs. */
export const runAsset = runAssetUrl;

export interface MeasureInput {
  video: Blob;
  question: string;
  prior?: string;
}

function form({ video, question, prior }: MeasureInput): FormData {
  const body = new FormData();
  body.append("video", video, video instanceof File ? video.name : "clip.mp4");
  body.append("question", question);
  if (prior) body.append("prior", prior);
  return body;
}

/** Upload with progress (fetch has no upload progress), then the live measurement. */
export function measure(
  input: MeasureInput,
  onUpload: (percent: number) => void,
  signal?: AbortSignal,
): Promise<CachedRun> {
  return upload<CachedRun>("/api/measure", form(input), onUpload, signal);
}

export interface StudyInput {
  video: Blob;
  gateA: GateLine;
  gateB: GateLine;
  gateDistanceM: number;
  speedLimitKmh?: number;
  /** The size of the frame the gates were drawn on (the clip's own pixels); the API scales them. */
  frameWidth?: number;
  frameHeight?: number;
}

/** Live street study (POST /api/study), behind the same live-run caps as a measure. */
export function study(
  input: StudyInput,
  onUpload: (percent: number) => void,
  signal?: AbortSignal,
): Promise<CachedStudyRun> {
  const body = new FormData();
  body.append("video", input.video, input.video instanceof File ? input.video.name : "street.mp4");
  body.append("gate_a", JSON.stringify(input.gateA));
  body.append("gate_b", JSON.stringify(input.gateB));
  body.append("gate_distance_m", String(input.gateDistanceM));
  if (input.speedLimitKmh != null) body.append("speed_limit_kmh", String(input.speedLimitKmh));
  if (input.frameWidth && input.frameHeight) {
    body.append("frame_width", String(input.frameWidth));
    body.append("frame_height", String(input.frameHeight));
  }
  return upload<CachedStudyRun>("/api/study", body, onUpload, signal);
}

interface JobStatus<T> {
  status: "running" | "done" | "error";
  result?: T;
  error?: ApiErrorBody & { status: number };
}

/** Poll GET /api/jobs/{id} every 3 s until the live run is done (or fails, or is cancelled). */
async function pollJob<T>(jobId: string, signal?: AbortSignal): Promise<T> {
  let misses = 0;
  for (;;) {
    await new Promise((r) => setTimeout(r, 3000));
    if (signal?.aborted) throw new ApiError(0, { code: "aborted", message: "Cancelled." });
    let job: JobStatus<T>;
    try {
      job = await getJson<JobStatus<T>>(`${API_URL}/api/jobs/${encodeURIComponent(jobId)}`);
      misses = 0;
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) throw e;
      if (++misses > 10) throw new ApiError(0, { code: "network", message: "Something broke on our side." });
      continue; // a dropped poll is retried
    }
    if (job.status === "done" && job.result) return job.result;
    if (job.status === "error") {
      const err = job.error ?? { code: "error", message: "Something broke on our side.", status: 500 };
      throw new ApiError(err.status, { code: err.code, message: err.message });
    }
  }
}

function upload<T>(
  path: string,
  body: FormData,
  onUpload: (percent: number) => void,
  signal?: AbortSignal,
): Promise<T> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_URL}${path}`);
    xhr.responseType = "json";
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) onUpload(Math.round((100 * e.loaded) / e.total));
    };
    xhr.onload = () => {
      const body = xhr.response as unknown;
      // 202: the run outlasts the host's request window; it continues as a job, poll for it.
      const job = xhr.status === 202 ? (body as { job_id?: string } | null)?.job_id : undefined;
      if (job) pollJob<T>(job, signal).then(resolve, reject);
      else if (xhr.status >= 200 && xhr.status < 300) resolve(body as T);
      else
        reject(
          new ApiError(
            xhr.status,
            (body as ApiErrorBody | null) ?? {
              code: "error",
              message: "Something broke on our side.",
            },
          ),
        );
    };
    xhr.onerror = () =>
      reject(new ApiError(0, { code: "network", message: "Something broke on our side." }));
    signal?.addEventListener("abort", () => xhr.abort());
    xhr.send(body);
  });
}

export async function guess(input: MeasureInput, signal?: AbortSignal): Promise<Guess> {
  return parse<Guess>(
    await fetch(`${API_URL}/api/guess`, { method: "POST", body: form(input), signal }),
  );
}
