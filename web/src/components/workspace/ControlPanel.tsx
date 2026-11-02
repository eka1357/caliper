"use client";

import { ChevronDown } from "lucide-react";
import { useId, useState } from "react";
import { Button } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { CaptureFlow } from "./CaptureFlow";
import type { RunIndexEntry } from "@/lib/types";
import { COPY } from "./copy";

interface ControlPanelProps {
  /** The recorded runs (runs/index.json); each chip loads one. */
  examples: RunIndexEntry[];
  selected: string | null;
  onExample: (runId: string) => void;
  question: string;
  onQuestion: (q: string) => void;
  prior: string;
  onPrior: (p: string) => void;
  compare: boolean;
  onCompare: (c: boolean) => void;
  clip: File | null;
  onClip: (f: File) => void;
  busy: boolean;
  onMeasure: () => void;
}

export function ControlPanel(p: ControlPanelProps) {
  const ids = { q: useId(), prior: useId(), compare: useId(), file: useId() };
  const [priorOpen, setPriorOpen] = useState(false);
  const [dragging, setDragging] = useState(false);
  const canMeasure = !p.busy && p.clip !== null && p.question.trim().length >= 3;

  return (
    <section aria-label="Question" className="flex flex-col gap-4">
      <label
        htmlFor={ids.file}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          const f = e.dataTransfer.files[0];
          if (f && f.type.startsWith("video/")) p.onClip(f);
        }}
        className={cn(
          "flex cursor-pointer flex-col gap-1 rounded-lg border border-dashed px-4 py-5 text-sm transition-colors focus-within:outline-2 focus-within:outline-ring",
          dragging ? "border-primary bg-muted" : "bg-card hover:bg-muted",
        )}
      >
        <span className="break-all">{p.clip ? p.clip.name : COPY.idle}</span>
        <span className="text-muted-foreground">MP4 or MOV, a few seconds long.</span>
        <input
          id={ids.file}
          type="file"
          accept="video/*"
          className="sr-only"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) p.onClip(f);
          }}
        />
      </label>
      <CaptureFlow onClip={p.onClip} />

      <div className="flex flex-col gap-2">
        <label htmlFor={ids.q} className="text-sm font-medium">
          Question
        </label>
        <Textarea
          id={ids.q}
          value={p.question}
          onChange={(e) => p.onQuestion(e.target.value)}
          placeholder="What is the length of the phone in cm?"
          maxLength={500}
          rows={3}
        />
        <div className="flex flex-wrap gap-2" aria-label="Recorded examples">
          {p.examples.map((r) => (
            <Button key={r.run_id} variant={r.run_id === p.selected ? "default" : "secondary"} size="xs"
              aria-pressed={r.run_id === p.selected} onClick={() => p.onExample(r.run_id)}
              className="h-auto min-h-6 max-w-full whitespace-normal py-1 text-left">
              {r.title}
            </Button>
          ))}
        </div>
      </div>

      <Collapsible open={priorOpen} onOpenChange={setPriorOpen}>
        <CollapsibleTrigger asChild>
          <Button variant="ghost" size="sm" className="h-auto max-w-full whitespace-normal px-0 text-left text-muted-foreground hover:bg-transparent">
            I know one real size or speed
            <ChevronDown className={cn("transition-transform", priorOpen && "rotate-180")} aria-hidden />
          </Button>
        </CollapsibleTrigger>
        <CollapsibleContent className="pt-2">
          <label htmlFor={ids.prior} className="sr-only">
            One real size or speed
          </label>
          <input
            id={ids.prior}
            value={p.prior}
            onChange={(e) => p.onPrior(e.target.value)}
            placeholder="the box is 50 cm wide"
            maxLength={300}
            className="h-9 w-full rounded-md border bg-muted px-3 text-sm placeholder:text-muted-foreground"
          />
        </CollapsibleContent>
      </Collapsible>

      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex min-w-0 items-center gap-2">
          <Switch id={ids.compare} checked={p.compare} onCheckedChange={p.onCompare} />
          <label htmlFor={ids.compare} className="text-sm">
            Compare with Muse Spark alone
          </label>
        </div>
        <Button size="lg" onClick={p.onMeasure} disabled={!canMeasure} className="px-5">
          Measure
        </Button>
      </div>
    </section>
  );
}
