# SAS.md — Software Architecture Specification

**Satisfies:** `PRD.md` v1.0. **Governs:** structure, components, data model, algorithms, interfaces, deployment.
**Conventions:** requirement IDs (`FR-*`, `S*`, `R*`) refer to `PRD.md`. Decision IDs `ADR-*` are logged in `docs/DECISIONS.md` (§14 lists the initial set).

---

## 1. Architectural drivers

| Driver | Consequence |
|--------|-------------|
| Correct "latest-available-at-decision-time" logic is the core value | Pure, isolated, heavily tested domain layer (FR-L1…L11) |
| Must run on Vercel (serverless) *and* Docker | Stateless backend, read-only committed data snapshot, no background workers, no DB server |
| Data is small (≈ 1.5k actual rows; forecasts ≲ a few hundred thousand rows) | In-memory columnar processing (pandas/NumPy), no database |
| Elexon availability and limits must not affect the demo | Ingestion decoupled from serving; snapshot committed |
| Reviewers read code | Hexagonal-lite layering, small modules, typed contracts end to end (OpenAPI → TS types) |
| ≤ 16 h budget | Minimal moving parts; one repo, one deployment unit; no premature infra |
| Anonymity | Neutral naming, no identity in metadata |

## 2. System context (C4 L1)

```
                 ┌────────────────────────────┐
                 │  Elexon BMRS Open Data API │   (only used OFFLINE by ingestion CLI)
                 │  FUELHH (WIND) · WINDFOR   │
                 └──────────────┬─────────────┘
                                │ HTTPS (batch, build-time / on-demand by developer)
                                ▼
┌─────────┐   HTTPS    ┌─────────────────────────────────────────────┐
│ Trader  │──────────▶ │            WindLens (this system)           │
│ Analyst │◀────────── │  React SPA  ⇄  FastAPI  ⇄  Data snapshot    │
│ Reviewer│            └─────────────────────────────────────────────┘
└─────────┘
```
Production serving never calls Elexon. The snapshot (`data/processed/`) is the system of record for the demo.

## 3. Container view (C4 L2)

| Container | Tech | Responsibility |
|-----------|------|----------------|
| **Web SPA** | React 18, TypeScript, Vite, React Router, TanStack Query, Recharts, Tailwind CSS (+ shadcn-style primitives), date-fns / date-fns-tz | Presentation, state in URL, charts, accessibility |
| **API service** | Python 3.12, FastAPI, Pydantic v2, pandas, NumPy, Uvicorn (Docker) / ASGI function (Vercel) | Serve analytics computed by the domain layer from the snapshot |
| **Data snapshot** | gzip CSV + JSON manifest, in repo | Immutable processed data |
| **Ingestion CLI** | Python (httpx, tenacity), shares `domain` normalisation | Fetch → cache raw → normalise → validate → write snapshot |
| **Reverse proxy (Docker only)** | nginx | Serve SPA static files and proxy `/api` → backend |

## 4. Repository layout (normative)

