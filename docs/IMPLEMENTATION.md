# IMPLEMENTATION.md — Build Plan, Procedures and Code Skeletons

**Implements:** `SAS.md`. **Satisfies:** `PRD.md`. Follow `MASTER_PROMPT.md` rules.
**Total budget:** 16 h of effort (plan below sums to 16.0 h). P0 first, then P1, then P2 only if time remains.

| Phase | Title | Hours | Output |
|------:|-------|------:|--------|
| 0 | Bootstrap & anonymity | 0.5 | Repo skeleton, tooling, CI stub |
| 1 | Data-source verification | 0.5 | `docs/DATA_SOURCES.md` |
| 2 | Ingestion pipeline & snapshot | 2.0 | `data/processed/*`, quality report |
| 3 | Domain logic + tests | 2.5 | `app/domain/*`, ≥ 90% coverage |
| 4 | API & services | 1.5 | `/api/v1/*`, OpenAPI, contract tests |
| 5 | Frontend | 4.0 | Desk, Lab, Revisions, About |
| 6 | Analysis & insights | 0.75 | `analysis/insights.py`, `docs/INSIGHTS.md` |
| 7 | Docker, Vercel, CI | 1.5 | Compose, `vercel.json`, workflow |
| 8 | Docs, README, video & submission kits | 1.25 | README, scripts, `HUMAN_ACTIONS.md` |
| 9 | Final audit | 0.5 | Evidence log, fixes |
| — | Buffer | 0.5 | |

> Phase 6 may overlap with 3–5 (insights are needed for UI copy and the video).

---

## Phase 0 — Bootstrap & anonymity (0.5 h)

**Goal:** a clean, anonymous, reproducible workspace.

