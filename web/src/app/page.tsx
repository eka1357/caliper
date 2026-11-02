import Link from "next/link";
import { HeroHeadline } from "@/components/landing/HeroHeadline";
import { HeroVisual } from "@/components/landing/HeroVisual";
import { HowItWorks } from "@/components/landing/HowItWorks";
import { KeyframeStill } from "@/components/landing/KeyframeStill";
import { LazyInView } from "@/components/landing/LazyInView";
import { LazyPairedChart } from "@/components/landing/lazy-charts";
import { SmoothScroll } from "@/components/landing/SmoothScroll";
import { FindingList } from "@/components/results/FindingList";
import { Placeholder, PlaceholderTag } from "@/components/site/Placeholder";
import { fixFor } from "@/components/workspace/copy";
import { Button } from "@/components/ui/button";
import { findings } from "@/lib/findings";
import { decimalsFor, fmt } from "@/lib/format";
import { fmtPct } from "@/lib/labels";
import { loadBenchmark } from "@/lib/results";
import { landingRuns } from "@/lib/runs-static";
import type { CachedRun } from "@/lib/types";

const REPO = "https://github.com/eka1357/caliper";
const MORTH =
  "https://www.hindustantimes.com/india-news/road-accident-deaths-increased-2-5-in-2024-from-2023-morth-report-101781204793385.html";

