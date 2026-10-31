import { cn } from "@/lib/utils";

/**
 * A clearly labelled stand-in for data that does not exist yet (field clips and the street study
 * arrive with Phase 4). It never shows a number.
 */
export function Placeholder({
  title,
  children,
  className,
}: {
  title: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      role="note"
      className={cn(
        "flex flex-col gap-2 rounded-lg border border-dashed bg-card/40 p-4 text-sm",
        className,
      )}
    >
      <div className="flex flex-wrap items-center gap-2">
        <PlaceholderTag />
        <span className="font-medium">{title}</span>
      </div>
      <div className="text-muted-foreground">{children}</div>
    </div>
  );
}

export function PlaceholderTag({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        "rounded-sm border border-dashed px-1.5 py-0.5 font-mono text-xs uppercase tracking-wide text-muted-foreground",
        className,
      )}
    >
      Placeholder
    </span>
  );
}
