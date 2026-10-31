"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useId, useRef, useState } from "react";
import { Placeholder, PlaceholderTag } from "@/components/site/Placeholder";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import * as api from "@/lib/api";
import type { CachedStudyRun, Health, RunIndexEntry } from "@/lib/types";
import { useObjectUrl } from "@/lib/useObjectUrl";
import { COPY } from "../workspace/copy";
import { STUDY_COPY } from "./copy";
import { defaultGates, type Gates, GateStage } from "./GateStage";
import { SpeedHistogram } from "./SpeedHistogram";
import { StudySummaryCard } from "./StudySummaryCard";

type Phase =
  | { kind: "idle" }
  | { kind: "uploading"; n: number }
  | { kind: "working" }
  | { kind: "cap"; message: string }
  | { kind: "error" };

export function StudyView() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const ids = { file: useId(), cam: useId(), dist: useId(), limit: useId() };
  const [studies, setStudies] = useState<RunIndexEntry[]>([]);
  const [health, setHealth] = useState<Health | null>(null);
  const [runId, setRunId] = useState<string | null>(params.get("run"));
  const [run, setRun] = useState<CachedStudyRun | null>(null);
  const [clip, setClip] = useState<File | null>(null);
  const [gates, setGates] = useState<Gates>(defaultGates(1280, 720));
  const [distance, setDistance] = useState("");
  const [limit, setLimit] = useState("");
  const [phase, setPhase] = useState<Phase>({ kind: "idle" });
  const abort = useRef<AbortController | null>(null);
  const localUrl = useObjectUrl(clip);

  useEffect(() => {
    void api.listRuns().then((list) => setStudies(list.filter((r) => r.kind === "study")));
    void api.health().then(setHealth);
  }, []);

  useEffect(() => {
    if (!runId) return;
    let live = true;
    api.getStudyRun(runId).then(
      (r) => live && setRun(r),
      () => live && setPhase({ kind: "error" }),
    );
    return () => {
      live = false;
    };
  }, [runId]);

  const pick = (id: string) => {
    abort.current?.abort();
    setClip(null);
    setRunId(id);
    router.replace(`${pathname}?run=${encodeURIComponent(id)}`, { scroll: false });
  };

  const onClip = (f: File | undefined) => {
    if (!f) return;
    setClip(f);
    setRun(null);
    setRunId(null);
    setPhase({ kind: "idle" });
  };

  const d = Number(distance);
  const lim = limit === "" ? undefined : Number(limit);
  const busy = phase.kind === "uploading" || phase.kind === "working";
  const canRun = !!clip && Number.isFinite(d) && d > 0 && (lim == null || lim > 0) && !busy;

  const onRun = async () => {
    if (!clip || !canRun) return;
    abort.current?.abort();
    const ctrl = new AbortController();
    abort.current = ctrl;
    setPhase({ kind: "uploading", n: 0 });
    try {
      const result = await api.study(
        { video: clip, gateA: gates[0], gateB: gates[1], gateDistanceM: d, speedLimitKmh: lim },
        (n) => setPhase(n >= 100 ? { kind: "working" } : { kind: "uploading", n }),
        ctrl.signal,
      );
      setRun(result);
      setRunId(result.result.run_id);
      setPhase({ kind: "idle" });
    } catch (e) {
      if (ctrl.signal.aborted) return;
      if (e instanceof api.ApiError && e.isCap) setPhase({ kind: "cap", message: e.body.message });
      else setPhase({ kind: "error" });
    }
  };

  const recorded = run && run.meta.source !== "live";
  const src = recorded ? api.runAsset(run.result.run_id, run.meta.clip) : localUrl;
  const poster = recorded ? api.runAsset(run.result.run_id, run.meta.poster) : null;
  const summary = run?.result ?? null;

  return (
    <div className="mx-auto grid w-full max-w-[1440px] grid-cols-1 gap-6 px-4 py-6 lg:grid-cols-12 lg:px-8">
      <div className="flex min-w-0 flex-col gap-4 lg:col-span-7">
        <GateStage
          key={src ?? "empty"}
          src={src}
          poster={poster}
          gates={gates}
          onGates={run ? undefined : setGates}
          onSize={(w, h) => !run && setGates(defaultGates(w, h))}
          overlay={run?.overlay ?? null}
          readings={summary?.readings ?? []}
        />
        <p className="min-h-5 text-sm text-muted-foreground">
          {clip && !run ? STUDY_COPY.gates : run?.meta.placeholder ? "Placeholder run." : ""}
        </p>
        <SpeedHistogram summary={summary} />
      </div>

      <div className="flex min-w-0 flex-col gap-5 lg:col-span-5">
        <header className="flex flex-col gap-1">
          <h1 className="text-2xl font-medium">{STUDY_COPY.title}</h1>
          <p className="text-sm text-muted-foreground">{STUDY_COPY.privacy}</p>
        </header>

        <section aria-labelledby="step1" className="flex flex-col gap-2">
          <h2 id="step1" className="text-sm font-medium">1. A street clip</h2>
          <p className="text-sm text-muted-foreground">{STUDY_COPY.guide}</p>
          <div className="flex flex-wrap items-center gap-2">
            <Button asChild variant="outline">
              <label htmlFor={ids.file}>Choose a clip</label>
            </Button>
            <input id={ids.file} type="file" accept="video/mp4,video/quicktime,video/*"
              className="sr-only" onChange={(e) => onClip(e.target.files?.[0])} />
            <Button asChild variant="outline" className="lg:hidden">
              <label htmlFor={ids.cam}>Record a clip</label>
            </Button>
            <input id={ids.cam} type="file" accept="video/*" capture="environment"
              className="sr-only" onChange={(e) => onClip(e.target.files?.[0])} />
            {clip && <span className="min-w-0 break-all text-sm text-muted-foreground">{clip.name}</span>}
          </div>
        </section>

        <section aria-labelledby="step2" className="flex flex-col gap-3">
          <h2 id="step2" className="text-sm font-medium">2. Gates and distance</h2>
          <p className="text-sm text-muted-foreground">{STUDY_COPY.gates}</p>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <label htmlFor={ids.dist} className="flex flex-col gap-1 text-sm">
              Distance between the marks (m)
              <input id={ids.dist} inputMode="decimal" value={distance}
                onChange={(e) => setDistance(e.target.value)} placeholder="10.0"
                className="h-9 rounded-md border bg-muted px-3 font-mono" />
            </label>
            <label htmlFor={ids.limit} className="flex flex-col gap-1 text-sm">
              Speed limit (km/h, optional)
              <input id={ids.limit} inputMode="numeric" value={limit}
                onChange={(e) => setLimit(e.target.value)} placeholder="30"
                className="h-9 rounded-md border bg-muted px-3 font-mono" />
            </label>
          </div>
        </section>

        <section aria-labelledby="step3" className="flex flex-col gap-3">
          <h2 id="step3" className="text-sm font-medium">3. Run</h2>
          <div className="flex flex-wrap items-center gap-3">
            <Button size="lg" onClick={() => void onRun()} disabled={!canRun}>
              Run the study
            </Button>
            <Button asChild variant="ghost">
              <Link href={runId ? `/study/report?run=${encodeURIComponent(runId)}` : "/study/report"}>
                Printable report
              </Link>
            </Button>
          </div>
          <p className="min-h-5 text-sm text-muted-foreground">
            {health && !health.live_runs_enabled && "Live studies are off right now."}
          </p>
          <div aria-live="polite" className="empty:hidden">
            {phase.kind === "uploading" && (
              <div className="flex flex-col gap-2">
                <p className="text-sm">{COPY.uploading(phase.n)}</p>
                <Progress value={phase.n} aria-label="Upload progress" />
              </div>
            )}
            {phase.kind === "working" && <p className="text-sm">{COPY.preparing}</p>}
            {phase.kind === "cap" && (
              <div className="rounded-lg border bg-card px-4 py-3 text-sm">
                <p>Live studies are paused for now.</p>
                <p className="text-muted-foreground">{phase.message}</p>
              </div>
            )}
            {phase.kind === "error" && (
              <div className="flex flex-wrap items-center justify-between gap-4 rounded-lg border bg-card px-4 py-3 text-sm">
                <p>{COPY.error}</p>
                <Button variant="outline" size="sm" onClick={() => void onRun()} disabled={!canRun}>
                  Retry
                </Button>
              </div>
            )}
          </div>
        </section>

        <StudySummaryCard summary={summary} />

        <nav aria-label="Recorded studies" className="flex flex-col gap-2">
          <h2 className="text-sm font-medium">Recorded studies</h2>
          {studies.length === 0 ? (
            <Placeholder title="No recorded study yet">
              The first recorded study will be our own Hyderabad street clip (Phase 4).
            </Placeholder>
          ) : (
            <ul className="flex flex-col gap-1">
              {studies.map((r) => (
                <li key={r.run_id}>
                  <Button variant="ghost" onClick={() => pick(r.run_id)}
                    aria-current={runId === r.run_id ? "true" : undefined}
                    className="h-auto w-full justify-between gap-3 px-3 py-2 text-left font-normal">
                    <span className="min-w-0 whitespace-normal break-words">{r.title}</span>
                    {r.placeholder && <PlaceholderTag />}
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </nav>
      </div>
    </div>
  );
}
