import Link from "next/link";

// Landing page is Phase 5b (docs/DESIGN.md section 6); this stub only routes to the tool.
export default function Home() {
  return (
    <main className="mx-auto flex w-full max-w-[1200px] flex-1 flex-col justify-center gap-6 px-6 py-24">
      <h1 className="font-display text-5xl">AI guesses. Caliper measures.</h1>
      <Link
        href="/workspace"
        className="w-fit rounded-md bg-primary px-4 py-2 font-medium text-primary-foreground"
      >
        Measure a clip
      </Link>
    </main>
  );
}