// The story (docs/DESIGN.md section 6). GSAP and Lenis live only on this route. Every number is
// read at build time from eval/results.csv, eval/paired_results.csv or a recorded run JSON.
export default async function Home() {
  const [bench, runs] = await Promise.all([loadBenchmark(), landingRuns()]);
  const { measured, missed, vetoed, abstained } = runs;
  const sizeSet = bench.field_summary.size;

  return (
    <>
      <SmoothScroll />
      <header className="border-b">
        <div className="mx-auto flex min-h-14 w-full min-w-0 max-w-[1200px] flex-wrap items-center justify-between gap-x-4 gap-y-1 px-6 py-2">
          <span className="font-medium">Caliper</span>
          <nav aria-label="Main" className="min-w-0">
            <ul className="flex flex-wrap items-center gap-1 text-sm">
              {[["/workspace", "Workspace"], ["/study", "Speed study"], ["/results", "Evidence"]].map(([h, l]) => (
                <li key={h}>
                  <Link href={h} className="rounded-md px-2 py-1.5 text-muted-foreground hover:text-foreground sm:px-3">
                    {l}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
        </div>
      </header>

      <main className="flex-1">
        {/* 1. Hero */}
        <section className="border-b [background-image:linear-gradient(var(--border)_1px,transparent_1px),linear-gradient(90deg,var(--border)_1px,transparent_1px)] [background-size:24px_24px]">
          <div className="mx-auto grid w-full max-w-[1200px] grid-cols-1 items-center gap-12 px-6 py-[72px] lg:grid-cols-12 lg:py-32">
            <div className="flex min-w-0 flex-col gap-6 lg:col-span-6">
              <HeroHeadline>AI guesses. Caliper measures.</HeroHeadline>
              <p className="max-w-xl text-lg text-muted-foreground">
                Ask how big, how fast, or how hard something accelerates in a video. Get a measured
                number with an error range, or an honest no.
              </p>
              <div className="flex flex-wrap gap-3">
                <Button asChild size="lg">
                  <Link href="/workspace">Measure a clip</Link>
                </Button>
                <Button asChild size="lg" variant="outline">
                  <Link href="/results">See the evidence</Link>
                </Button>
              </div>
            </div>
            <div className="min-w-0 lg:col-span-6">
              {measured ? (
                <HeroVisual run={measured} />
              ) : (
                <Placeholder title="Hero clip">No recorded run yet.</Placeholder>
              )}
            </div>
          </div>
        </section>

        {/* 2. The gap */}
        <Section id="gap" title="Same model. Same video. One guesses, one measures.">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <GuessCard run={measured} />
            <MeasuredCard run={measured} />
            <InstrumentCard run={measured} />
          </div>
          {measured && <p className="text-sm text-muted-foreground">Question: {measured.meta.question}</p>}
        </Section>

        {/* 3. How it works */}
        <Section id="how" title="How it works">
          {measured ? <HowItWorks run={measured} /> : <Placeholder title="How it works">No recorded run yet.</Placeholder>}
        </Section>

        {/* 4. The audit */}
        <Section id="audit" title="The audit can only say no">
          <p className="max-w-3xl text-muted-foreground">
            After the numbers are computed, Muse Spark looks at keyframes with the outlines drawn on
            them and checks the evidence: the right object, the right reference, the same plane. It
            can veto a result. It can never change a number.
          </p>
          {vetoed?.result.audit ? (
            <div className="grid grid-cols-1 items-start gap-6 md:grid-cols-2">
              <KeyframeStill run={vetoed} />
              <div className="flex flex-col gap-3 rounded-lg border bg-card p-5">
                <p className="flex flex-wrap items-center gap-2 text-sm">
                  <span className="text-destructive">Vetoed</span>
                  {vetoed.meta.placeholder && <PlaceholderTag />}
                </p>
                <p>{vetoed.result.audit.reason}</p>
                <p className="text-sm text-muted-foreground">Question: {vetoed.meta.question}</p>
                {vetoed.meta.placeholder && (
                  <p className="text-xs text-muted-foreground">
                    Placeholder: this verdict is scripted on a synthetic scene to show the flow; no
                    model was called.
                  </p>
                )}
              </div>
            </div>
          ) : (
            <Placeholder title="Audit example">No recorded veto yet.</Placeholder>
          )}
        </Section>

        {/* 5. On a real street */}
        <Section id="street" title="On a real street">
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
            <div className="flex flex-col gap-4">
              <p className="text-muted-foreground">
                Film a street for a few minutes with two marks a measured distance apart. Caliper
                measures every vehicle it can, gives each an error range, refuses the ones it
                cannot measure, and reports the 85th-percentile speed: the number traffic engineers
                use to decide on calming.
              </p>
              <p className="text-sm text-muted-foreground">
                India recorded 177,175 road deaths in 2024, and the transport ministry attributes
                70.3% of them to over-speeding (
                <a className="underline underline-offset-4" href={MORTH}>
                  Hindustan Times on the MoRTH 2024 report
                </a>
                ).
              </p>
              <Button asChild variant="outline" className="w-fit">
                <Link href="/study">Run a speed study</Link>
              </Button>
            </div>
            <Placeholder title="Street study still and 85th-percentile card">
              Our own street clip with every vehicle tagged by speed and range arrives with Phase 4.
              No study number is shown until it has been measured.
            </Placeholder>
          </div>
        </Section>

        {/* 6. Evidence */}
        <Section id="evidence" title="The evidence, including what does not work yet">
          <p className="max-w-3xl text-muted-foreground">
            Scored with the official evaluator on Stanford&apos;s QuantiPhy validation set. These
            sentences are generated from our results files.
          </p>
          <FindingList items={findings(bench)} />
          <LazyInView minHeight={480}>
            <LazyPairedChart rows={bench.paired} />
          </LazyInView>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {sizeSet ? (
              <div className="flex flex-col gap-2 rounded-lg border bg-card p-5">
                <p className="text-sm text-muted-foreground">Our own clips: size against a tape measure</p>
                <p className="flex items-baseline gap-2">
                  <span className="font-mono text-4xl tabular-nums">{fmtPct(sizeSet.median_rel_error)}</span>
                  <span className="text-sm text-muted-foreground">median error, {sizeSet.measured} of {sizeSet.n} clips measured</span>
                </p>
                <p className="text-sm text-muted-foreground">
                  Truth inside the 90% range on {sizeSet.coverage == null ? "n/a" : Math.round(sizeSet.coverage * sizeSet.measured)} of{" "}
                  {sizeSet.measured}. Muse Spark alone, given the same coin size: {fmtPct(sizeSet.guess_median_rel_error)} median
                  error, with no range.
                </p>
              </div>
            ) : (
              <Placeholder title="Field set accuracy">No field clip has been scored.</Placeholder>
            )}
            {missed ? <MissCard run={missed} /> : (
              <Placeholder title="Speed study against GPS">
                Not validated yet: the gate method needs a Set A filmed with the markers in the car&apos;s lane.
              </Placeholder>
            )}
          </div>
          <Button asChild variant="outline" className="w-fit">
            <Link href="/results">All results and the method</Link>
          </Button>
        </Section>

        {/* 7. When Caliper says no */}
        <Section id="no" title="When Caliper says no">
          <ul className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {abstained.map((r) => (
              <li key={r.result.run_id} className="flex flex-col gap-3 rounded-lg border bg-card p-5">
                <KeyframeStill run={r} />
                <p className="flex flex-wrap items-center gap-2 text-sm">
                  <span className="text-destructive">Abstained</span>
                  {r.meta.placeholder && <PlaceholderTag />}
                </p>
                <p>I won&apos;t guess. {r.result.abstain_reason}</p>
                <p className="text-sm text-muted-foreground">Fix: {fixFor(r.result)}</p>
              </li>
            ))}
          </ul>
        </Section>
      </main>

      {/* 9. Footer */}
      <footer className="border-t">
        <div className="mx-auto flex w-full max-w-[1200px] flex-col gap-3 px-6 py-12 text-sm text-muted-foreground">
          <p>Built with Muse Spark 1.3 and SAM 3.1 on Meta Model API. Built Oct 27 to Nov 4 2026.</p>
          <p>
            Benchmark: Stanford QuantiPhy validation set; annotations CC BY 4.0. Its videos keep
            their own licenses, are used for evaluation only, and never appear on this site.
          </p>
          <p className="flex flex-wrap gap-x-6 gap-y-2">
            <a className="underline underline-offset-4" href={REPO}>Source on GitHub</a>
            <Link className="underline underline-offset-4" href="/results">Limitations and results</Link>
          </p>
        </div>
      </footer>
    </>
  );
}

function Section({ id, title, children }: { id: string; title: string; children: React.ReactNode }) {
  return (
    <section id={id} aria-labelledby={`${id}-h`} className="border-b">
      <div className="mx-auto flex w-full max-w-[1200px] flex-col gap-8 px-6 py-[72px] lg:py-32">
        <h2 id={`${id}-h`} className="font-display text-4xl leading-tight sm:text-5xl">{title}</h2>
        {children}
      </div>
    </section>
  );
}

function MeasuredCard({ run }: { run: CachedRun | null }) {
  const r = run?.result;
  if (!run || !r || r.value == null) return <Placeholder title="Caliper">No measured run yet.</Placeholder>;
  const d = decimalsFor(r.interval_90, r.value);
  return (
    <div className="flex flex-col gap-2 rounded-lg border bg-card p-5">
      <p className="flex flex-wrap items-center gap-2 text-sm">
        <span className="text-primary">Caliper</span>
        {run.meta.placeholder && <PlaceholderTag />}
      </p>
      <p className="flex items-baseline gap-2">
        <span className="font-mono text-4xl tabular-nums">{fmt(r.value, d)}</span>
        <span className="font-mono text-muted-foreground">{r.unit}</span>
      </p>
      {r.interval_90 && (
        <p className="font-mono text-xs tabular-nums text-muted-foreground">
          90% range {fmt(r.interval_90[0], d)} to {fmt(r.interval_90[1], d)}
        </p>
      )}
    </div>
  );
}

function InstrumentCard({ run }: { run: CachedRun | null }) {
  const ins = run?.meta.instrument;
  if (!run || !ins || ins.value == null) {
    return <Placeholder title="Instrument">No instrument reading for this run.</Placeholder>;
  }
  return (
    <div className="flex flex-col gap-2 rounded-lg border bg-card p-5">
      <p className="text-sm text-muted-foreground">Instrument · {ins.instrument}</p>
      <p className="flex items-baseline gap-2">
        <span className="font-mono text-4xl tabular-nums">{ins.value}</span>
        <span className="font-mono text-muted-foreground">{ins.unit}</span>
      </p>
      <p className="text-xs text-muted-foreground">Measured by hand when the clip was filmed.</p>
    </div>
  );
}

/** A measured run whose instrument reading falls outside its range: shown, not hidden. */
function MissCard({ run }: { run: CachedRun }) {
  const r = run.result;
  const ins = run.meta.instrument;
  if (r.value == null || !ins || ins.value == null) return null;
  const d = decimalsFor(r.interval_90, r.value);
  return (
    <div className="flex flex-col gap-3 rounded-lg border bg-card p-5">
      <KeyframeStill run={run} />
      <p className="text-sm"><span className="text-destructive">A miss we show</span> · {run.meta.question}</p>
      <p className="font-mono text-sm tabular-nums">
        Caliper {fmt(r.value, d)} {r.unit}
        {r.interval_90 && ` (90% range ${fmt(r.interval_90[0], d)} to ${fmt(r.interval_90[1], d)})`} · {ins.instrument} {ins.value} {ins.unit}
      </p>
      <p className="text-sm text-muted-foreground">{run.meta.notes}</p>
    </div>
  );
}

function GuessCard({ run }: { run: CachedRun | null }) {
  const g = run?.guess;
  if (!g || g.parsed_value == null) {
    return (
      <div className="flex flex-col gap-2 rounded-lg border border-dashed bg-card/40 p-5 text-muted-foreground">
        <p className="flex items-center gap-2 text-sm">
          Muse Spark alone <PlaceholderTag />
        </p>
        <p className="text-sm">No recorded guess for this run.</p>
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-2 rounded-lg border border-dashed bg-card/40 p-5 text-muted-foreground">
      <p className="text-sm">Muse Spark alone · guess</p>
      <p className="flex items-baseline gap-2">
        <span className="font-mono text-4xl tabular-nums">{g.parsed_value}</span>
        <span className="font-mono">{run?.result.unit}</span>
      </p>
      <p className="text-xs">No range: a guess has none.</p>
    </div>
  );
}
