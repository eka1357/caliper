import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { fmtPct, variantLabel } from "@/lib/labels";
import { type Benchmark, calibration, FIELD_SETS, fieldRows } from "@/lib/results";

// Field set on /results. Every value is read from web/public/results.json (eval/report.py over
// eval/field_results.csv, field_guesses.csv and interval_calibration.csv). Server component.

const n2 = (v: number | null, d = 2) => (v == null ? "n/a" : v.toFixed(d));

function Head({ cols }: { cols: string[] }) {
  return (
    <TableHeader>
      <TableRow>
        {cols.map((h) => (
          <TableHead key={h} className="font-sans">{h}</TableHead>
        ))}
      </TableRow>
    </TableHeader>
  );
}

export function FieldResults({ bench }: { bench: Benchmark }) {
  const sizeRows = fieldRows(bench, "size");
  const unit = sizeRows[0]?.unit ?? "";
  const variants = ["caliper_no_audit", "caliper"];
  const k = calibration(bench, "caliper_no_audit", false)?.interval_log_term ?? null;

  return (
    <div className="flex flex-col gap-8">
      {/* Per-set summary */}
      <div className="min-w-0 rounded-lg border bg-card">
        <Table className="font-mono text-xs tabular-nums">
          <TableCaption className="px-4 pb-4 text-left font-sans">
            Source: eval/field_results.csv and eval/field_guesses.csv. Our own clips, each with an
            instrument reading. Median error counts measured clips only; Muse Spark alone was given
            the same question and the same known size.
          </TableCaption>
          <Head cols={["Set", "What it tests", "Clips", "Measured", "Refused", "Median error",
            "Truth inside 90% range", "Muse Spark alone median error"]} />
          <TableBody>
            {FIELD_SETS.map(({ set, label, what }) => {
              const s = bench.field_summary[set];
              if (!s) return null;
              return (
                <TableRow key={set}>
                  <TableCell className="font-sans">{label}</TableCell>
                  <TableCell className="min-w-48 whitespace-normal font-sans">{what}</TableCell>
                  <TableCell>{s.n}</TableCell>
                  <TableCell>{s.measured}</TableCell>
                  <TableCell>{s.abstained}</TableCell>
                  <TableCell>{fmtPct(s.median_rel_error)}</TableCell>
                  <TableCell>
                    {s.coverage == null ? "n/a" : `${Math.round(s.coverage * s.measured)} of ${s.measured}`}
                  </TableCell>
                  <TableCell>
                    {set === "none" ? `answered ${s.guess_answered} of ${s.guess_n}` : fmtPct(s.guess_median_rel_error)}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>

      {/* Set C with intervals */}
      <div className="flex flex-col gap-2">
        <h3 className="font-medium">Set C: size against a tape measure</h3>
        <div className="min-w-0 rounded-lg border bg-card">
          <Table className="font-mono text-xs tabular-nums">
            <TableCaption className="px-4 pb-4 text-left font-sans">
              Source: eval/field_results.csv. Values in {unit}. The 90% range includes the error term
              calibrated on the QuantiPhy dev split; the field set was never used to set it.
            </TableCaption>
            <Head cols={["Clip", "Caliper", "90% range", "Tape", "Error", "Inside range",
              "Muse Spark alone", "Its error"]} />
            <TableBody>
              {sizeRows.map((r) => (
                <TableRow key={r.clip_id}>
                  <TableCell className="font-sans">{r.clip_id}</TableCell>
                  <TableCell>{n2(r.pred)}</TableCell>
                  <TableCell>{r.lo == null ? "n/a" : `${n2(r.lo)} to ${n2(r.hi)}`}</TableCell>
                  <TableCell>{n2(r.truth, 1)}</TableCell>
                  <TableCell>{fmtPct(r.rel_error)}</TableCell>
                  <TableCell className="font-sans">
                    {r.covered == null ? "n/a" : r.covered ? "yes" : <span className="text-destructive">no</span>}
                  </TableCell>
                  <TableCell>{n2(r.guess_pred, 1)}</TableCell>
                  <TableCell>{fmtPct(r.guess_rel_error)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </div>

      {/* Refusals per set, verbatim */}
      <div className="flex flex-col gap-2">
        <h3 className="font-medium">Every refusal, in Caliper&apos;s words</h3>
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {FIELD_SETS.map(({ set, label, what }) => {
            const rows = fieldRows(bench, set);
            const refused = rows.filter((r) => r.status === "abstained");
            const measured = rows.filter((r) => r.status === "measured");
            return (
              <div key={set} className="min-w-0 rounded-lg border bg-card">
                <Table className="text-xs">
                  <TableCaption className="px-4 pb-4 text-left">
                    {label}, {what}: {refused.length} of {rows.length} refused.
                    {measured.length > 0 && ` Measured: ${measured.map((r) => `${r.clip_id} ${n2(r.pred)} ${r.unit} (truth ${r.truth == null ? "none" : n2(r.truth, set === "size" ? 1 : 2)})`).join(", ")}.`}
                  </TableCaption>
                  {refused.length > 0 && (
                    <Head cols={set === "speed" ? ["Clip", "GPS", "Muse alone", "Its error", "Caliper"] : ["Clip", "Caliper"]} />
                  )}
                  <TableBody>
                    {refused.map((r) => (
                      <TableRow key={r.clip_id}>
                        <TableCell className="font-mono">{r.clip_id}</TableCell>
                        {set === "speed" && (
                          <>
                            <TableCell className="font-mono tabular-nums">{n2(r.truth)}</TableCell>
                            <TableCell className="font-mono tabular-nums">{n2(r.guess_pred, 1)}</TableCell>
                            <TableCell className="font-mono tabular-nums">{fmtPct(r.guess_rel_error)}</TableCell>
                          </>
                        )}
                        <TableCell className="min-w-56 whitespace-normal">{r.reason}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            );
          })}
        </div>
        <p className="max-w-3xl text-sm text-muted-foreground">
          Set A speeds are in m/s. The street study&apos;s gate method is not validated by this Set A:
          its markers stand on the far kerb while the car drives in the near lane, so the distance
          between them is not the car&apos;s path. Set A was therefore measured with the car as its
          own ruler, using only frames where the whole car is in the picture.
        </p>
      </div>

      {/* Interval fix on dev */}
      <div className="flex flex-col gap-2">
        <h3 className="font-medium">The interval fix, checked on QuantiPhy dev</h3>
        <p className="max-w-3xl text-sm text-muted-foreground">
          The first field run showed 90% ranges that covered almost no truths: they held only the
          tracking noise. An error term {k == null ? "" : `of ${k} (log scale) `}was added, set on
          the QuantiPhy dev split so that 90% of answered dev questions fall inside. Ranges that
          become wider than half the value are refused by the existing width check.
        </p>
        <div className="min-w-0 rounded-lg border bg-card">
          <Table className="font-mono text-xs tabular-nums">
            <TableCaption className="px-4 pb-4 text-left font-sans">
              Source: eval/interval_calibration.csv (eval/calibrate_interval.py over the dev runs
              before and after). After the term, the share inside is measured on the answers that
              remain, so it is an in-sample check; Set C above is the out-of-sample one.
            </TableCaption>
            <Head cols={["Variant", "Answered before", "Truth inside before", "Answered after",
              "Truth inside after", "Newly refused by the width check"]} />
            <TableBody>
              {variants.map((v) => {
                const b = calibration(bench, v, true);
                const a = calibration(bench, v, false);
                if (!b || !a) return null;
                return (
                  <TableRow key={v}>
                    <TableCell className="font-sans">{variantLabel(v)}</TableCell>
                    <TableCell>{b.answered}</TableCell>
                    <TableCell>{`${b.covered} (${fmtPct(b.coverage)})`}</TableCell>
                    <TableCell>{a.answered}</TableCell>
                    <TableCell>{`${a.covered} (${fmtPct(a.coverage)})`}</TableCell>
                    <TableCell>{a.newly_refused_interval_width}</TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      </div>
    </div>
  );
}
