# Deploy

Web on Vercel, API on Modal (ARCHITECTURE section 12). Config: `web/vercel.json`, `deploy/modal_app.py`.
The cached example runs in `web/public/runs/` work on Vercel with no backend at all; the API adds
live runs, which stay inside the caps from `.env` (AGENTS rule 14).

## What the host gets

| Setting | Where it comes from |
| --- | --- |
| `LIVE_RUNS_ENABLED` | forced to `true` in `deploy/modal_app.py` |
| `MODEL_API_KEY`, model names, `AUDIT_ENABLED`, every cap (`LIVE_*`, `PER_*`, `DAILY_SPEND_CAP_USD`) | Modal secret `caliper-env`, made from those lines of your `.env` (step 2) |
| `WEB_ORIGINS` (CORS) | `CALIPER_WEB_ORIGINS` in your shell when you run `modal deploy` |
| `CACHE_DIR` (API cache and the daily spend ledger) | Modal Volume `caliper-cache`, committed after every POST |
| `NEXT_PUBLIC_API_URL` | Vercel project environment variable (step 5) |

The API runs in at most one container: the per-IP limit and the in-flight cost reservation live in
memory, so a second container would double the caps.

## Steps that need your login (PowerShell, from the repo root)

1. Modal login (opens a browser): `backend\.venv\Scripts\modal.exe token new`
   (install first if needed: `backend\.venv\Scripts\python.exe -m pip install "modal>=1.6,<2"`).
2. Create the secret from only the needed lines of `.env` (the filtered file is gitignored by `.env.*`; delete it after):
   ```powershell
   Select-String -Path .env -Pattern '^(MODEL_API_KEY|META_API_BASE_URL|MUSE_MODEL|SAM_MODEL|AUDIT_ENABLED|LIVE_|PER_RUN|PER_STUDY|DAILY_SPEND)' | ForEach-Object { $_.Line } | Set-Content .env.host; if ($?) { backend\.venv\Scripts\modal.exe secret create caliper-env --from-dotenv .env.host --force }; Remove-Item .env.host
   ```
3. First deploy, with a placeholder origin (the Vercel URL is not known yet):
   `$env:CALIPER_WEB_ORIGINS = "http://localhost:3000"; backend\.venv\Scripts\modal.exe deploy deploy/modal_app.py`
   Note the printed URL (`https://<workspace>--caliper-api-api.modal.run`) and check
   `<url>/api/health` shows `"live_runs_enabled": true` and the caps.
4. Vercel login: `npx vercel login` (from `web\`), or import the GitHub repo at vercel.com/new.
5. Vercel project: Root Directory `web`; keep "Include files outside the root directory" on (the
   CSV download routes read `../eval` at build time); add the environment variable
   `NEXT_PUBLIC_API_URL` = the Modal URL from step 3 (Production and Preview). Deploy:
   `npx vercel --prod` from `web\`, or push to main.
6. Redeploy the API with the real origin:
   `$env:CALIPER_WEB_ORIGINS = "https://<your-app>.vercel.app"; backend\.venv\Scripts\modal.exe deploy deploy/modal_app.py`
7. From a private window: a cached run on `/workspace`, one live measure, the cap message after the
   per-IP limit, and `/results`.

To pause live runs for good after judging: `backend\.venv\Scripts\modal.exe app stop caliper-api`
(the Vercel site keeps working on cached runs).

## Status (2026-11-04)

- Web: https://caliper-sigma.vercel.app (Vercel project `caliper`, root directory `web`, `.vercelignore` uploads only `web/` and the three eval CSVs; the repo is connected, so a push to main redeploys).
- API: https://ekavardhan1234--caliper-api-api.us-east.modal.run (health, recorded runs and CORS for the site checked).
- **Open:** live measure requests are cancelled by Modal at about 145 s (`Received a cancellation signal`), and a cold live measure (spec, SAM, audit) takes longer on the host. Fix: run the measurement as a background job (POST returns a job id, the UI polls), or cut the work per request. Until then the site works on recorded runs only.
