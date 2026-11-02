// The one place a cached run's asset URL is built. The id is the manifest run_id, which is the
// folder name under web/public/runs (runs.save_cached_run writes result.run_id equal to it).
// Production servers and Vercel match public files case-sensitively, so never build these from
// any other string. backend/tests/test_runs.py checks every manifest entry at exact case.

export function runAssetUrl(runId: string, file: string | null | undefined): string | null {
  return file ? `/runs/${encodeURIComponent(runId)}/${file}` : null;
}
