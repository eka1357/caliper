# Caliper commands. Scripts referenced here are created during the build phases (see PROMPTS.md).
# Targets marked $ spend API credits; run them only when you mean to.

PY := backend/.venv/bin/python

.PHONY: setup dev-api dev-web test lint baseline eval field ablation report

setup:
	cd backend && python -m venv .venv && .venv/bin/pip install -e ".[dev]"
	cd web && npm install

dev-api:
	cd backend && .venv/bin/uvicorn caliper.api:app --reload --port 8000

dev-web:
	cd web && npm run dev

test:
	cd backend && .venv/bin/python -m pytest -q
	cd web && npx tsc --noEmit

lint:
	cd backend && .venv/bin/ruff check . && .venv/bin/ruff format --check .
	cd web && npm run lint

# $ Muse Spark alone on QuantiPhy validation (Phase 0)
baseline:
	$(PY) eval/baseline.py

# $ Caliper on QuantiPhy validation: dev, holdout, full
eval:
	$(PY) eval/quantiphy.py --splits dev holdout full

# $ Caliper on our field clips
field:
	$(PY) eval/field.py

# $ Rule-parser ablation on QuantiPhy validation
ablation:
	$(PY) eval/ablation.py --splits dev holdout full

# Free: rebuild results.csv, web/public/results.json and the README table from saved outputs
report:
	$(PY) eval/report.py
