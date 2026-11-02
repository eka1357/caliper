# Caliper commands. Scripts referenced here are created during the build phases (see PROMPTS.md).
# Targets marked $ spend API credits; run them only when you mean to.

PY := backend/.venv/bin/python

.PHONY: setup dev-api dev-web test lint baseline eval field ablation study report

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
	cd web && node --test tests/*.test.mjs

lint:
	cd backend && .venv/bin/ruff check . && .venv/bin/ruff format --check .
	cd web && npm run lint

# $ Muse Spark alone on QuantiPhy validation (Phase 0)
baseline:
	$(PY) eval/baseline.py

# $ Caliper on QuantiPhy validation, frozen code (DECISIONS "Freeze"): specs, both variants, then
# score dev, holdout and full. Each step stops before passing its cap; cached calls cost $0.
eval:
	$(PY) eval/quantiphy.py --split full --specs-only --max-spend 4.00
	$(PY) eval/quantiphy.py --split full --variant caliper --max-spend 6.00
	$(PY) eval/quantiphy.py --split full --variant caliper_no_audit --max-spend 0.50
	$(PY) eval/holdout_finalize.py

# $ Caliper on our field clips
field:
	$(PY) eval/field.py

# $ Rule-parser and audit-off ablations on QuantiPhy validation
ablation:
	$(PY) eval/ablation.py --splits dev holdout full

# $ Street speed study on one clip, e.g. make study CLIP=data/field/S01.mp4 GATE_M=10.0
study:
	$(PY) -m caliper.study --clip $(CLIP) --gate-m $(GATE_M)

# Free: rebuild results.csv, web/public/results.json and the README table from saved outputs
report:
	$(PY) eval/report.py