```
<anon-repo>/
├── README.md
├── HUMAN_ACTIONS.md
├── CHANGELOG.md                      # optional
├── Makefile
├── docker-compose.yml
├── vercel.json
├── requirements.txt                  # Vercel Python deps (mirrors backend/requirements.txt)
├── .env.example
├── .gitignore  .dockerignore  .editorconfig  .pre-commit-config.yaml
├── .github/workflows/ci.yml
├── api/
│   └── index.py                      # Vercel ASGI entrypoint → backend.app.main:app
├── backend/
│   ├── pyproject.toml                # ruff, mypy, pytest, coverage config
│   ├── requirements.txt  requirements-dev.txt
│   ├── Dockerfile
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                   # app factory, middleware, routers, error handlers
│   │   ├── config.py                 # pydantic-settings; all tunables
│   │   ├── deps.py                   # FastAPI dependencies (repository, services)
│   │   ├── logging.py
│   │   ├── api/v1/
│   │   │   ├── router.py
│   │   │   ├── health.py  meta.py  decision.py  revisions.py
│   │   │   ├── accuracy.py  risk.py  export.py
│   │   │   └── schemas.py            # Pydantic response/request models
│   │   ├── services/
│   │   │   ├── decision_service.py   # orchestrates domain for Decision Desk
│   │   │   ├── accuracy_service.py   # orchestrates domain for Accuracy Lab
│   │   │   ├── risk_service.py
│   │   │   └── cache.py              # tiny keyed LRU (functools / dict)
│   │   ├── domain/                   # PURE: no FastAPI, no I/O
│   │   │   ├── constants.py          # TZ, period length, sign convention docs
│   │   │   ├── timeutils.py          # cutoff, delivery-day, hour-of-day
│   │   │   ├── selection.py          # decision-time vintage selection
│   │   │   ├── horizon.py            # horizon calc & bucketing
│   │   │   ├── metrics.py            # all metrics
│   │   │   ├── breakdowns.py         # by hour/level/day/horizon
│   │   │   ├── baseline.py           # persistence
│   │   │   ├── risk.py               # quantile buffers, walk-forward back-test
│   │   │   └── models.py             # typed dataclasses / TypedDicts
│   │   ├── data/
│   │   │   ├── repository.py         # Protocol + SnapshotRepository
│   │   │   ├── loader.py             # read CSV.gz → typed DataFrames (validated)
│   │   │   └── fingerprint.py
│   │   └── ingestion/
│   │       ├── elexon_client.py      # HTTP client, chunking, retry
│   │       ├── normalise.py          # raw JSON → typed frames
│   │       ├── validate.py           # quality report
│   │       ├── pipeline.py           # orchestrates fetch → normalise → validate → write
│   │       └── cli.py                # `python -m app.ingestion.cli ...`
│   └── tests/
│       ├── conftest.py  fixtures/ (tiny hand-made raw & processed samples)
│       ├── domain/ (test_timeutils, test_selection, test_horizon, test_metrics, test_breakdowns, test_risk, test_baseline)
│       ├── ingestion/ (test_client_retry, test_normalise, test_validate)
│       ├── api/ (test_contract_*.py, test_openapi_snapshot.py)
│       └── test_end_to_end_snapshot.py
├── frontend/
│   ├── package.json  tsconfig.json  vite.config.ts  eslint.config.js  tailwind.config.ts
│   ├── Dockerfile  nginx.conf  index.html
│   ├── public/ (favicon, og image)
│   └── src/
│       ├── main.tsx  App.tsx  routes.tsx
│       ├── api/ (client.ts, hooks.ts, types.gen.ts  ← generated from OpenAPI)
│       ├── lib/ (format.ts, time.ts, units.ts, csv.ts, colors.ts, insights.ts, urlState.ts)
│       ├── components/
│       │   ├── layout/ (Shell, TopNav, Footer, ProvenanceBar)
│       │   ├── controls/ (DeliveryDatePicker, CutoffSelect, PeriodRange, HindsightToggle)
│       │   ├── charts/ (ForecastChart, VintageStrip, HorizonChart, HourChart, LevelChart, DistributionChart, ScatterChart, DailyTrendChart, SensitivityChart, RevisionsChart)
│       │   ├── kpi/ (KpiCard, KpiStrip, Scorecard)
│       │   ├── tables/ (DataTable, WorstDaysTable)
│       │   ├── help/ (MethodologyDialog, Glossary, InfoTip)
│       │   └── states/ (Skeleton, EmptyState, ErrorState)
│       ├── pages/ (DecisionDesk.tsx, AccuracyLab.tsx, Revisions.tsx, About.tsx)
│       ├── styles/ (index.css, tokens.css)
│       └── test/ (setup.ts, msw handlers)
├── data/
│   ├── raw/                          # committed (small) or gitignored per size rule (§7.5)
│   └── processed/
│       ├── actuals.csv.gz  forecasts.csv.gz
│       ├── manifest.json  quality_report.json
├── analysis/
│   ├── insights.py                   # reproducible script generating video numbers → docs/INSIGHTS.md
│   └── notebook.ipynb                # optional narrative (outputs cleared or committed lightly)
├── scripts/
│   ├── new_repo_name.sh  check_anonymity.sh  verify_deploy.sh  smoke_docker.sh  gen_types.sh
│   └── check_no_placeholders.sh  check_numbers_consistency.sh   # new — see VERIFICATION_GATE.md §2.3, §2.4
└── docs/
    ├── MASTER_PROMPT.md PRD.md SAS.md IMPLEMENTATION.md ENGINEERING_REFERENCE.md VERIFICATION_GATE.md  (the spec set)
    ├── DECISIONS.md  DATA_SOURCES.md  METHODOLOGY.md  INSIGHTS.md  AGENT_CAPABILITIES.md  AUDIT.md
    ├── VIDEO_SCRIPT.md  FORM_ANSWERS.md  ARCHITECTURE.md (diagrams)
    └── img/
```

