import { buildTimeOnly, readEvalFile } from "@/lib/results";

// Serves eval/results.csv as it is in the repo (prerendered at build time).
async function load() {
  "use cache";
  buildTimeOnly();
  return readEvalFile("results.csv");
}

export async function GET() {
  return new Response(await load(), {
    headers: { "content-type": "text/csv; charset=utf-8" },
  });
}