0. **Capability preflight** (`MASTER_PROMPT.md §5.0`, `VERIFICATION_GATE.md §1`): probe network reach to the Elexon hosts, GitHub push access, Docker, a headless browser, and audio/video/Vercel auth; write the results to `docs/AGENT_CAPABILITIES.md` before anything else. This decides, fact not assumption, which later steps are yours to finish and which go to `HUMAN_ACTIONS.md`.
1. Generate an anonymous repo name: `scripts/new_repo_name.sh` → prints e.g. `kjhwr`. (`LC_ALL=C tr -dc 'a-z' </dev/urandom | head -c 6`.) Use it as the directory and the GitHub repo name.
2. `git init -b main`; configure **local** identity to a neutral placeholder: `git config user.name "dev"` and `git config user.email "dev@users.noreply.invalid"` (the human may override at push time; document in `HUMAN_ACTIONS.md` that GitHub may attach their account — they should use a noreply email and check "Keep my email private").
3. Create the layout from `SAS.md §4` (empty dirs with `.gitkeep` where needed).
4. Tooling files: `.gitignore`, `.dockerignore`, `.editorconfig`, `.pre-commit-config.yaml` (ruff, ruff-format, prettier, end-of-file-fixer, check-yaml, detect-private-key), `Makefile` (targets in §Makefile below).
5. Backend: `backend/pyproject.toml`, `requirements.txt` (runtime), `requirements-dev.txt`.
6. Frontend: `npm create vite@latest frontend -- --template react-ts`; add deps (below).
7. `scripts/check_anonymity.sh`: greps the working tree and `git log` for the strings in `.anonymity-denylist` (the human's name/handle/email/college/company — **file is gitignored and supplied by the human**; script is a no-op with a warning if absent) and also fails on any `author` fields in `package.json`/`pyproject.toml`, on Docker `LABEL maintainer`, and on non-neutral `git config` identities.
8. First commit: `chore: bootstrap repository skeleton`.

**Acceptance:** `make help` works; `pre-commit run --all-files` passes; `check_anonymity.sh` passes.

### Makefile (normative targets)
```make
.PHONY: help setup ingest verify-snapshot lint typecheck test test-backend test-frontend build run dev up down smoke types insights clean
help:            ## list targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "%-18s %s\n",$$1,$$2}'
setup:           ## install backend & frontend deps
	cd backend && python -m venv .venv && . .venv/bin/activate && pip install -r requirements-dev.txt
	cd frontend && npm ci
ingest:          ## fetch Elexon data and rebuild snapshot
	cd backend && . .venv/bin/activate && python -m app.ingestion.cli run
verify-snapshot: ## re-hash processed data vs manifest
	cd backend && . .venv/bin/activate && python -m app.ingestion.cli verify
lint:            ## ruff + eslint
	cd backend && . .venv/bin/activate && ruff check . && ruff format --check .
	cd frontend && npm run lint
typecheck:       ## mypy + tsc
	cd backend && . .venv/bin/activate && mypy --strict app/domain app/services
	cd frontend && npm run typecheck
test: test-backend test-frontend ## all tests
test-backend:
	cd backend && . .venv/bin/activate && pytest --cov=app --cov-report=term-missing --cov-fail-under=85
test-frontend:
	cd frontend && npm run test -- --run --coverage
types:           ## regenerate TS API types from OpenAPI
	bash scripts/gen_types.sh
insights:        ## regenerate docs/INSIGHTS.md
	cd backend && . .venv/bin/activate && python ../analysis/insights.py
dev:             ## run API (8000) and web (5173)
	(cd backend && . .venv/bin/activate && uvicorn app.main:app --reload --port 8000) & (cd frontend && npm run dev)
up:              ## docker compose up
	docker compose up --build
down:
	docker compose down -v
smoke:           ## smoke-test local docker
	bash scripts/smoke_docker.sh
```

---

## Phase 1 — Data-source verification (0.5 h)

**Goal:** replace assumptions with verified facts. Write `docs/DATA_SOURCES.md`.

1. Fetch `https://data.elexon.co.uk/bmrs/api/v1/swagger/v1/swagger.json` (or the documentation pages in the brief). Locate `/datasets/FUELHH/stream` and `/datasets/WINDFOR/stream`.
2. Record, for each: path, HTTP method, **parameter names and types** (expected: FUELHH — `settlementDateFrom`, `settlementDateTo`, `settlementPeriodFrom/To`, `fuelType[]`; WINDFOR — `publishDateTimeFrom`, `publishDateTimeTo`, optionally `format`), required flags, maximum date range (if documented), response schema (expected fields: `dataset`, `publishTime`, `startTime`, `settlementDate`, `settlementPeriod`, `fuelType`, `generation` for FUELHH; `dataset`, `publishTime`, `startTime`, `generation` for WINDFOR), whether an API key is needed (expected: not required), rate limits, response format (JSON array).
3. Do a tiny live probe (one day each). Record: row counts per day, `startTime` granularity, whether FUELHH returns multiple `publishTime`s per `startTime`, the `fuelType` casing, WINDFOR publish cadence (hourly? every few hours?), the horizon range per publish (e.g., how far ahead), whether `generation` can be negative/null.
4. Save two small raw samples as test fixtures (`backend/tests/fixtures/raw_fuelhh_sample.json`, `raw_windfor_sample.json`).
5. Note any scope definitions printed in the docs (e.g., what WIND covers) for the Methodology text. **Do not assert unverified facts.**
6. If probes are impossible (no network), mark `HUMAN_ACTIONS.md` item "Run `make ingest`" and proceed with fixtures per `ENGINEERING_REFERENCE §6`.

**Acceptance:** `docs/DATA_SOURCES.md` has the verified parameter table and two fixtures committed.

---

## Phase 2 — Ingestion pipeline & snapshot (2.0 h)

**Goal:** deterministic, resumable ingestion producing the committed snapshot. (FR-D1…D7)

### 2.1 `config.py` (excerpt)
```python
from datetime import date, time
from pathlib import Path
from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    data_dir: Path = Path(__file__).resolve().parents[2] / "data"
    timezone: str = "Europe/London"
    default_cutoff: time = time(9, 0)
    cutoff_grid: list[time] = [time(6), time(8), time(9), time(9, 20), time(9, 50), time(10), time(12)]
    scope_mode: Literal["decision_date", "delivery_date"] = "decision_date"
    scope_start: date = date(2026, 1, 1)   # inclusive, interpreted per scope_mode
    scope_end: date = date(2026, 1, 31)    # inclusive
    ingest_forecast_publish_start: str = "2025-12-30T00:00:00Z"
    ingest_forecast_publish_end: str = "2026-02-02T00:00:00Z"
    ingest_actuals_start: str = "2026-01-01T00:00:00Z"
    ingest_actuals_end: str = "2026-02-02T00:00:00Z"
    mape_min_actual_mw: float = 500.0
    min_history_days: int = 7
    outcome_lag_days: int = 2
    horizon_buckets_h: list[float] = [0, 6, 12, 18, 24, 36, 48, 72]
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:8080"]
    elexon_base_url: str = "https://data.elexon.co.uk/bmrs/api/v1"
```
Scope helper: `delivery_days(settings) -> list[date]` returns `scope_start+1 … scope_end+1` when `decision_date`, else `scope_start … scope_end`.

### 2.2 `elexon_client.py`
- `httpx.Client(timeout=httpx.Timeout(30.0, connect=10.0), headers={"Accept": "application/json", "User-Agent": "windlens-ingest/1.0"})`.
- Day-chunk generators for both datasets (parameter names from Phase 1).
- `tenacity` retry: exponential backoff (`wait_exponential(multiplier=1, max=30)`), stop after 6 attempts, retry on 429/5xx/timeouts; honour `Retry-After`.
- If a 400 indicates range too large, automatically halve the chunk (recursion with depth limit).
- Return `(url, params, status, payload_bytes)`; the pipeline writes the raw file and updates the manifest.
- Politeness: sequential requests, `time.sleep(0.2)` between chunks.

### 2.3 `normalise.py`
```python
def normalise_actuals(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    df = df[df["fuelType"].str.upper() == "WIND"]
    df["start_time"] = pd.to_datetime(df["startTime"], utc=True)
    df["publish_time"] = pd.to_datetime(df.get("publishTime"), utc=True, errors="coerce")
    df["generation_mw"] = pd.to_numeric(df["generation"], errors="coerce")
    df = (df.sort_values(["start_time", "publish_time"])
            .drop_duplicates("start_time", keep="last"))      # R11
    return df[["start_time", "generation_mw"]].reset_index(drop=True)

def normalise_forecasts(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    df["start_time"] = pd.to_datetime(df["startTime"], utc=True)
    df["publish_time"] = pd.to_datetime(df["publishTime"], utc=True)
    df["generation_mw"] = pd.to_numeric(df["generation"], errors="coerce")
    df = (df.sort_values(["start_time", "publish_time"])
            .drop_duplicates(["start_time", "publish_time"], keep="last"))
    return df[["start_time", "publish_time", "generation_mw"]].reset_index(drop=True)
```
Count and record dropped duplicates, NaNs, non-WIND rows.

### 2.4 `validate.py` — hard vs soft checks
Hard (raise): empty datasets; non-UTC; non-30-min alignment; actuals not unique; forecast `(start_time, publish_time)` not unique; `generation_mw` NaN share > 1%; negative values; forecasts missing entirely for the ingestion window.
Soft (warn, record): missing actual periods (expected 48 × days); delivery days with < 48 decision-time forecast points at the default cutoff; unusual horizons; WINDFOR publish cadence gaps.
Write `quality_report.json` with counts and lists of missing periods.

### 2.5 `pipeline.py` + `cli.py`
Commands: `run` (fetch→normalise→validate→write), `fetch`, `build` (from existing raw), `verify` (hash check), `report`.
- Write `actuals.csv.gz`/`forecasts.csv.gz` with `index=False`, ISO-8601 `Z` timestamps, sorted, `float_format="%.3f"`.
- Compute `fingerprint = sha256(actuals_sha + forecasts_sha + schema_version)[:16]`.
- Size policy per SAS §12.1; log final sizes.

### 2.6 Tests (`tests/ingestion/`)
- `test_normalise.py`: fixtures with duplicates, other fuel types, bad numerics → expected frames.
- `test_validate.py`: each hard check triggers; soft warnings recorded.
- `test_client_retry.py`: `respx`/`pytest-httpx` simulating 429→200, 500→500→200, timeout, 400-range split.
- `test_pipeline_idempotent.py`: running twice yields identical hashes.

**Acceptance:** `make ingest` populates `data/processed/*`; `quality_report.json` exists; all ingestion tests pass; commit `feat(ingestion): …` and commit the snapshot as `chore(data): add January 2026 snapshot`.

---

## Phase 3 — Domain logic + tests (2.5 h) — **the heart of the project**

Write tests first (TDD) for `timeutils`, `selection`, `metrics`. Domain code must be pure and typed.

### 3.1 `domain/constants.py`
```python
from zoneinfo import ZoneInfo
LONDON = ZoneInfo("Europe/London")
PERIOD_MINUTES = 30
PERIOD_HOURS = 0.5          # MWh = MW * PERIOD_HOURS
# Sign convention: error = forecast - actual. Positive => over-forecast => shortfall risk for the buyer.
```

### 3.2 `domain/timeutils.py`
```python
import pandas as pd
from datetime import date, time
from .constants import LONDON

def london_delivery_date(start_time: pd.Series) -> pd.Series:
    """London-local calendar date (as normalised naive Timestamp) of each UTC start_time."""
    return start_time.dt.tz_convert(LONDON).dt.tz_localize(None).dt.normalize()

def decision_cutoff_utc(start_time: pd.Series, cutoff_local: time) -> pd.Series:
    """Cutoff instant (UTC) = (delivery_date - 1 day) at cutoff_local in Europe/London."""
    d = london_delivery_date(start_time)
    naive = d - pd.Timedelta(days=1) + pd.Timedelta(hours=cutoff_local.hour, minutes=cutoff_local.minute)
    local = naive.dt.tz_localize(LONDON, nonexistent="shift_forward", ambiguous="NaT")
    if local.isna().any():
        raise ValueError("Ambiguous cutoff time at DST boundary")
    return local.dt.tz_convert("UTC")

def london_hour(start_time: pd.Series) -> pd.Series:
    return start_time.dt.tz_convert(LONDON).dt.hour
```
Scalar helper `cutoff_for_delivery_date(date, time) -> datetime` for API metadata.

### 3.3 `domain/selection.py`
```python
def select_decision_forecasts(forecasts: pd.DataFrame, cutoff_local: time) -> pd.DataFrame:
    f = forecasts.assign(cutoff_utc=decision_cutoff_utc(forecasts["start_time"], cutoff_local))
    eligible = f[f["publish_time"] <= f["cutoff_utc"]]           # inclusive boundary
    if eligible.empty:
        return _empty_selected()
    idx = eligible.groupby("start_time", sort=True)["publish_time"].idxmax()
    sel = eligible.loc[idx].copy()
    sel["horizon_h"] = (sel["start_time"] - sel["publish_time"]).dt.total_seconds() / 3600
    sel["delivery_date"] = london_delivery_date(sel["start_time"]).dt.date
    sel = sel.rename(columns={"generation_mw": "forecast_mw"})
    _assert_no_leakage(sel)
    return sel.reset_index(drop=True)
```
`_assert_no_leakage` raises `AssertionError` if any `publish_time > cutoff_utc` or duplicate `start_time`.

### 3.4 `domain/metrics.py` — functions
`compute_metrics(joined: pd.DataFrame, *, mape_min_actual: float) -> Metrics` returning a typed dict with: `n, n_missing_actual, mean_actual, mae, rmse, bias, nmae_pct, wape_pct, mape_pct, mape_n, p50_abs, p90_abs, p95_abs, p5_err, p50_err, p95_err, over_forecast_share, shortfall_mean, shortfall_p90, shortfall_p95, shortfall_max, correlation`. `skill_vs_persistence` computed in `baseline.py` and merged by the service. Return `None` values (not NaN) for undefined metrics and `n=0` for empty input.

### 3.5 `domain/horizon.py`, `breakdowns.py`, `baseline.py`, `risk.py`
Implement per SAS §7.5–7.9 using shared `compute_metrics`. Keep each file < 200 lines. Public functions documented with docstrings including units.

### 3.6 Required unit tests (hand-computed expectations; **write these exactly**)
**Timeutils**
1. Delivery 2026‑01‑15 at 09:00 → cutoff `2026-01-14T09:00:00Z`.
2. A target of `2026-01-15T00:00Z` (first period) and `2026-01-15T23:30Z` (last) share the same cutoff.
3. Summer date (2026‑07‑15): London 09:00 on D−1 = `08:00Z` (DST aware).
4. Spring-forward day (2026‑03‑29): cutoff for delivery 03‑29 is D−1 09:00 GMT (`09:00Z`); cutoff for delivery 03‑30 is D−1 09:00 BST (`08:00Z`).
5. Autumn day (2026‑10‑25): delivery day has 50 half-hours; ensure the vectorised function handles all.
**Selection**
6. Three vintages for one target (08:00, 09:00, 10:00 on D−1): cutoff 09:00 → picks 09:00 (**boundary inclusive**).
7. Cutoff 09:00 and only a 09:00:01 vintage → no selection for that target.
8. Vintage published after delivery start (hindsight) never selected.
9. Different targets within a day share the same cutoff; selected vintages may differ per target (different horizons) — assert.
10. Duplicated `(start_time, publish_time)` rows (should not exist post-normalise): selection still returns one row.
11. Missing vintages for some targets → those targets absent; counts correct.
12. Property test (Hypothesis): for random forecast sets, `selected.publish_time ≤ cutoff` and equals the max eligible; and increasing cutoff never selects an *older* vintage.
**Horizon**
13. `start=2026‑01‑15T12:00Z`, `publish=2026‑01‑14T09:00Z` → 27.0 h.
14. Decision-time horizons for the default cutoff span exactly 15.0–38.5 h on a full 48-period winter day.
**Metrics** (use f = [100, 200, 300, 400], a = [110, 190, 330, 380])
15. e = [−10, 10, −30, 20]; MAE = 17.5; RMSE = sqrt((100+100+900+400)/4) = sqrt(375) ≈ 19.3649; bias = −2.5; over-forecast share = 0.5; shortfall = [0, 10, 0, 20] → mean 7.5, max 20, P90 (linear) = 17.0; P95 = 18.5.
16. Empty and all-NaN inputs → `n=0`, metrics `None`.
17. MAPE excludes actual < threshold and reports `mape_n`.
18. Correlation sign and range.
**Breakdowns/risk/baseline**
19. By-hour grouping uses London local hours; counts sum to n.
20. By-level bins: quantile edges returned; each bin has ≥ 1 row; sums to n.
21. Risk: with errors `[−10, 10, −30, 20]` Q90 (linear) = 17.0 → risk-adjusted forecast = max(0, f − 17).
22. Walk-forward: day *d* uses only days ≤ d − `outcome_lag_days`; insufficient history flagged; coverage computed on evaluated periods only.
23. Persistence: last actual with `start_time + 30m ≤ cutoff`; skill = 1 − MAE_f/MAE_p.
**Audit**
24. `test_no_leakage_on_real_snapshot`: for every cutoff in grid, assert 100% of selected rows satisfy `publish_time ≤ cutoff_utc`.
25. `test_recompute_matches`: independent, slow, loop-based reference implementation for one day matches vectorised results to 1e‑9.

**Acceptance:** `pytest backend/tests/domain` green; domain coverage ≥ 90%; `mypy --strict` clean. Commit: `feat(domain): …`, `test(domain): …`.

---

## Phase 4 — API & services (1.5 h)

1. `data/repository.py`: `Protocol` with `actuals() -> DataFrame`, `forecasts() -> DataFrame`, `fingerprint: str`, `manifest: dict`. `SnapshotRepository` loads & validates invariants; `InMemoryRepository` for tests.
2. `services/*`: orchestrate domain; memoise with `cache.py` (key = endpoint + sorted params + fingerprint). Convert frames to API models (rounding: MW to 1 dp, percentages to 2 dp for API; UI formats).
3. `api/v1/schemas.py`: Pydantic models per `ENGINEERING_REFERENCE §7`. Use `Field(description=…, examples=…)` so Swagger is self-documenting.
4. Routers: thin; param parsing with `Annotated[..., Query(...)]`; custom validators for `cutoff` (`^\d{2}:\d{2}$`, 00:00–23:59), dates in scope.
5. `main.py`: app factory; `GZipMiddleware`; CORS; request-ID + timing middleware; exception handlers (problem+json); OpenAPI metadata (title, version, description); docs at `/api/docs`; `openapi_url="/api/openapi.json"`; startup event warms default cutoff caches.
6. `scripts/gen_types.sh`: dump OpenAPI via `python -c "import json; from app.main import app; print(json.dumps(app.openapi()))" > frontend/openapi.json` then `npx openapi-typescript frontend/openapi.json -o frontend/src/api/types.gen.ts`.
7. Tests (`tests/api`): status codes, schema validation (using generated schema), edge params, 404/422 problem bodies, cache headers, CSV content, determinism, `test_recompute_matches` at API level (S3), OpenAPI snapshot test (committed `openapi.snapshot.json`).

**Acceptance:** Swagger works; contract tests green; p95 latency < 300 ms locally (measure with a quick script).

---

## Phase 5 — Frontend (4.0 h)

### 5.1 Setup (0.5 h)
```
npm i react-router-dom @tanstack/react-query recharts date-fns date-fns-tz clsx zod
npm i -D typescript vite @vitejs/plugin-react tailwindcss postcss autoprefixer eslint prettier \
        vitest @testing-library/react @testing-library/user-event @testing-library/jest-dom jsdom msw vitest-axe \
        openapi-typescript @playwright/test @vitest/coverage-v8
```
`vite.config.ts`: dev proxy `/api → http://localhost:8000`; `build.sourcemap=false`; manual chunks for `recharts`. `tsconfig`: `strict`, `noUncheckedIndexedAccess`.

### 5.2 Foundation (0.5 h)
`tokens.css` (light/dark variables: `--forecast`, `--actual`, `--over`, `--under`, `--band`, neutrals), `Shell`, `TopNav` (Desk · Lab · Revisions · About), `ProvenanceBar` (data source & snapshot hash from `/meta`), `ErrorBoundary`, `Skeleton`, `EmptyState`, `ErrorState`, `InfoTip`, `MethodologyDialog`, `urlState.ts` hooks, `api/client.ts` (fetch wrapper with problem+json parsing), `api/hooks.ts` (typed query hooks).

### 5.3 Decision Desk (1.25 h)
Layout (desktop): left control column (date picker with prev/next, cutoff select, Hindsight toggle, risk-level select, demand what-if input); right: **Decision banner** → **KPI strip** → **ForecastChart** → **VintageStrip** → **DataTable**.
- Banner: “Forecasts published up to **Wed 14 Jan 2026, 09:00 GMT** · latest vintage used: **08:30** · horizon **15.0–38.5 h**”.
- KPIs: mean/peak/min MW, total MWh, largest 3 h ramp, coverage `48/48`.
- ForecastChart: forecast line (stepAfter optional off), risk band (forecast − Q95…forecast − Q50 when enabled), actual line + error area in Hindsight mode, cutoff-independent X axis in London local, tooltip with MW, vintage `publish_time`, horizon, and (hindsight) error with colour semantics. Demand line + residual-to-procure area when entered.
- VintageStrip: tiny heat-strip showing publish time per period (visualises which vintage each half-hour uses).
- DataTable: sortable, sticky header, CSV export.
- Keyboard: ←/→ change day.

### 5.4 Accuracy Lab (1.25 h)
Order: **Scorecard** (cards for MAE, RMSE, Bias, nMAE, P90 |error|, P90 shortfall, over-forecast share, skill vs persistence, coverage) → **Daily trend** (MAE bars + bias line; click selects day → link to Desk) → **By horizon** (bar/line with shaded decision band) → **By hour** → **By wind level** → **Distribution** (histogram with P5/P50/P95 + shortfall marker) + **Scatter** (with 1:1 line) → **Worst days** table → **Cutoff sensitivity** → **Risk buffer** card (levels, overall vs hourly, back-test coverage vs target with a gauge/bars and honest caveat).
Each chart: title, one-line dynamic insight (from `lib/insights.ts`), “View as table”, export CSV, `aria-label`/description.

### 5.5 Revisions explorer (0.25 h)
Select a target half-hour (defaults from Desk context); chart of vintages (x = publish_time, y = forecast MW) with vertical cutoff line, highlighted selected vintage, and horizontal actual line (hindsight toggle). Caption explains why the highlighted point is the "latest available".

### 5.6 About/Methodology (0.1 h)
Render `METHODOLOGY.md`-aligned content: sources, definitions, worked example, sign convention, formulas, caveats, how to reproduce.

### 5.7 Polish & QA (0.15 h) — see Phase 5 acceptance below.

### 5.8 Frontend tests
- `lib/*`: formatters, urlState, insights, csv (table-driven).
- Components: KpiCard, Scorecard, DataTable (sorting), CutoffSelect, DeliveryDatePicker (disables out-of-scope), ForecastChart (renders aria summary, table toggle).
- Pages with MSW: Desk loading → loaded → error → empty; changing cutoff triggers new request with the right params; Hindsight toggle shows actual series.
- a11y: `vitest-axe` on each page; keyboard navigation test for date picker.
- Playwright (P1): `desk → lab → revisions` smoke at 1280×800 and 390×844; screenshot artefacts used for README.

**Phase 5 acceptance:** all P0 UI requirements met; no console errors; Lighthouse targets (S7) on production build; both light/dark readable; reduced-motion respected.

---

## Phase 6 — Analysis & insights (0.75 h)

`analysis/insights.py` imports the **same domain code** (no re-implementation), loads the snapshot, and writes `docs/INSIGHTS.md` with:
1. Headline metrics at default cutoff.
2. Horizon table and the decision horizon range.
3. Over/under-forecast frequency & magnitudes; P90/P95 shortfall.
4. Hour-of-day best/worst hours.
5. Wind-level analysis (largest error bin).
6. Top 5 worst days (+ one-line description such as max ramp or lull, computed from data).
7. Cutoff sensitivity table and conclusion.
8. Vintage value: MAE of latest-available vs earliest-available vs persistence.
9. Risk-buffer calibration table (in-sample vs walk-forward coverage).
10. Data coverage.
Also emit `docs/insights.json` consumed by the video script generator and by a test that asserts the numbers in `INSIGHTS.md` equal live API responses (prevents drift). **Every number spoken in the video must exist in `INSIGHTS.md`.**

---

## Phase 7 — Docker, Vercel, CI (1.5 h)

### 7.1 `backend/Dockerfile`
```dockerfile
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /srv
COPY backend/requirements.txt ./requirements.txt
RUN pip install -r requirements.txt
COPY backend/app ./app
COPY data/processed ./data/processed
ENV DATA_DIR=/srv/data
RUN useradd -r -u 10001 appuser && chown -R appuser /srv
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --retries=5 CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health').status==200 else 1)"
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000","--proxy-headers"]
```
(Build context = repo root: `docker build -f backend/Dockerfile .`.)

### 7.2 `frontend/Dockerfile` + `nginx.conf`
```dockerfile
FROM node:22-alpine AS build
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build
FROM nginx:1.27-alpine
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
```
```nginx
server {
  listen 80;
  root /usr/share/nginx/html;
  gzip on; gzip_types text/css application/javascript application/json image/svg+xml;
  add_header X-Content-Type-Options nosniff always;
  add_header Referrer-Policy strict-origin-when-cross-origin always;
  location /api/ { proxy_pass http://api:8000; proxy_set_header Host $host; }
  location / { try_files $uri /index.html; }
  location /assets/ { expires 1y; add_header Cache-Control "public, immutable"; try_files $uri =404; }
}
```

### 7.3 `docker-compose.yml`
```yaml
services:
  api:
    build: { context: ., dockerfile: backend/Dockerfile }
    ports: ["8000:8000"]
    healthcheck:
      test: ["CMD","python","-c","import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health')"]
      interval: 10s
      retries: 6
  web:
    build: { context: ., dockerfile: frontend/Dockerfile }
    ports: ["8080:80"]
    depends_on: { api: { condition: service_healthy } }
```
`scripts/smoke_docker.sh`: `docker compose up -d --build`, poll `http://localhost:8000/api/v1/health` and `http://localhost:8080/` and `http://localhost:8080/api/v1/meta`, check JSON fields, `docker compose down`.

### 7.4 Vercel
`api/index.py`:
```python
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.main import app  # noqa: E402  (ASGI app exposed to Vercel)
```
`vercel.json` (adapt after measuring):
```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "buildCommand": "cd frontend && npm ci && npm run build",
  "outputDirectory": "frontend/dist",
  "functions": {
    "api/index.py": { "includeFiles": "{backend/app/**,data/processed/**}", "maxDuration": 30 }
  },
  "rewrites": [
    { "source": "/api/(.*)", "destination": "/api/index" },
    { "source": "/((?!assets/|favicon).*)", "destination": "/index.html" }
  ],
  "headers": [
    { "source": "/(.*)", "headers": [
      { "key": "X-Content-Type-Options", "value": "nosniff" },
      { "key": "Referrer-Policy", "value": "strict-origin-when-cross-origin" },
      { "key": "X-Frame-Options", "value": "DENY" } ] },
    { "source": "/assets/(.*)", "headers": [ { "key": "Cache-Control", "value": "public, max-age=31536000, immutable" } ] }
  ]
}
```
Notes: root `requirements.txt` must pin the runtime deps; set `DATA_DIR` default to resolve relative to the repo (config does). Ensure FastAPI app serves under `/api/...` paths (routes defined with prefix `/api/v1`, docs at `/api/docs`) so the rewrite passes the original path. **Verify locally with `vercel dev` or `vercel build` if the CLI is available; otherwise document as human step.** Measure cold start; if > 4 s or bundle too large, apply ADR-007 fallback.
`scripts/verify_deploy.sh <base_url>`: curl `/`, `/api/v1/health`, `/api/v1/meta`, `/api/v1/decision-view?delivery_date=2026-01-15`, `/api/v1/accuracy/summary`, `/api/docs`; fail on non-200 or missing JSON fields; also check there is no `x-vercel-protection` / 401/403 (protected deployment).

### 7.5 CI (`.github/workflows/ci.yml`)
Jobs: `backend` (setup-python 3.12, cache pip, ruff, mypy, pytest+cov), `frontend` (setup-node 22, cache npm, lint, typecheck, vitest, build), `types-fresh` (regenerate types and `git diff --exit-code`), `docker` (build both images), `anonymity` (script). Trigger on `push` and `pull_request`. Add a status badge to README.

**Acceptance:** `docker compose up --build` works from a clean clone; `scripts/smoke_docker.sh` passes; CI green; Vercel config verified or listed in `HUMAN_ACTIONS.md` with exact commands.

---

## Phase 8 — Docs, README, video & submission kits (1.25 h)

### 8.1 README (required content; FR-P3)
1. Title, one-paragraph summary, badges (CI), **Live demo link** (`<<VERCEL_URL>>` placeholder replaced by the human), screenshots (2–3 from Playwright).
2. **What it does** (the two purposes) and the **core idea** (decision-time vintage selection with a diagram).
3. **Quick start**: Docker (`docker compose up --build` → `localhost:8080`), local dev (`make setup && make dev`), regenerate data (`make ingest`).
4. **Directory & file guide** (tree with one-line descriptions — mirrors SAS §4).
5. **Methodology summary**: scope, cutoff, sign convention, metrics list, horizon, risk buffer; link to `docs/METHODOLOGY.md`.
6. **Key findings** (5–6 bullets from `INSIGHTS.md`).
7. **API overview** with example `curl`s; link to `/api/docs`.
8. **Testing & quality**: commands, coverage, CI.
9. **Deployment**: Vercel steps; Heroku note.
10. **Assumptions & limitations**.
11. **AI assistance disclosure** (mandatory, explicit). Template:
   > **AI assistance disclosure.** This project was built with the help of AI tools: *<<tool names, e.g., Claude (Anthropic) via the Claude app / agentic coding tools>>* were used for planning, scaffolding, writing and reviewing code, tests and documentation. All design decisions, data-source verification, results and final code were reviewed and validated by the author, who is responsible for the submission.
   (The agent must fill in the real tools used; the human confirms.)
12. License (MIT) — no personal name; use "The WindLens contributors".

### 8.2 Docs
`docs/METHODOLOGY.md` (formulas, worked example with real numbers from the snapshot), `docs/DECISIONS.md` (ADRs 001–012 + any new), `docs/ARCHITECTURE.md` (Mermaid diagrams: context, container, sequence of a Decision Desk request, selection logic), `docs/INSIGHTS.md` (generated).

### 8.3 Video kit — `docs/VIDEO_SCRIPT.md`
Produce a timed script with **on-screen action + narration + insight numbers (pulled from `INSIGHTS.md`)**. Total ≤ 9:30 spoken (leave slack under the 10:00 cap). Structure:

**Part 1 — Client pitch (target 4:30; hard cap 5:00)**
| Time | Screen | Narration beats |
|------|--------|-----------------|
| 0:00–0:25 | Title card → Decision Desk | Who/why: day-ahead buyers need to know wind *as they knew it at decision time* and how much to trust it. One-sentence promise. |
| 0:25–1:30 | Desk for a representative day (pick a typical day) | Show banner (“forecasts up to 09:00 on D−1, latest vintage 08:30”), KPIs, forecast curve, vintage strip. Explain "latest available" vs "latest ever". Toggle cutoff (09:00 → 06:00) to show impact. |
| 1:30–2:15 | Hindsight toggle on same day | Reveal actuals; error colours; "this day: MAE X MW (Y%)". |
| 2:15–3:30 | Accuracy Lab: scorecard → horizon → hour → level | 3–4 headline insights with numbers: overall MAE/bias; error grows with horizon; worst hours; where errors are largest; worst days. |
| 3:30–4:20 | Risk buffer + back-test + what-if demand | "Plan a buffer of ~Z MW (P90 shortfall); back-test coverage C% vs target 90%." Show residual-to-procure with entered demand. Honest caveat. |
| 4:20–4:50 | Cutoff sensitivity + close | "Deciding at 09:50 vs 06:00 changes MAE by ΔMW." Value proposition + call to action (pilot results). |

**Part 2 — Tech lead review (target 4:30; hard cap 5:00)**
| Time | Screen | Narration beats |
|------|--------|-----------------|
| 5:00–5:40 | Repo tree (GitHub) + architecture diagram | Layers, snapshot-based serving, why (reliability, reproducibility, Vercel). |
| 5:40–6:50 | `domain/selection.py` + test | The core algorithm; boundary inclusivity; leakage assertion; Europe/London handling; property tests. |
| 6:50–7:30 | `metrics.py`, `risk.py` | Definitions, sign convention, walk-forward lag rationale, hand-computed tests. |
| 7:30–8:10 | `ingestion/` + `manifest.json` | Chunking, retries, idempotence, validation, fingerprint. |
| 8:10–8:50 | API (Swagger) + OpenAPI→TS types | Contracts, errors, caching, tests. |
| 8:50–9:20 | Frontend structure + a11y + tests | URL state, query hooks, charts-with-table, axe. |
| 9:20–9:50 | CI, Docker, Vercel, README, AI disclosure; trade-offs & next steps | What I'd do next (live ingestion, capacity normalisation if allowed, probabilistic forecasts). |

Include: pre-recording checklist (browser zoom 110%, hide bookmarks, light theme, test mic, notifications off, 1080p), rehearsal timing table, caption outline, YouTube settings (**Unlisted**; title neutral; no personal info in description), post-upload check in incognito.

### 8.4 `HUMAN_ACTIONS.md` (ordered)
1. Create the **public** GitHub repo named exactly `<anon-name>`; push (`git remote add origin …; git push -u origin main`); confirm no identity leakage (`scripts/check_anonymity.sh`, GitHub profile email privacy).
2. (If not done) run `make ingest` and commit the snapshot.
3. Create the Vercel project from the repo (Framework preset: **Other**), **Deployment Protection → Disabled / Public**, deploy; set the URL in README; run `scripts/verify_deploy.sh https://<url>`.
4. Record the video following `docs/VIDEO_SCRIPT.md`; upload to YouTube as **Unlisted**; paste the link into README (optional) and form.
5. Open **every** URL (repo, app, video) in an **incognito** window and tick the checklist.
6. Fill `docs/FORM_ANSWERS.md` details into the submission form and submit.

### 8.5 `docs/FORM_ANSWERS.md`
Pre-written fields: repo URL, live app URL, video URL, 3-sentence solution summary, assumptions list (cutoff, scope), AI tools disclosure, time spent (≤ 16 h; human to fill the real number), what you'd do next.

---

## Phase 9 — Final audit (0.5 h)

This phase executes `VERIFICATION_GATE.md` Tier 1 and starts Tier 2; that file is now authoritative on what counts as "passed" (pasted real evidence, not a description) and adds items this list used to miss. Run the audit and store evidence in `docs/AUDIT.md`:
1. `make lint typecheck test` all green; coverage numbers recorded — paste full output.
2. Clean clone test: `git clone` into temp → `docker compose up --build` → `scripts/smoke_docker.sh` — paste output, or mark RED per `docs/AGENT_CAPABILITIES.md` if no Docker daemon is available to you.
3. Lighthouse (desktop) on production build: record scores (S7), only if Tier 0 found a usable headless browser.
4. Axe results: zero serious/critical violations.
5. **Leakage audit**: run `test_no_leakage_on_real_snapshot` **against the real committed snapshot**; also manually inspect one day in the Revisions explorer.
6. **Data integrity (new, S8)**: confirm `data/processed/*` came from a genuine live Elexon pull, not `tests/fixtures/` — paste `manifest.json` fetch timestamps/row counts. If it can't be confirmed, this is RED regardless of everything else, and becomes `HUMAN_ACTIONS.md` item H3.
7. **Number consistency (new, S9)**: regenerate `docs/INSIGHTS.md` last, then run `scripts/check_numbers_consistency.sh` against **every** numeric claim in README/video script/form answers — not a five-number spot check.
8. **Placeholder sweep (new)**: `scripts/check_no_placeholders.sh` — zero unresolved `TODO`/`<<...>>`/lorem-ipsum tokens.
9. README checklist (FR-P3); links valid; screenshots present.
10. Anonymity check: `check_anonymity.sh`, **plus** the account/URL/video-recording vectors in `VERIFICATION_GATE.md §3–§4` that the script can't see; `git log` review (≥ 15 meaningful commits; Conventional Commits).
11. Walk through `ENGINEERING_REFERENCE §14` rubric; fix any <full-score rows.
12. Estimate video timing from the script's word count (`VERIFICATION_GATE.md §2.5`) before the human's stopwatch dry-run (≤ 9:30).
13. Close with the Tier-3 sign-off block from `VERIFICATION_GATE.md §6`.

---

## Appendix A — Dependency lists (pin exact versions at build time)

`backend/requirements.txt`: `fastapi`, `uvicorn[standard]` (Docker only; not needed on Vercel — keep in a separate `requirements-docker.txt` if bundle size matters), `pydantic>=2`, `pydantic-settings`, `pandas`, `numpy`, `httpx`, `tenacity`.
`backend/requirements-dev.txt`: `-r requirements.txt`, `pytest`, `pytest-cov`, `hypothesis`, `httpx`, `pytest-httpx` (or `respx`), `ruff`, `mypy`, `pandas-stubs`, `import-linter`, `pip-audit`.
Root `requirements.txt` (Vercel): the runtime subset.

## Appendix B — Commit plan (≥ 15 commits)
1 `chore: bootstrap repository skeleton` · 2 `docs: add data source verification` · 3 `feat(ingestion): elexon client with retries` · 4 `feat(ingestion): normalise and validate` · 5 `chore(data): add January 2026 snapshot` · 6 `feat(domain): time utils and cutoff` · 7 `feat(domain): decision-time selection` · 8 `feat(domain): metrics and breakdowns` · 9 `feat(domain): risk buffer and back-test` · 10 `feat(api): v1 endpoints and schemas` · 11 `feat(web): shell, routing and api hooks` · 12 `feat(web): decision desk` · 13 `feat(web): accuracy lab` · 14 `feat(web): revisions and methodology` · 15 `build: docker and compose` · 16 `build: vercel deployment` · 17 `ci: github actions` · 18 `docs: readme, methodology, video script` · 19 `test: audits and e2e` · 20 `chore: final polish`.

## Appendix C — Triage rules if time is short
Cut in this order: P2 items → Playwright e2e → scatter chart → by-level chart → what-if demand → dark mode → risk back-test UI (keep API). **Never cut:** selection logic + tests, accuracy summary/horizon/hour, methodology panel, Docker, deployment, README, AI disclosure, video script.
