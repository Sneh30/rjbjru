# WindLens — one-command developer workflows.
PY := backend/.venv/bin/python
PIP := backend/.venv/bin/pip
UVICORN := backend/.venv/bin/uvicorn

.PHONY: help setup ingest verify-snapshot build-snapshot lint typecheck test test-backend test-frontend \
        build build-frontend types insights dev up down smoke verify-snapshot-hash clean check \
        numbers video-timing screenshots

help: ## List available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "%-22s %s\n",$$1,$$2}'

setup: ## Create the backend venv and install frontend dependencies
	python3 -m venv backend/.venv
	$(PIP) install --upgrade pip
	$(PIP) install -r backend/requirements-dev.txt
	cd frontend && npm ci

ingest: ## Fetch Elexon data and rebuild the committed snapshot
	cd backend && .venv/bin/python -m app.ingestion.cli run

build-snapshot: ## Rebuild the snapshot from cached raw responses (no network)
	cd backend && .venv/bin/python -m app.ingestion.cli build

verify-snapshot: ## Re-hash processed data against the manifest
	cd backend && .venv/bin/python -m app.ingestion.cli verify

lint: ## Ruff and ESLint
	cd backend && .venv/bin/ruff check . && .venv/bin/ruff format --check .
	cd frontend && npm run lint

typecheck: ## mypy (strict) and TypeScript
	cd backend && .venv/bin/mypy --strict app/domain app/services app/data app/api
	cd frontend && npm run typecheck

test: test-backend test-frontend ## Run all tests

test-backend: ## Backend tests with coverage
	cd backend && .venv/bin/pytest

test-frontend: ## Frontend tests with coverage
	cd frontend && npm run test -- --run --coverage

build: ## Production frontend build
	cd frontend && npm run build

types: ## Regenerate frontend API types from OpenAPI
	bash scripts/gen_types.sh

insights: ## Regenerate docs/INSIGHTS.md and docs/insights.json
	$(PY) analysis/insights.py

numbers: ## Verify every README/video/form number traces to INSIGHTS.md
	bash scripts/check_numbers_consistency.sh

video-timing: ## Estimate spoken video length from the script word count
	python3 scripts/check_video_timing.py

screenshots: ## Capture docs/img from a running Docker stack on :8080
	node scripts/capture_screenshots.mjs

dev: ## Run API on :8000 and Vite on :5173
	cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000 & cd frontend && npm run dev

up: ## docker compose up --build
	docker compose up --build

down: ## Stop and remove containers
	docker compose down -v

smoke: ## Smoke-test the local Docker stack
	bash scripts/smoke_docker.sh

check: lint typecheck test ## Lint, type-check and test

clean: ## Remove local caches and build output
	rm -rf backend/.pytest_cache backend/.mypy_cache backend/.ruff_cache backend/htmlcov \
		backend/.coverage frontend/dist frontend/coverage frontend/node_modules/.vite