> If the five spec documents would clutter the repo for graders, keep them under `docs/spec/`. Either is acceptable; README must index them.

## 5. Layering and dependency rules

```
frontend ──HTTP──▶ api (routers) ─▶ services ─▶ domain ◀── (pure)
                                     │
                                     └▶ data.repository (Protocol) ◀─ SnapshotRepository (CSV.gz)
ingestion ─▶ domain.normalise-compatible types ─▶ writes snapshot
```
Rules (enforced by an import-linter test or ruff `TID` rules):
1. `domain` imports only stdlib, `numpy`, `pandas`, `zoneinfo`. **Never** FastAPI, Pydantic models from `api`, or file I/O.
2. `services` call `domain` and the `Repository` protocol; they contain no HTTP concerns.
3. `api` routers translate HTTP ↔ services, validate params, shape responses (Pydantic).
4. `ingestion` may import `domain.constants/timeutils` only.
5. Frontend components never compute domain metrics; they format/present what the API returns. The only client-side calculations: unit formatting, residual-to-procure what-if (simple subtraction), insight sentence templating from returned numbers.

## 6. Domain model

All timestamps are **tz-aware UTC** in memory (`datetime64[ns, UTC]`). Local conversion only for delivery-day and hour-of-day derivations.

```python
# domain/models.py (conceptual)
@dataclass(frozen=True)
class Cutoff:                     # a decision cutoff for one delivery day
    delivery_date: date           # London local date
    local_time: time              # e.g. 09:00
    instant_utc: datetime

# Frames (pandas DataFrames with enforced dtypes)
Actuals:    start_time[UTC], generation_mw[float64]
Forecasts:  start_time[UTC], publish_time[UTC], generation_mw[float64]
Selected:   start_time, publish_time, forecast_mw, horizon_h, cutoff_utc, delivery_date
Joined:     Selected + actual_mw, error_mw (= forecast − actual), abs_error_mw, shortfall_mw (= max(0, error))
```

### 6.1 Invariants
- `Actuals.start_time` unique; all on :00 or :30.
- `Forecasts` unique on `(start_time, publish_time)`.
- `Selected` unique on `start_time`; `publish_time ≤ cutoff_utc` for every row (**asserted** in `select_decision_forecasts` and re-checked by an audit test).
- `horizon_h = (start_time − publish_time) / 1h`; may be negative for post-hoc forecasts (they are excluded by the selection rule for decision views; the horizon analysis ignores rows with `horizon_h < 0` and counts them).

## 7. Algorithms

### 7.1 Decision cutoff (FR-L1)
```
delivery_date  = London-local calendar date of start_time
cutoff_local   = datetime.combine(delivery_date − 1 day, cutoff_time) in Europe/London
cutoff_utc     = cutoff_local → UTC
```
Vectorised implementation: `local = start_time.dt.tz_convert("Europe/London")`; `d = local.dt.tz_localize(None).dt.normalize()`; `naive = d − 1 day + Δ(cutoff)`; `cutoff_utc = naive.dt.tz_localize("Europe/London", nonexistent="shift_forward", ambiguous="NaT").dt.tz_convert("UTC")`. Rows with NaT are impossible at 09:00 but are handled (raise a typed error).

