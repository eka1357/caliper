"use client";

import { motion, useReducedMotion } from "motion/react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { cardEnter, reducedFade } from "@/lib/motion";
import type { CachedRun, Guess } from "@/lib/types";
import { COPY, fixFor } from "./copy";
import { Readout } from "./Readout";

interface ResultCardProps {
  run: CachedRun;
  guess: Guess | null;
  compare: boolean;
}

/** Measured and Abstained look equally deliberate (DESIGN principle 3). */
export function ResultCard({ run, guess, compare }: ResultCardProps) {
  const reduce = useReducedMotion();
  const r = run.result;
  const measured = r.status === "measured" && r.value !== null;
  const enter = reduce
    ? { initial: { opacity: 0 }, animate: { opacity: 1 }, exit: { opacity: 0 }, transition: reducedFade }
    : cardEnter;
  return (
    <motion.div {...enter}>
      <Card className="gap-4 rounded-lg border bg-card py-5">
        <CardContent className="flex flex-col gap-4 px-5">
          <div className="flex flex-wrap items-center gap-2">
            {measured ? (
              <Badge>Measured</Badge>
            ) : (
              <Badge variant="outline" className="border-destructive/60 text-foreground">
                <span className="size-1.5 rounded-full bg-destructive" aria-hidden />
                Abstained
              </Badge>
            )}
            {run.meta.placeholder && <PlaceholderBadge />}
          </div>
          {measured && r.value !== null ? (
            <>
              <Readout value={r.value} unit={r.unit} interval={r.interval_90} />
              <p className="text-sm text-muted-foreground">{r.method.split(";").slice(0, 3).join(";")}</p>
            </>
          ) : (
            <div className="flex flex-col gap-2">
              <p className="text-2xl font-medium">{COPY.abstained}</p>
              <p className="text-foreground">{r.abstain_reason}</p>
              <p className="text-sm text-muted-foreground">Try this: {fixFor(r)}</p>
            </div>
          )}
          {compare && (
            <GuessLine guess={guess ?? run.guess ?? null} live={run.meta.source === "live"} />
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
}

export function PlaceholderBadge() {
  return (
    <Badge variant="outline" className="border-dashed text-muted-foreground">
      Placeholder · synthetic test clip
    </Badge>
  );
}

/** Guesses look like guesses: dimmed, dashed border, labelled (DESIGN principle 4). */
function GuessLine({
  guess,
  live,
}: {
  guess: Pick<Guess, "text" | "parsed_value"> | null;
  live: boolean;
}) {
  return (
    <div className="rounded-md border border-dashed border-border px-3 py-2 text-muted-foreground">
      <p className="text-xs uppercase tracking-wide">Muse Spark alone · guess</p>
      {guess ? (
        <p className="text-sm">
          {guess.parsed_value !== null && (
            <span className="font-mono tabular mr-2">{guess.parsed_value}</span>
          )}
          {guess.text}
        </p>
      ) : (
        <p className="text-sm">
          {live ? "Waiting for the guess." : "No recorded guess for this run."}
        </p>
      )}
    </div>
  );
}
