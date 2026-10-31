import type { Finding } from "@/lib/findings";
import { cn } from "@/lib/utils";

/** Findings and limitations side by side, in the same weight: a caveat is part of the result. */
export function FindingList({ items, className }: { items: Finding[]; className?: string }) {
  return (
    <ul className={cn("grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3", className)}>
      {items.map((f) => (
        <li key={f.id} className="flex flex-col gap-2 rounded-lg border bg-card p-4">
          <p className="flex items-center gap-2 text-xs text-muted-foreground">
            <span
              aria-hidden
              className={cn("size-1.5 rounded-full", f.kind === "limit" ? "bg-destructive" : "bg-success")}
            />
            {f.kind === "limit" ? "Limitation" : "Finding"}
          </p>
          <h3 className="font-medium">{f.title}</h3>
          <p className="text-sm text-muted-foreground">{f.body}</p>
          <p className="mt-auto pt-1 font-mono text-xs text-muted-foreground">{f.source}</p>
        </li>
      ))}
    </ul>
  );
}
