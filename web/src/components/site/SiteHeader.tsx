import Link from "next/link";
import { cn } from "@/lib/utils";

const LINKS = [
  { href: "/workspace", label: "Workspace" },
  { href: "/study", label: "Speed study" },
  { href: "/results", label: "Evidence" },
] as const;

/** Shared top bar for the tool routes. No animation library here (AGENTS.md section 9). */
export function SiteHeader({ current, wide = true }: { current?: string; wide?: boolean }) {
  return (
    <header className="border-b print:hidden">
      <div
        className={cn(
          "mx-auto flex h-14 w-full items-center justify-between gap-4 px-4 lg:px-8",
          wide ? "max-w-[1440px]" : "max-w-[1200px]",
        )}
      >
        <Link href="/" className="font-medium">
          Caliper
        </Link>
        <nav aria-label="Main">
          <ul className="flex items-center gap-1 text-sm">
            {LINKS.map((l) => (
              <li key={l.href}>
                <Link
                  href={l.href}
                  aria-current={current === l.href ? "page" : undefined}
                  className={cn(
                    "rounded-md px-2 py-1.5 text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring sm:px-3",
                    current === l.href && "text-foreground",
                  )}
                >
                  {l.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      </div>
    </header>
  );
}
