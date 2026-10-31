"use client";

import { Button } from "@/components/ui/button";
import type { RunIndexEntry } from "@/lib/types";
import { cn } from "@/lib/utils";

interface RunPickerProps {
  runs: RunIndexEntry[];
  selected: string | null;
  onPick: (runId: string) => void;
}

/** Recorded runs: always available, never count against live caps. */
export function RunPicker({ runs, selected, onPick }: RunPickerProps) {
  if (runs.length === 0) return null;
  return (
    <nav aria-label="Recorded runs" className="flex flex-col gap-2">
      <h2 className="text-sm font-medium">Recorded runs</h2>
      <ul className="flex flex-col gap-1">
        {runs.map((r) => (
          <li key={r.run_id}>
            <Button
              variant="ghost"
              onClick={() => onPick(r.run_id)}
              aria-current={selected === r.run_id ? "true" : undefined}
              className={cn(
                "h-auto w-full justify-between gap-3 px-3 py-2 text-left font-normal",
                selected === r.run_id && "bg-muted",
              )}
            >
              <span className="truncate">{r.title}</span>
              <span className="flex shrink-0 items-center gap-2 text-xs text-muted-foreground">
                {r.placeholder && <span className="rounded-sm border border-dashed px-1">placeholder</span>}
                <span className={r.status === "measured" ? "text-primary" : "text-foreground"}>
                  {r.status === "measured" ? "Measured" : "Abstained"}
                </span>
              </span>
            </Button>
          </li>
        ))}
      </ul>
    </nav>
  );
}
