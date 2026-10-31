import type { Metadata } from "next";
import { PairedChart, SplitCharts } from "@/components/results/BenchmarkCharts";
import { FindingList } from "@/components/results/FindingList";
import { Placeholder } from "@/components/site/Placeholder";
import { SiteHeader } from "@/components/site/SiteHeader";
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { findings } from "@/lib/findings";
import { fmtMra, fmtPct, splitLabel, VARIANT_NOTE, variantLabel } from "@/lib/labels";
import { caliperOn, loadBenchmark, splitsPresent } from "@/lib/results";

export const metadata: Metadata = { title: "Evidence · Caliper" };

const REPO = "https://github.com/eka1357/caliper/blob/main";

// No GSAP, no Lenis, no decorative components on this route (AGENTS.md section 9).
// Every number below is read from eval/results.csv or eval/paired_results.csv at build time.
export default async function ResultsPage() {
  const bench = await loadBenchmark();
  const splits = splitsPresent(bench);
  const initial = splits.find((s) => caliperOn(bench, s)) ?? splits[0] ?? "dev";
  const variants = [...new Set(bench.results.map((r) => r.variant))];

  return (
    <>
      <SiteHeader current="/results" />
      <main className="mx-auto flex w-full max-w-[1440px] flex-1 flex-col gap-12 px-4 py-10 lg:px-8">
        <header className="flex max-w-3xl flex-col gap-3">
          <h1 className="text-3xl font-medium">The evidence</h1>
          <p className="text-muted-foreground">
            Caliper on Stanford&apos;s QuantiPhy validation set (158 questions, 24 videos), scored
            with the official evaluator. MRA is QuantiPhy&apos;s mean relative accuracy on a 0 to
            100 scale. Everything on this page is generated from{" "}
            <a className="underline underline-offset-4" href="/results/results.csv">
              results.csv
            </a>{" "}
            and{" "}
            <a className="underline underline-offset-4" href="/results/paired_results.csv">
              paired_results.csv
            </a>
            , including the parts that do not flatter us.
          </p>
        </header>

        <section aria-labelledby="findings-h" className="flex flex-col gap-4">
          <h2 id="findings-h" className="text-xl font-medium">
            What the numbers say
          </h2>
          <FindingList items={findings(bench)} />
        </section>

        <SplitCharts rows={bench.results} splits={splits} initial={initial} />

        <section aria-labelledby="paired-h" className="flex flex-col gap-4">
          <div className="flex max-w-3xl flex-col gap-1">
            <h2 id="paired-h" className="text-xl font-medium">
              Like for like
            </h2>
            <p className="text-sm text-muted-foreground">
              Abstentions make the official score unfair in both directions, so each Caliper variant
              is also compared with Muse Spark alone on exactly the questions that variant answered
              (pre-registered in EVAL_PROTOCOL section 4a). Caliper&apos;s abstentions are never
              filled with a model answer.
            </p>
          </div>
          <PairedChart rows={bench.paired} />
        </section>

        <section aria-labelledby="table-h" className="flex flex-col gap-4">
          <h2 id="table-h" className="text-xl font-medium">
            Every row
          </h2>
          <div className="min-w-0 rounded-lg border bg-card">
            <Table className="font-mono text-xs tabular-nums">
              <TableCaption className="px-4 pb-4 text-left font-sans">
                Source: eval/results.csv. Official columns count an abstention as a miss;
                &ldquo;answered&rdquo; columns score answered questions only. Blank means the
                variant has no question in that category on that split.
              </TableCaption>
              <TableHeader>
                <TableRow>
                  {["Variant", "Split", "MRA", "S2", "D2", "S3", "D3", "Coverage", "MRA answered",
                    "Within 10%", "Off 2x", "Within 10% answered", "Off 2x answered", "n", "Cost",
                    "Run date", "Source"].map((h) => (
                    <TableHead key={h} className="font-sans">{h}</TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {bench.results.map((r) => (
                  <TableRow key={`${r.variant}-${r.split}`}>
                    <TableCell className="font-sans">{variantLabel(r.variant)}</TableCell>
                    <TableCell className="font-sans">{splitLabel(r.split)}</TableCell>
                    <TableCell>{fmtMra(r.mra_average)}</TableCell>
                    <TableCell>{fmtMra(r.mra_S2)}</TableCell>
                    <TableCell>{fmtMra(r.mra_D2)}</TableCell>
                    <TableCell>{fmtMra(r.mra_S3)}</TableCell>
                    <TableCell>{fmtMra(r.mra_D3)}</TableCell>
                    <TableCell>{fmtPct(r.coverage)}</TableCell>
                    <TableCell>{fmtMra(r.mra_answered)}</TableCell>
                    <TableCell>{fmtPct(r.share_within_10pct)}</TableCell>
                    <TableCell>{fmtPct(r.share_off_2x)}</TableCell>
                    <TableCell>{fmtPct(r.share_within_10pct_answered)}</TableCell>
                    <TableCell>{fmtPct(r.share_off_2x_answered)}</TableCell>
                    <TableCell>{r.n ?? "n/a"}</TableCell>
                    <TableCell>{r.cost_usd == null ? "n/a" : `$${r.cost_usd.toFixed(2)}`}</TableCell>
                    <TableCell>{r.run_date}</TableCell>
                    <TableCell className="min-w-72 whitespace-normal font-sans text-muted-foreground">
                      {r.source}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          <div className="min-w-0 rounded-lg border bg-card">
            <Table className="font-mono text-xs tabular-nums">
              <TableCaption className="px-4 pb-4 text-left font-sans">
                Source: eval/paired_results.csv. Muse Spark alone scored on exactly the questions
                each Caliper variant answered.
              </TableCaption>
              <TableHeader>
                <TableRow>
                  {["Variant", "Split", "Category", "Answered", "MRA variant", "MRA Muse alone",
                    "Within 10% variant", "Within 10% Muse alone", "Off 2x variant",
                    "Off 2x Muse alone"].map((h) => (
                    <TableHead key={h} className="font-sans">{h}</TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {bench.paired.map((r) => (
                  <TableRow key={`${r.variant}-${r.split}-${r.category}`}>
                    <TableCell className="font-sans">{variantLabel(r.variant)}</TableCell>
                    <TableCell className="font-sans">{splitLabel(r.split)}</TableCell>
                    <TableCell>{r.category}</TableCell>
                    <TableCell>{r.n_answered}</TableCell>
                    <TableCell>{fmtMra(r.mra_variant)}</TableCell>
                    <TableCell>{fmtMra(r.mra_muse)}</TableCell>
                    <TableCell>{fmtPct(r.within10_variant)}</TableCell>
                    <TableCell>{fmtPct(r.within10_muse)}</TableCell>
                    <TableCell>{fmtPct(r.off2x_variant)}</TableCell>
                    <TableCell>{fmtPct(r.off2x_muse)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          <dl className="grid max-w-4xl grid-cols-1 gap-x-6 gap-y-2 text-sm sm:grid-cols-[max-content_1fr]">
            {variants.map((v) => (
              <div key={v} className="contents">
                <dt className="font-medium">{variantLabel(v)}</dt>
                <dd className="text-muted-foreground">{VARIANT_NOTE[v] ?? ""}</dd>
              </div>
            ))}
          </dl>
        </section>

        <section aria-labelledby="field-h" className="flex flex-col gap-4">
          <div className="flex max-w-3xl flex-col gap-1">
            <h2 id="field-h" className="text-xl font-medium">
              Our own clips and the street study
            </h2>
            <p className="text-sm text-muted-foreground">
              These charts read eval/field_results.csv, which does not exist yet: the field clips
              are recorded with an instrument (GPS, tape, timing) and are scored in Phase 4.
            </p>
          </div>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <Placeholder title="Field set: relative error per clip">
              One dot per clip with a 10% target line (claim H2). No field clip has been scored.
            </Placeholder>
            <Placeholder title="Street study: speed error against GPS">
              Set A cars through the study code path (claim H5). Not run yet.
            </Placeholder>
            <Placeholder title="Interval coverage">
              Share of field clips whose 90% range contains the truth, target 80% (claim H3).
            </Placeholder>
            <Placeholder title="Audit catches and false vetoes">
              Wrong-object tracks the audit caught and correct results it wrongly vetoed (claim
              A2), counted on the field set.
            </Placeholder>
          </div>
        </section>

        <section aria-labelledby="method-h" className="flex max-w-3xl flex-col gap-3 text-sm">
          <h2 id="method-h" className="text-xl font-medium">
            Method and downloads
          </h2>
          <p className="text-muted-foreground">
            QuantiPhy videos are split by video into dev and holdout before any tuning; thresholds
            and prompts are tuned on dev only, and holdout is reported separately. Muse Spark alone
            uses QuantiPhy&apos;s official zero-shot prompt. An abstention leaves the answer blank,
            which the official evaluator scores as a miss. Full protocol in{" "}
            <a className="underline underline-offset-4" href={`${REPO}/docs/EVAL_PROTOCOL.md`}>
              EVAL_PROTOCOL.md
            </a>
            .
          </p>
          <ul className="flex flex-wrap gap-x-6 gap-y-2">
            <li>
              <a className="underline underline-offset-4" href="/results/results.csv" download>
                results.csv
              </a>
            </li>
            <li>
              <a className="underline underline-offset-4" href="/results/paired_results.csv" download>
                paired_results.csv
              </a>
            </li>
            <li className="text-muted-foreground">field_results.csv (after Phase 4)</li>
          </ul>
          <p className="text-xs text-muted-foreground">
            QuantiPhy (Stanford) annotations are CC BY 4.0. The benchmark videos keep
            their own licenses and are never shown on this site.
          </p>
        </section>
      </main>
    </>
  );
}
