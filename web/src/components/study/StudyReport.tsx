"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useId, useState } from "react";
import { Placeholder } from "@/components/site/Placeholder";
import { Button } from "@/components/ui/button";
import * as api from "@/lib/api";
import type { CachedStudyRun } from "@/lib/types";
import { STUDY_COPY } from "./copy";
import { SpeedHistogram } from "./SpeedHistogram";
import { StudySummaryCard } from "./StudySummaryCard";
import { VehicleTable } from "./VehicleTable";

/** Clean page for window.print(): date, place, method, summary, histogram, table, limitations. */
export function StudyReport() {
  const params = useSearchParams();
  const runId = params.get("run");
  const placeId = useId();
  const [run, setRun] = useState<CachedStudyRun | null>(null);
  const [failed, setFailed] = useState(false);
  const [place, setPlace] = useState("");

  useEffect(() => {
    if (!runId) return;
    api.getStudyRun(runId).then(setRun, () => setFailed(true));
  }, [runId]);

  const summary = run?.result ?? null;
  const date = run ? new Date(run.meta.created_utc).toLocaleDateString() : null;

  return (
    <article className="mx-auto flex w-full max-w-[800px] flex-col gap-8 px-4 py-10">
      <div className="flex flex-wrap items-center justify-between gap-3 print:hidden">
        <Button asChild variant="ghost" className="px-0">
          <Link href={runId ? `/study?run=${encodeURIComponent(runId)}` : "/study"}>Back to the study</Link>
        </Button>
        <Button onClick={() => window.print()} disabled={!summary}>
          Print
        </Button>
      </div>

      <header className="flex flex-col gap-3">
        <h1 className="text-3xl font-medium">{STUDY_COPY.title}</h1>
        <dl className="grid grid-cols-1 gap-x-6 gap-y-2 text-sm sm:grid-cols-[max-content_1fr]">
          <dt className="text-muted-foreground">Date of filming</dt>
          <dd className="font-mono">{date ?? "n/a"}</dd>
          <dt className="text-muted-foreground">
            <label htmlFor={placeId}>Place</label>
          </dt>
          <dd>
            <input
              id={placeId}
              value={place}
              onChange={(e) => setPlace(e.target.value)}
              placeholder="Street and city"
              className="h-8 w-full rounded-md border bg-muted px-2 print:border-0 print:bg-transparent print:px-0"
            />
          </dd>
        </dl>
        {run?.meta.placeholder && (
          <p className="text-sm text-destructive">Placeholder run: not a real street survey.</p>
        )}
      </header>

      <section className="flex flex-col gap-2">
        <h2 className="text-lg font-medium">Method</h2>
        <p className="text-sm text-muted-foreground">{STUDY_COPY.method}</p>
      </section>

      {failed && <p className="text-sm">This study could not be loaded.</p>}
      {!summary ? (
        <Placeholder title="No study selected">
          {STUDY_COPY.noStudy} Open a recorded study on the study page, then come back here to print
          it.
        </Placeholder>
      ) : (
        <>
          <section className="flex flex-col gap-3">
            <h2 className="text-lg font-medium">Summary</h2>
            <StudySummaryCard summary={summary} />
          </section>
          <section className="flex flex-col gap-3 break-inside-avoid">
            <h2 className="text-lg font-medium">Speeds</h2>
            <SpeedHistogram summary={summary} />
          </section>
          <section className="flex flex-col gap-3">
            <h2 className="text-lg font-medium">Every vehicle</h2>
            <VehicleTable readings={summary.readings} />
          </section>
        </>
      )}

      <section className="flex flex-col gap-2">
        <h2 className="text-lg font-medium">Limitations</h2>
        <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">
          {STUDY_COPY.limitations.map((l) => (
            <li key={l}>{l}</li>
          ))}
        </ul>
      </section>
      <p className="text-xs text-muted-foreground">
        Made with Caliper (Muse Spark 1.3 and SAM 3.1 on Meta Model API). {STUDY_COPY.privacy}
      </p>
    </article>
  );
}