### 7.2 Vintage selection (FR-L2, core)
```
Input: forecasts F(start_time, publish_time, mw), cutoff_time
1. F.cutoff_utc ← decision_cutoff(F.start_time, cutoff_time)
2. E ← F[F.publish_time ≤ F.cutoff_utc]            # inclusive boundary
3. idx ← E.groupby(start_time).publish_time.idxmax()
4. S ← E.loc[idx]; S.horizon_h ← (start_time − publish_time)/1h
Output: S (one row per start_time that has an eligible vintage)
Complexity: O(N) with a single sort/groupby; N ≲ 10^6.
```
Post-conditions asserted: uniqueness; `S.publish_time ≤ S.cutoff_utc`; no row in F with same `start_time` has `publish_time` in `(S.publish_time, S.cutoff_utc]`.

### 7.3 Join and error (FR-L4)
`J = S.merge(A, on="start_time", how="left")`. `error = forecast_mw − actual_mw`; rows with NaN actual are kept for the Decision view (shown without actual) and excluded from metrics (count reported).

### 7.4 Metrics (FR-L5) — definitions
Let rows i = 1..n with forecast f_i, actual a_i, e_i = f_i − a_i.
- MAE = mean|e|; RMSE = sqrt(mean e²); Bias = mean(e).
- nMAE = MAE / mean(a); WAPE = Σ|e| / Σa (reported alongside; equals nMAE when means align—keep one, show the other in the methodology if useful. **Use nMAE as the displayed headline "% of average output".**)
- MAPE (guarded) = mean(|e|/a) over a ≥ `MAPE_MIN_ACTUAL_MW` (default 500).
- Abs-error percentiles: P50, P90, P95 (linear interpolation; NumPy `method="linear"`).
- Signed-error percentiles: P5, P50, P95.
- Over-forecast share = mean(e > 0). Shortfall s_i = max(0, e_i): mean, P90, P95, max.
- Correlation r = Pearson(f, a). R² reported only if requested (not headline).
- Skill vs persistence = 1 − MAE_f / MAE_p over the same rows (FR-L11).
- Energy-equivalent: ΣMW × 0.5 = MWh (Decision view totals).

