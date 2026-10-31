import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { Workspace } from "@/components/workspace/Workspace";

export const metadata: Metadata = { title: "Workspace · Caliper" };

// No GSAP, no Lenis, no decorative components on this route (AGENTS.md section 9).
export default function WorkspacePage() {
  return (
    <>
      <header className="border-b">
        <div className="mx-auto flex h-14 w-full max-w-[1440px] items-center px-4 lg:px-8">
          <Link href="/" className="font-medium">
            Caliper
          </Link>
        </div>
      </header>
      <main className="flex-1">
        <h1 className="sr-only">Measure a clip</h1>
        <Suspense fallback={<Skeleton className="mx-auto mt-6 aspect-video w-full max-w-[1440px]" />}>
          <Workspace />
        </Suspense>
      </main>
    </>
  );
}
