"use client";

import { useEffect, useState } from "react";

/**
 * Shown while a live run works on the server. The stages are the order the server works in;
 * the server does not report which one is running, so none is marked as current.
 */
export function LiveWait({ steps }: { steps: readonly string[] }) {
  const [t0] = useState(() => Date.now());
  const [now, setNow] = useState(t0);
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);
  const s = Math.floor((now - t0) / 1000);
  const elapsed = `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
  return (
    <div className="flex flex-col gap-2 rounded-lg border bg-card px-4 py-3 text-sm" role="status" aria-live="polite">
      <p className="font-medium">
        A live run takes about 2 to 4 minutes; recorded runs are instant.
        <span className="ml-2 font-mono text-muted-foreground tabular-nums">{elapsed}</span>
      </p>
      <p className="text-xs text-muted-foreground">What the server does, in order:</p>
      <ol className="list-inside list-decimal text-muted-foreground">
        {steps.map((step) => (
          <li key={step}>{step}</li>
        ))}
      </ol>
      <p className="text-xs text-muted-foreground">You can leave this page open; the result appears here when it is ready.</p>
    </div>
  );
}
