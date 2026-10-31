import type { Metadata } from "next";
import { Suspense } from "react";
import { StudyReport } from "@/components/study/StudyReport";
import { Skeleton } from "@/components/ui/skeleton";

export const metadata: Metadata = { title: "Speed survey report · Caliper" };

export default function StudyReportPage() {
  return (
    <main className="flex-1">
      <Suspense fallback={<Skeleton className="mx-auto mt-10 h-96 w-full max-w-[800px]" />}>
        <StudyReport />
      </Suspense>
    </main>
  );
}
