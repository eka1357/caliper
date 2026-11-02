import { buildTimeOnly, readEvalFile } from "@/lib/results";

// Serves eval/field_results.csv as it is in the repo (prerendered at build time).
async function load() {
  "use cache";
  buildTimeOnly();
  return readEvalFile("field_results.csv");
}

export async function GET() {
  return new Response(await load(), {
    headers: { "content-type": "text/csv; charset=utf-8" },
  });
}
