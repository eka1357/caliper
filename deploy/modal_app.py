"""Hosted Caliper API on Modal (ARCHITECTURE section 12: "Backend: Modal web endpoint ... with
ffmpeg installed"). Web is on Vercel; it calls this API at NEXT_PUBLIC_API_URL.

Deploy from the repo root (steps that need your login are in docs/DEPLOY.md):

    $env:CALIPER_WEB_ORIGINS = "https://<your-app>.vercel.app"
    modal deploy deploy/modal_app.py

What runs: caliper.api (FastAPI) with
- LIVE_RUNS_ENABLED forced to true on the host (AGENTS rule 14), every other cap read from the
  Modal secret `caliper-env`, which is made from the cap lines of your .env (docs/DEPLOY.md);
- the API cache and the daily spend ledger on a Modal Volume, so a restart neither re-spends
  nor resets the daily cap; the volume is committed after every POST;
- one container at most: the per-IP rate limit and the in-flight cost reservation live in
  memory (caliper/caps.py), so a second container would double the caps.
"""

from __future__ import annotations

import os
from pathlib import Path

import modal

REPO = Path(__file__).resolve().parents[1]
REMOTE = "/root/caliper"  # config.ROOT in the container (backend/caliper/config.py parents[2])
CACHE = f"{REMOTE}/data/cache"
WEB_ORIGINS = os.environ.get("CALIPER_WEB_ORIGINS", "http://localhost:3000")  # read at deploy

image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("ffmpeg")
    .pip_install_from_pyproject(str(REPO / "backend" / "pyproject.toml"))
    .env({"PYTHONPATH": f"{REMOTE}/backend", "CALIPER_WEB_ORIGINS": WEB_ORIGINS})
    .add_local_dir(
        REPO / "backend" / "caliper",
        f"{REMOTE}/backend/caliper",
        ignore=["__pycache__", "**/*.pyc"],
    )  # fmt: skip
    # /api/runs serves the recorded demo runs; /api/results reads these two CSVs.
    .add_local_dir(REPO / "web" / "public" / "runs", f"{REMOTE}/web/public/runs")
    .add_local_file(REPO / "eval" / "results.csv", f"{REMOTE}/eval/results.csv")
    .add_local_file(REPO / "eval" / "field_results.csv", f"{REMOTE}/eval/field_results.csv")
)
volume = modal.Volume.from_name("caliper-cache", create_if_missing=True)
app = modal.App("caliper-api", image=image)


@app.function(
    secrets=[modal.Secret.from_name("caliper-env")],
    volumes={CACHE: volume},
    max_containers=1,
    timeout=600,  # a live study on a 60 s clip can take minutes
    scaledown_window=300,
)
@modal.concurrent(max_inputs=8)
@modal.asgi_app()
def api():
    # Host overrides, set before caliper.config is imported (it reads os.environ once).
    os.environ["LIVE_RUNS_ENABLED"] = "true"
    os.environ["CACHE_DIR"] = CACHE
    os.environ["WEB_ORIGINS"] = os.environ["CALIPER_WEB_ORIGINS"]

    from caliper.api import app as fastapi_app

    @fastapi_app.middleware("http")
    async def commit_volume(request, call_next):
        response = await call_next(request)
        if request.method == "POST":
            volume.commit()  # spend ledger and API cache survive a container restart
        return response

    return fastapi_app
