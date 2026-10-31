"use client";

import { AnimatePresence, LayoutGroup, motion } from "motion/react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import * as api from "@/lib/api";
import { fitWindowS } from "@/lib/format";
import { layoutSpring } from "@/lib/motion";
import type { CachedRun, Guess, Health, RunIndexEntry } from "@/lib/types";
import { useObjectUrl } from "@/lib/useObjectUrl";
import { ChainPanel } from "./ChainPanel";
import { ControlPanel } from "./ControlPanel";
import { COPY, LIVE_STEPS } from "./copy";
import { ResultCard } from "./ResultCard";
import { RunPicker } from "./RunPicker";
import { VideoStage } from "./VideoStage";

type Phase =
  | { kind: "idle" }
  | { kind: "uploading"; n: number }
  | { kind: "working" }
  | { kind: "done" }
  | { kind: "cap"; message: string }
  | { kind: "error" };

export function Workspace() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const [runs, setRuns] = useState<RunIndexEntry[]>([]);
  const [health, setHealth] = useState<Health | null>(null);
  const [run, setRun] = useState<CachedRun | null>(null);
  const [runId, setRunId] = useState<string | null>(params.get("run"));
  const [phase, setPhase] = useState<Phase>({ kind: "idle" });
  const [clip, setClip] = useState<File | null>(null);
  const [question, setQuestion] = useState("");
  const [prior, setPrior] = useState("");
  const [compare, setCompare] = useState(false);
  const [guess, setGuess] = useState<Guess | null>(null);
  const [seekTo, setSeekTo] = useState<{ frame: number; n: number } | null>(null);
  const abort = useRef<AbortController | null>(null);
  const localUrl = useObjectUrl(clip);

  useEffect(() => {
    void api.listRuns().then((list) => {
      setRuns(list);
      setRunId((id) => id ?? list[0]?.run_id ?? null);
    });
    void api.health().then(setHealth);
  }, []);

  useEffect(() => {
    if (!runId || runId.startsWith("live-")) return;
    let live = true;
    api.getRun(runId).then(
      (r) => {
        if (!live) return;
        setRun(r);
        setGuess(null);
        setQuestion(r.meta.question);
        setPhase({ kind: "done" });
      },
      () => live && setPhase({ kind: "error" }),
    );
    return () => {
      live = false;
    };
  }, [runId]);

  const pick = useCallback(
    (id: string) => {
      abort.current?.abort();
      setClip(null);
      setRunId(id);
      router.replace(`${pathname}?run=${encodeURIComponent(id)}`, { scroll: false });
    },
    [router, pathname],
  );

  const onClip = (f: File) => {
    setClip(f);
    setRun(null);
    setRunId(null);
    setGuess(null);
    setPhase({ kind: "idle" });
  };

  const onMeasure = async () => {
    if (!clip) return;
    abort.current?.abort();
    const ctrl = new AbortController();
    abort.current = ctrl;
    const input = { video: clip, question, prior: prior || undefined };
    setRun(null);
    setGuess(null);
    setPhase({ kind: "uploading", n: 0 });
    if (compare) void api.guess(input, ctrl.signal).then(setGuess, () => setGuess(null));
    try {
      const result = await api.measure(
        input,
        (n) => setPhase(n >= 100 ? { kind: "working" } : { kind: "uploading", n }),
        ctrl.signal,
      );
      setRun(result);
      setRunId(result.result.run_id);
      setPhase({ kind: "done" });
    } catch (e) {
      if (ctrl.signal.aborted) return;
      if (e instanceof api.ApiError && e.isCap) {
        if (e.body.cached_runs?.length) setRuns(e.body.cached_runs);
        setPhase({ kind: "cap", message: e.body.message });
      } else setPhase({ kind: "error" });
    }
  };

  const live = run?.meta.source === "live";
  const src = live ? localUrl : run ? api.runAsset(run.result.run_id, run.meta.clip) : localUrl;
  const poster = run && !live ? api.runAsset(run.result.run_id, run.meta.poster) : null;
  const fitWindow = useMemo(() => {
    const t0 = run?.result.spec.timestamp_s;
    const w = run ? fitWindowS(run.result.method) : null;
    return t0 != null && w ? ([t0 - w / 2, t0 + w / 2] as [number, number]) : null;
  }, [run]);
  const busy = phase.kind === "uploading" || phase.kind === "working";

  return (
    <div className="mx-auto grid w-full max-w-[1440px] grid-cols-1 gap-6 px-4 py-6 lg:grid-cols-12 lg:px-8">
      <div className="flex min-w-0 flex-col gap-4 lg:col-span-7">
        <VideoStage src={src} poster={poster} overlay={run?.overlay ?? null} fitWindow={fitWindow}
          seekTo={seekTo} />
        <p className="min-h-5 text-sm text-muted-foreground">
          {health && !health.live_runs_enabled && "Live runs are off right now. The recorded runs work."}
        </p>
      </div>
      <LayoutGroup>
        <motion.div layout="position" transition={layoutSpring} className="flex min-w-0 flex-col gap-5 lg:col-span-5">
          <ControlPanel
            question={question} onQuestion={setQuestion} prior={prior} onPrior={setPrior}
            compare={compare} onCompare={setCompare} clip={clip} onClip={onClip} busy={busy}
            onMeasure={() => void onMeasure()}
          />
          <Status phase={phase} onRetry={() => void onMeasure()} />
          <AnimatePresence mode="wait">
            {run && phase.kind === "done" && (
              <motion.div key={run.result.run_id} layout transition={layoutSpring} className="flex flex-col gap-4">
                <ResultCard run={run} guess={guess} compare={compare} />
                <ChainPanel run={run}
                  onSeekFrame={(frame) => setSeekTo((s) => ({ frame, n: (s?.n ?? 0) + 1 }))} />
              </motion.div>
            )}
          </AnimatePresence>
          <RunPicker runs={runs} selected={runId} onPick={pick} />
        </motion.div>
      </LayoutGroup>
    </div>
  );
}

function Status({ phase, onRetry }: { phase: Phase; onRetry: () => void }) {
  return (
    <div aria-live="polite" className="empty:hidden">
      {phase.kind === "uploading" && (
        <div className="flex flex-col gap-2">
          <p className="text-sm">{COPY.uploading(phase.n)}</p>
          <Progress value={phase.n} aria-label="Upload progress" />
        </div>
      )}
      {phase.kind === "working" && (
        <div className="flex flex-col gap-1 rounded-lg border bg-card px-4 py-3 text-sm">
          <p>{COPY.preparing}</p>
          <ol className="list-inside list-decimal text-muted-foreground">
            {LIVE_STEPS.slice(1).map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ol>
          <p className="text-xs text-muted-foreground">A live run takes about a minute.</p>
        </div>
      )}
      {phase.kind === "cap" && (
        <div className="rounded-lg border bg-card px-4 py-3 text-sm">
          <p>{COPY.cap}</p>
          <p className="text-muted-foreground">{phase.message}</p>
        </div>
      )}
      {phase.kind === "error" && (
        <div className="flex items-center justify-between gap-4 rounded-lg border bg-card px-4 py-3 text-sm">
          <p>{COPY.error}</p>
          <Button variant="outline" size="sm" onClick={onRetry}>
            Retry
          </Button>
        </div>
      )}
    </div>
  );
}