### 7.5 Horizon analysis (FR-L6)
For all forecast rows with `start_time ∈ window` and `0 ≤ horizon_h` (and join to actual): bucket horizon by `[0,6),[6,12),[12,18),[18,24),[24,36),[36,48),[48,72),[72,∞)`; compute metrics per bucket. Also return, for the active cutoff, the **decision horizon range** `[min, max]` over selected rows to shade on the chart. (Do not mix vintages inside a bucket's per-target average; compute over all rows—each row is a (target, vintage) pair—state this in the tooltip.)

### 7.6 Breakdowns (FR-L7)
- **By hour of day** (London local hour, 0–23, using half-hour periods grouped by hour or by 48 settlement periods; default 24 hours).
- **By wind level**: quantile bins (5) on actual (default) or forecast (query param), with bin edges returned.
- **By day**: daily MAE, bias, max abs error, shortfall P90.
- **Worst days / periods**: top-N by MAE and by max |error|; return links (delivery_date).

### 7.7 Cutoff sensitivity (FR-L8)
For each cutoff `c ∈ CUTOFF_GRID` (default `06:00, 08:00, 09:00, 09:20, 09:50, 10:00, 12:00`): run 7.2–7.4 and return the headline metrics + coverage + mean horizon. (Pure; memoised per cutoff.)

### 7.8 Persistence baseline (FR-L11)
For delivery day D with cutoff c: `a_last` = actual of the latest period with `start_time + 30 min ≤ c`; baseline forecast for all periods of D = `a_last`. Periods where `a_last` is NaN → baseline missing → skill computed on the intersect set (count reported).

### 7.9 Risk buffer (FR-L9) and walk-forward back-test (FR-L10)
- Empirical **signed error** distribution E (overall) and E_h (by London hour).
- Buffer at level p: `B_p = Q_p(E)` (p ∈ {0.5, 0.75, 0.9, 0.95}) — the over-forecast margin exceeded only (1 − p) of the time. Risk-adjusted forecast `f*_i = max(0, f_i − B_p)`.
- **Walk-forward**: for each delivery day d with ≥ `MIN_HISTORY_DAYS` (default 7) earlier days, compute `B_p(d)` from days `< d` only (and only days whose actuals are fully known by the cutoff of d — i.e., delivery date ≤ d−2 to avoid using outcomes not yet observed at 09:00 on d−1; **implement this lag explicitly and test it**). Coverage = share of evaluated periods with `a_i ≥ f*_i`. Report coverage vs p, mean buffer, and the share of days with ≥ 1 breach.
- Output labels: `in_sample` vs `walk_forward`.

## 8. API specification (overview; full schemas in ENGINEERING_REFERENCE §7)

Base path `/api/v1`. All GET. JSON unless stated. Times are ISO‑8601 UTC with `Z`; additional `local` fields in `Europe/London`.

| Endpoint | Purpose | Key params |
|----------|---------|------------|
| `GET /health` | Liveness + dataset fingerprint | — |
| `GET /meta` | Scope, defaults, available delivery dates, cutoff grid, data coverage, ingestion info, constants | — |
| `GET /decision-view` | Decision-time forecast for one delivery day (+ actual/error for hindsight) | `delivery_date`, `cutoff=HH:MM` (default from config), `include_actuals` |
| `GET /revisions` | All vintages for a target half-hour (+ cutoff, selected vintage, actual) | `target_time` (UTC ISO) or (`delivery_date`,`period`), `cutoff` |
| `GET /accuracy/summary` | Scorecard | `start`,`end` (delivery dates), `cutoff` |
| `GET /accuracy/daily` | Daily accuracy series | same |
| `GET /accuracy/by-horizon` | Metrics by horizon bucket + decision band | `start`,`end`,`cutoff` |
| `GET /accuracy/by-hour` | Metrics by London hour | same |
| `GET /accuracy/by-level` | Metrics by wind-level bin | `+ basis=actual|forecast`, `bins` |
| `GET /accuracy/distribution` | Histogram of signed errors + scatter sample | `+ bins` |
| `GET /accuracy/worst` | Top-N worst days/periods | `+ n`, `metric` |
| `GET /accuracy/cutoff-sensitivity` | Metrics across cutoff grid | `start`,`end` |
| `GET /risk/buffer` | Quantile buffers overall & by hour (in-sample) | `start`,`end`,`cutoff`,`levels` |
| `GET /risk/backtest` | Walk-forward coverage | `cutoff`, `level`, `min_history_days` |
| `GET /export/decision-view.csv` | CSV of Decision view | as decision-view |
| `GET /export/accuracy.csv` | CSV of selected accuracy table | `table=by-horizon|by-hour|daily|...` |

**Errors:** RFC 7807 `application/problem+json`: `{type,title,status,detail,instance,errors?}`. `404` out-of-scope date, `422` validation, `500` generic (no stack traces).
**Caching:** `Cache-Control: public, max-age=300, stale-while-revalidate=3600`; `ETag` = dataset fingerprint + normalised query.
**Versioning:** URL prefix; breaking changes ⇒ `/v2`.
**OpenAPI:** exported to `frontend/openapi.json` by `scripts/gen_types.sh`; TS types generated with `openapi-typescript`; CI fails if generated file is stale.

## 9. Deployment architecture

### 9.1 Local dev
- Backend: `uvicorn app.main:app --reload --port 8000` from `backend/`.
- Frontend: `npm run dev` (Vite, port 5173) with proxy `/api → http://localhost:8000`.

### 9.2 Docker (FR-P1)
```
docker compose up --build
  ├─ api  (python:3.12-slim, non-root, uvicorn, healthcheck)  :8000
  └─ web  (nginx:alpine serving frontend/dist, proxy /api → api:8000) :8080
```
- Multi-stage builds; pinned base image tags; `.dockerignore`; data snapshot copied into the API image (`/app/data`); `DATA_DIR` env points to it.
- Healthchecks and `depends_on: condition: service_healthy`.

### 9.3 Vercel (FR-P2) — single project, two build targets
- Static SPA from `frontend/dist` (Vite build).
- Python serverless function at `/api/*` via root `api/index.py` which does `sys.path.insert(0, "backend")` and `from app.main import app`.
- `vercel.json` (normative shape; see IMPLEMENTATION Phase 7 for the full file): `buildCommand`, `outputDirectory`, `functions["api/index.py"].includeFiles = "{data/processed/**,backend/app/**}"`, `rewrites` `/api/(.*)` → `/api/index`, SPA fallback `/(.*)` → `/index.html`, security headers.
- Constraints to respect: serverless Python bundle limit (~250 MB uncompressed) — keep dependency set to FastAPI, Pydantic, pandas, NumPy, (no pyarrow, no scipy, no matplotlib). **If bundle/cold-start proves problematic**, fallback plan (ADR-007): replace pandas in the request path with a NumPy-only implementation, or precompute all selection results for the `CUTOFF_GRID` at ingestion time into compact JSON and serve those (UI retains continuous cutoff for grid values only). Decide by measurement in Phase 7; do not pre-optimise.
- Disable Vercel Deployment Protection / Authentication so the URL is public.
- Environment variables: none required (all defaults baked in); optional `DEFAULT_CUTOFF`.

### 9.4 Heroku fallback (documented, not primary)
Container deploy of the same `backend` image plus the built SPA served by FastAPI `StaticFiles` (a build flag copies `frontend/dist` into the image). Instructions in ENGINEERING_REFERENCE §12.

## 10. Frontend architecture

- **Routing:** `/` → redirect to `/desk`; `/desk`, `/lab`, `/revisions`, `/about`. Query params are the source of truth (`date`, `cutoff`, `from`, `to`, `hindsight`, `level`, `target`). `urlState.ts` provides typed read/write hooks; changing a control updates the URL (replace for continuous controls, push for date changes).
- **Server state:** TanStack Query per endpoint (`staleTime` 5 min, `gcTime` 1 h, retry 1 with backoff), query keys include all params; prefetch adjacent days on the Desk.
- **Charts:** Recharts wrapped by thin components with a consistent props contract (`data`, `units`, `ariaLabel`, `onPointFocus`). Large series (≤ 1,500 points) fine; use `isAnimationActive={false}` for perf. A **"View as table"** toggle on every chart renders the same data in a semantic `<table>`.
- **Design system:** Tailwind tokens (`tokens.css` CSS variables) for colour semantics (§9 PRD), spacing and typography; light/dark; focus rings; reduced motion.
- **Performance:** route-level code-splitting (`React.lazy`) for Lab and Revisions; chart components lazy; memoised selectors; preconnect none (same origin).
- **Error boundaries** per page; global `ErrorState`; Sentry-style logging omitted (no external services).
- **Testing:** Vitest + React Testing Library + MSW (mock API using fixtures generated from the backend's real responses), `vitest-axe` for accessibility, Playwright smoke e2e (desktop & mobile viewports) in CI optional/P1.
- **Insights text:** `lib/insights.ts` turns returned numbers into sentences (e.g., horizon growth), unit-tested.

## 11. Cross-cutting concerns

| Concern | Design |
|---------|--------|
| **Configuration** | `pydantic-settings` (`config.py`): `DATA_DIR`, `TIMEZONE=Europe/London`, `DEFAULT_CUTOFF=09:00`, `SCOPE_MODE`, `SCOPE_START/END`, `CUTOFF_GRID`, `MAPE_MIN_ACTUAL_MW`, `MIN_HISTORY_DAYS`, `HORIZON_BUCKETS`, `CORS_ORIGINS`. Env-overridable, validated at start-up |
| **Caching** | Dataset loaded once per process (`lru_cache` on repository factory). Service-level memoisation keyed `(endpoint, normalised params, dataset_fingerprint)` with a bounded dict; safe because data immutable |
| **Concurrency** | Stateless; CPU-bound endpoints are fast (<100 ms) so run in the threadpool (sync route handlers) |
| **Validation** | Pydantic models + custom validators (`cutoff` regex & range, date in scope, `start ≤ end`) |
| **Errors** | Domain exceptions (`OutOfScopeError`, `NoDataError`) → handlers → problem+json |
| **Logging** | JSON logs: `ts, level, request_id, method, path, status, duration_ms`; no PII |
| **Security** | Input validation, CORS allowlist, security headers (CSP `default-src 'self'`; `img-src 'self' data:`; `style-src 'self' 'unsafe-inline'` only if Tailwind requires; otherwise strict), pinned deps, `pip-audit`/`npm audit` in CI (non-blocking report) |
| **Observability** | `/health` includes `data_fingerprint`, `rows`, `window`; `X-Request-ID` header |
| **Accessibility** | See PRD FR-U9; axe tests |
| **Testability** | Pure domain; repository protocol enables in-memory fake; API tests use `TestClient` with fixture snapshot |
| **Reproducibility** | `manifest.json` stores request URLs/params, UTC fetch times, row counts, SHA-256; `make ingest` regenerates; `make verify-snapshot` checks hash |

## 12. Data architecture

### 12.1 Pipeline (offline)
```
fetch (per-day chunks, retries) ─▶ data/raw/{dataset}/{YYYY-MM-DD}.json
        ─▶ normalise (typed frames, dedupe) ─▶ validate (quality_report.json)
        ─▶ write data/processed/{actuals,forecasts}.csv.gz + manifest.json
```
- **Chunking:** FUELHH by settlement date range per day; WINDFOR by `publishDateTime` range per day (confirm param names in Phase 2). Merge, then dedupe.
- **Idempotency:** a chunk is skipped if raw file exists and manifest hash matches (`--force` to refetch).
- **Window:** per FR-D4 (config `INGEST_START`, `INGEST_END`).
- **Size policy:** if `forecasts.csv.gz` ≤ ~25 MB commit it; otherwise commit only horizon-bounded rows (`horizon_h ≤ 96`, configurable and documented) — decision-time logic needs ≤ ~40 h, horizon chart ≤ 72+ h bucket. Raw cache is gitignored if > 25 MB total; the manifest + processed files stay committed.

### 12.2 Processed schema
`actuals.csv.gz`: `start_time` (ISO‑8601 Z), `generation_mw` (float).
`forecasts.csv.gz`: `start_time`, `publish_time`, `generation_mw`.
`manifest.json`: `{schema_version, generated_at, source:{base_url, datasets:[…]}, window:{…}, chunks:[{dataset,params,url,rows,sha256,fetched_at}], processed:{actuals:{rows,sha256}, forecasts:{rows,sha256}}, fingerprint}`.
`quality_report.json`: coverage and anomaly counts (see ENGINEERING_REFERENCE §6.4).

### 12.3 Runtime access
`SnapshotRepository` loads both CSVs once, enforces dtypes/invariants (§6.1), exposes `actuals()`, `forecasts()`, `fingerprint`, `window`. Pre-sorting by `(start_time, publish_time)` once.

## 13. Requirements traceability matrix

| PRD | Component(s) | Test(s) |
|-----|--------------|---------|
| FR-D1–D7 | `ingestion/*`, `data/loader` | `tests/ingestion/*`, `test_end_to_end_snapshot` |
| FR-L1 | `domain/timeutils.py` | `test_timeutils.py` |
| FR-L2, L3 | `domain/selection.py`, `horizon.py` | `test_selection.py` (+ audit) |
| FR-L4, L5 | `domain/metrics.py` | `test_metrics.py` |
| FR-L6, L7 | `domain/breakdowns.py`, `horizon.py` | `test_breakdowns.py` |
| FR-L8 | `services/accuracy_service.py` | `test_contract_accuracy.py` |
| FR-L9, L10 | `domain/risk.py` | `test_risk.py` |
| FR-L11 | `domain/baseline.py` | `test_baseline.py` |
| FR-A1–A6 | `api/v1/*`, `main.py` | `tests/api/*` |
| FR-U1–U4 | `pages/*`, `components/*` | Vitest + Playwright |
| FR-U5, U6 | `components/risk`, `lib` | component tests |
| FR-U7–U11 | `components/states`, a11y, `layout` | axe + visual checklist |
| FR-P1–P6 | Docker files, vercel.json, scripts, docs | `smoke_docker.sh`, `verify_deploy.sh`, CI |
| S1 | selection audit | `test_no_leakage` |
| S2 | caching, vectorised domain | perf test |
| S3 | contract test vs independent recomputation | `test_contract_accuracy.py::test_recompute_matches` |
| S8, FR-P7 | `docs/AGENT_CAPABILITIES.md`, ingestion pipeline | `VERIFICATION_GATE.md §1` (T1), `manifest.json` |
| S9, FR-P8 | `analysis/insights.py` → `docs/INSIGHTS.md`, `scripts/check_numbers_consistency.sh` | `VERIFICATION_GATE.md §2.4` |
| FR-P9, FR-P10 | `HUMAN_ACTIONS.md` H2/H5/H7 | `VERIFICATION_GATE.md §3`, `§4` |

## 14. Architecture decision records (initial set; copy into `docs/DECISIONS.md`)

| ADR | Decision | Rationale | Alternatives |
|-----|----------|-----------|--------------|
| 001 | Cutoff default **09:00 Europe/London D−1**, configurable | Conservative vs GB day-ahead auction gate closures; unknown client cutoff | 09:20/09:50/12:00 (offered in sensitivity) |
| 002 | Scope = decision dates in Jan 2026 (delivery Jan 2–Feb 1) | Literal reading of brief | delivery-date reading (config) |
| 003 | `error = forecast − actual` | Positive = shortfall risk for buyer | actual − forecast |
| 004 | Snapshot-based serving; ingestion offline | Reliability on serverless; reproducible | Live calls to Elexon per request |
| 005 | FastAPI + pandas/NumPy, no DB | Small data; vectorised; simple | SQLite/DuckDB/Postgres |
| 006 | Single repo, single Vercel project (SPA + Python function) | Fewer moving parts | Separate FE/BE deployments |
| 007 | Measure bundle/cold-start; fallback to NumPy-only/precomputed grid | Avoid premature optimisation | Always precompute |
| 008 | Recharts | Sufficient, accessible with wrappers, small learning curve | ECharts, visx, Plotly |
| 009 | OpenAPI → generated TS types | End-to-end type safety | Hand-written types |
| 010 | Walk-forward with 2-day outcome lag | Avoid leakage in buffer back-test | Naive expanding window |
| 011 | nMAE uses mean actual (no capacity data allowed) | Constraint C5 | Installed capacity |
| 012 | Committed processed data; raw optional | Anyone can run offline | Download on build |

## 15. Failure modes and handling

| Failure | Detection | Handling |
|---------|-----------|----------|
| Snapshot missing/corrupt | Start-up validation | Fail fast with explicit log; `/health` 503 |
| Date out of scope | Param validation | 404 problem+json with valid range |
| No eligible vintage for a period | Selection | Row omitted from Selected; counted in `coverage.missing_forecast`; UI shows gap marker |
| Missing actual | Join | `actual_mw=null`; excluded from metrics |
| Empty metric set | n=0 | Return `null` metrics with `n=0`, UI empty state |
| Vercel cold-start timeout | Observed | ADR-007 fallback |
| Elexon changes schema | Ingestion tests with recorded fixtures | Adapter isolates mapping |

## 16. Performance design

- Load once; pre-sorted frames; selection via vectorised groupby per cutoff (≈ tens of ms for 10⁵–10⁶ rows); memoise by cutoff (7–10 distinct values typical).
- Pre-warm: on start-up compute and cache the default cutoff selection.
- Responses small (≤ 100 KB); gzip enabled (`GZipMiddleware`, min size 1 KB).
- Frontend: lazy routes, memoised charts, `content-visibility` for tables.

## 17. Quality gates (CI)

`ruff check`, `ruff format --check`, `mypy --strict app/domain app/services`, `pytest --cov` (fail-under 85 total, 90 domain), OpenAPI snapshot diff, `npm run lint`, `npm run typecheck`, `npm run test -- --run`, `npm run build`, Docker build for both images, generated-types freshness check, anonymity check script.
