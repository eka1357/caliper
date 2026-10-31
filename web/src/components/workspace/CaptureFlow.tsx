"use client";

import { useId, useState } from "react";
import { Button } from "@/components/ui/button";
import { useObjectUrl } from "@/lib/useObjectUrl";
import { COPY } from "./copy";

type Step = "closed" | "guide" | "review";

/** Mobile capture: one-screen guide, then the camera, then a review before upload. */
export function CaptureFlow({ onClip }: { onClip: (f: File) => void }) {
  const inputId = useId();
  const [step, setStep] = useState<Step>("closed");
  const [file, setFile] = useState<File | null>(null);
  const url = useObjectUrl(file);

  if (step === "closed") {
    return (
      <Button variant="outline" className="lg:hidden" onClick={() => setStep("guide")}>
        Record a clip
      </Button>
    );
  }

  if (step === "guide") {
    return (
      <div className="flex flex-col gap-3 rounded-lg border bg-card p-4 lg:hidden" role="region"
        aria-label="Before you record">
        <p>{COPY.captureGuide}</p>
        <div className="flex gap-2">
          <Button asChild>
            <label htmlFor={inputId}>Open the camera</label>
          </Button>
          <Button variant="ghost" onClick={() => setStep("closed")}>
            Cancel
          </Button>
        </div>
        <input
          id={inputId}
          type="file"
          accept="video/*"
          capture="environment"
          className="sr-only"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) {
              setFile(f);
              setStep("review");
            }
          }}
        />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3 rounded-lg border bg-card p-4 lg:hidden" role="region"
      aria-label="Review your clip">
      {url && <video src={url} className="aspect-video w-full rounded-md bg-muted" controls muted playsInline />}
      <div className="flex gap-2">
        <Button
          onClick={() => {
            if (file) onClip(file);
            setStep("closed");
          }}
        >
          Use this clip
        </Button>
        <Button variant="ghost" onClick={() => setStep("guide")}>
          Retake
        </Button>
      </div>
    </div>
  );
}
