"use client";

import { ChevronDown } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { fmtMs, fmtUsd } from "@/lib/format";
import type { CachedRun, Check } from "@/lib/types";
import { cn } from "@/lib/utils";
import { PositionChart, SpeedChart } from "./FitChart";

/** "Show the chain": every number expands into spec, scale, fit, checks and audit. */
export function ChainPanel({
  run,
  onSeekFrame,
}: {
  run: CachedRun;
  onSeekFrame: (frame: number) => void;
}) {
  const [open, setOpen] = useState(false);
  const r = run.result;
  return (
    <Collapsible open={open} onOpenChange={setOpen} className="rounded-lg border bg-card">
      <CollapsibleTrigger asChild>
        <Button variant="ghost" className="h-11 w-full justify-between px-4">
          Show the chain
          <ChevronDown className={cn("transition-transform", open && "rotate-180")} aria-hidden />
        </Button>
      </CollapsibleTrigger>
      <CollapsibleContent className="flex flex-col gap-6 border-t px-4 py-4">
        <Section title="Spec">
          <pre
            className="max-h-64 overflow-auto rounded-md bg-muted p-3 font-mono text-xs leading-relaxed"
            tabIndex={0}
            aria-label="Measurement spec JSON"
          >
            {JSON.stringify(r.spec, null, 2)}
          </pre>
          {run.meta.placeholder && (
            <p className="text-xs text-muted-foreground">Typed by hand for this placeholder; no model call.</p>
          )}
        </Section>
        <Section title="Scale">
          <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
            <dt className="text-muted-foreground">Reference</dt>
            <dd>{r.spec.reference_phrase ?? "the target itself"}</dd>
            <dt className="text-muted-foreground">Value</dt>
            <dd className="font-mono tabular">
              {r.spec.reference_value_si ?? "n/a"} {r.spec.reference_value_si !== null && "m"}
            </dd>
            <dt className="text-muted-foreground">Source</dt>
            <dd>{r.spec.reference_source || "n/a"}</dd>
            <dt className="text-muted-foreground">Metres per pixel</dt>
            <dd className="font-mono tabular">
              {r.scale_m_per_px !== null ? r.scale_m_per_px.toPrecision(4) : "n/a"}
            </dd>
          </dl>
        </Section>
        <Section title="Fit">
          <p className="text-sm text-muted-foreground">{r.method}</p>
          <PositionChart rows={run.overlay.fit ?? []} />
          {r.quantity !== "size" && <SpeedChart rows={run.overlay.speed ?? []} />}
        </Section>
        <Section title="Checks">
          <ChecksTable checks={r.checks} />
        </Section>
        <Section title="Audit">
          {r.audit ? (
            <div className="flex flex-col gap-1 text-sm">
              <p>{r.audit.approve ? "Approved: the evidence matches the question." : `Vetoed: ${r.audit.reason}`}</p>
              <p className="text-muted-foreground">
                Right target: {yes(r.audit.target_is_right_object)}. Right reference:{" "}
                {yes(r.audit.reference_is_right_object)}. Same plane: {r.audit.reference_same_plane}.
                Occlusion or identity switch: {yes(r.audit.occlusion_or_identity_switch)}.
              </p>
              <AuditKeyframes run={run} onSeekFrame={onSeekFrame} />
              {run.meta.notes.includes("scripted") && (
                <p className="text-xs text-muted-foreground">Verdict scripted for this placeholder; no model call.</p>
              )}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              {r.checks.some((c) => !c.passed) ? "Not run: a check refused first." : "Not run."}
            </p>
          )}
        </Section>
        <Section title="Backend">
          <p className="text-sm">
            {run.meta.placeholder
              ? "None: placeholder run (engine and checks only, no model calls)"
              : r.backend === "meta_api"
                ? "Meta Model API (Muse Spark 1.3, SAM 3.1)"
                : "Muse Spark Open"}
          </p>
        </Section>
        <Section title="Cost and timing">
          <p className="font-mono tabular text-sm">
            {fmtUsd(r.cost_usd)}
            {r.timings_ms.total !== undefined && ` · ${fmtMs(r.timings_ms.total)}`}
          </p>
        </Section>
      </CollapsibleContent>
    </Collapsible>
  );
}

/** The keyframes Muse Spark saw: each button shows that frame on the stage, with outlines. */
function AuditKeyframes({ run, onSeekFrame }: { run: CachedRun; onSeekFrame: (f: number) => void }) {
  const call = run.result.artifacts.audit_call as { keyframes?: unknown } | undefined;
  const frames = Array.isArray(call?.keyframes)
    ? call.keyframes.filter((f): f is number => typeof f === "number")
    : [];
  if (frames.length === 0) return null;
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="text-muted-foreground">Muse Spark saw frames:</span>
      {frames.map((f) => (
        <Button key={f} variant="outline" size="xs" onClick={() => onSeekFrame(f)}
          aria-label={`Show frame ${f} on the video`}>
          <span className="font-mono tabular">{f}</span>
        </Button>
      ))}
    </div>
  );
}

function yes(b: boolean) {
  return b ? "yes" : "no";
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-2">
      <h3 className="text-sm font-medium">{title}</h3>
      {children}
    </section>
  );
}

function ChecksTable({ checks }: { checks: Check[] }) {
  if (checks.length === 0) return <p className="text-sm text-muted-foreground">No checks ran.</p>;
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Check</TableHead>
          <TableHead className="text-right">Value</TableHead>
          <TableHead>Threshold</TableHead>
          <TableHead>Result</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {checks.map((c) => (
          <TableRow key={c.name}>
            <TableCell className="font-mono text-xs">{c.name}</TableCell>
            <TableCell className="font-mono tabular text-right text-xs">
              {c.value !== null ? Number(c.value.toPrecision(3)) : "n/a"}
            </TableCell>
            <TableCell className="text-xs text-muted-foreground">{c.threshold}</TableCell>
            <TableCell className={cn("text-xs", c.passed ? "text-success" : "text-destructive")}>
              {c.passed ? "pass" : "fail"}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
