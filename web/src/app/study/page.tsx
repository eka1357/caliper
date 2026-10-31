import type { Metadata } from "next";
import { Suspense } from "react";
import { SiteHeader } from "@/components/site/SiteHeader";
import { StudyView } from "@/components/study/StudyView";
import { Skeleton } from "@/components/ui/skeleton";

export const metadata: Metadata = { title: "Speed study · Caliper" };

// No GSAP, no Lenis, no decorative components on this route (AGENTS.md section 9).
export default function StudyPage() {
  return (
    <>
      <SiteHeader current="/study" />
      <main className="flex-1">
        <Suspense fallback={<Skeleton className="mx-auto mt-6 aspect-video w-full max-w-[1440px]" />}>
          <StudyView />
        </Suspense>
      </main>
    </>
  );
}
