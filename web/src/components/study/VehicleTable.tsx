import type { VehicleReading } from "@/lib/types";
import { fmtKmh, fmtRange } from "./copy";

/** Per-vehicle readings. No plates or faces: only class, times and speed. */
export function VehicleTable({ readings }: { readings: VehicleReading[] }) {
  return (
    <div className="w-full min-w-0 overflow-x-auto rounded-lg border">
      <table className="w-full text-sm">
        <caption className="sr-only">Per-vehicle readings</caption>
        <thead className="border-b text-left text-muted-foreground">
          <tr>
            <th className="px-3 py-2 font-normal">Vehicle</th>
            <th className="px-3 py-2 font-normal">Class</th>
            <th className="px-3 py-2 font-normal">Speed (km/h)</th>
            <th className="px-3 py-2 font-normal">90% range</th>
            <th className="px-3 py-2 font-normal">Gate A to B (s)</th>
            <th className="px-3 py-2 font-normal">Note</th>
          </tr>
        </thead>
        <tbody className="font-mono tabular-nums">
          {readings.map((r) => (
            <tr key={r.vehicle_id} className="border-b last:border-0">
              <td className="px-3 py-2">{r.vehicle_id}</td>
              <td className="px-3 py-2 font-sans">{r.vehicle_class}</td>
              <td className="px-3 py-2">{r.status === "measured" ? fmtKmh(r.speed_kmh) : "no reading"}</td>
              <td className="px-3 py-2">{r.status === "measured" ? fmtRange(r.interval_90_kmh) : ""}</td>
              <td className="px-3 py-2">
                {r.t_gate_a_s != null && r.t_gate_b_s != null
                  ? `${r.t_gate_a_s.toFixed(2)} to ${r.t_gate_b_s.toFixed(2)}`
                  : ""}
              </td>
              <td className="px-3 py-2 font-sans text-muted-foreground">{r.reason ?? ""}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
