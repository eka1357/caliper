"use client";

import dynamic from "next/dynamic";

// Chart code (bklit + Motion) is split out of the landing's first load; the charts sit below
// the fold and mount inside LazyInView, so this code is fetched only when they are near.
export const LazyPairedChart = dynamic(
  () => import("@/components/results/BenchmarkCharts").then((m) => m.PairedChart),
  { ssr: false },
);

export const LazySizeChart = dynamic(
  () => import("@/components/workspace/FitChart").then((m) => m.SizeChart),
  { ssr: false },
);

export const LazyPositionChart = dynamic(
  () => import("@/components/workspace/FitChart").then((m) => m.PositionChart),
  { ssr: false },
);
