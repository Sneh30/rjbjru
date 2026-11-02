# ENGINEERING_REFERENCE.md — Handbook, Reference Library & Governance Guide

**Purpose:** the long-lived reference the agent consults while building and the reviewer consults while evaluating. It does not change *what* is built (PRD) or *how it is structured* (SAS); it supplies the **definitions, standards, schemas, edge-case catalogues, runbooks and checklists** that make the build unambiguous.

**Table of contents**
1. Glossary
2. Domain primer (day-ahead market, wind forecasting)
3. Python standards
4. TypeScript / React standards
5. Git, review & documentation standards
6. Data reference (sources, fields, fixtures, quality report)
7. API reference (schemas & examples)
8. Metric reference (formulas & interpretation)
9. Selection logic: edge-case catalogue
10. UI/UX & chart design reference
11. Testing strategy & catalogue
12. Deployment reference (Docker, Vercel, Heroku)
13. Runbooks & troubleshooting
14. 100/100 self-scoring rubric
15. Governance: risks, quality gates, change control
16. FAQ of ambiguities (rulings)
17. Checklists (pre-commit, pre-deploy, pre-record, pre-submit)
18. Insight-writing & wording rules
19. Appendices (config reference, command cheat-sheet, example worked day)

---

## 1. Glossary

| Term | Definition |
|------|------------|
| **Day-ahead market (DAM)** | Wholesale auction where power for delivery day *D* is traded on *D−1*. Buyers commit before knowing actual weather. |
| **Delivery day (D)** | London-local calendar day for which power is bought. 48 half-hour periods in January. |
| **Decision date (D−1)** | The day on which the purchase decision is made. |
| **Decision cutoff** | Latest instant at which the buyer can use information. Default 09:00 Europe/London on D−1 (assumption; configurable). |
| **Target time / `startTime`** | Start of a half-hour period for which generation is forecast/measured (UTC in source). |
| **Vintage / `publishTime`** | The moment a particular forecast was created. A target has many vintages. |
| **Horizon (lead time)** | `startTime − publishTime`, in hours. |
| **Latest available forecast** | For target T: the vintage with the maximum `publishTime` ≤ cutoff(T). |
| **Actual / outturn** | Measured generation (FUELHH, WIND). |
| **Error** | `forecast − actual` (MW). Positive = over-forecast. |
| **Over-forecast** | Forecast > actual. Less wind than expected → buyer must buy more → *shortfall risk*. |
| **Under-forecast** | Forecast < actual. More wind than expected → possible over-purchase. |
| **Shortfall** | `max(0, forecast − actual)`. |
| **Bias** | Mean signed error (MW). |
| **MAE / RMSE** | Mean absolute / root-mean-square error (MW). |
| **nMAE** | MAE ÷ mean(actual), shown as %. (No capacity data allowed, so capacity-normalised error is not available.) |
| **Persistence baseline** | Naive forecast: last known actual at the cutoff held constant. |
| **Skill score** | `1 − MAE_forecast / MAE_baseline`; > 0 means better than baseline. |
| **Risk buffer (B_p)** | p-th empirical quantile of signed error; the over-forecast margin exceeded only (1−p) of the time. |
| **Risk-adjusted forecast** | `max(0, forecast − B_p)`. |
| **Walk-forward back-test** | Evaluating a rule on each day using only information that would have been available before it. |
| **Coverage (empirical)** | Share of periods where `actual ≥ risk-adjusted forecast`; ideally ≈ p. |
| **MW vs MWh** | Power vs energy. A half-hour at 8,000 MW = 4,000 MWh. |
| **Snapshot** | Committed processed dataset the app serves. |
| **Fingerprint** | Short hash identifying the snapshot (displayed in UI/health). |

## 2. Domain primer

### 2.1 Why the problem is subtle
Elexon publishes wind forecasts repeatedly; for any half-hour there may be dozens of forecasts at different lead times. Naïvely joining "forecast" to "actual" by `startTime` picks arbitrary or hindsight-contaminated vintages. A trader at 09:00 on D−1 can only use forecasts that existed by then. The accuracy of *those* forecasts (15–39 h ahead for a 09:00 cutoff) is what matters — not the accuracy of 1-hour-ahead nowcasts.

### 2.2 Why errors matter asymmetrically
If wind is over-forecast, residual demand is understated; the buyer must source the gap later (intraday/balancing), often at a worse price. If wind is under-forecast, the buyer may over-purchase and need to sell back. Hence the product highlights **over-forecast tail risk** (shortfall P90/P95) and provides a buffer. Do not claim price impact — no price data is in scope.

### 2.3 What wind forecast error typically looks like (hypotheses to *test*, not assert)
- Error grows with horizon.
- Absolute error is larger at mid-to-high output (steeper part of the power curve) and during fast ramps/storm fronts.
- Relative error is large at very low output (MAPE unstable → use guarded MAPE/nMAE).
- Errors are autocorrelated across adjacent half-hours (a "bad day" is bad for many periods) → daily aggregation matters; periods are not independent, so don't over-interpret period-level confidence.
- 31 days of January ≠ annual behaviour (seasonality).

### 2.4 Market-timing note (state as assumption)
GB day-ahead auctions close in the morning UK time on D−1. The exact gate closure differs by venue. The product uses 09:00 as a safe default and offers a grid (06:00–12:00) to demonstrate sensitivity. Never state the client's actual cutoff as fact.

## 3. Python standards

### 3.1 Tooling and config (`pyproject.toml`)
```toml
[tool.ruff]
line-length = 100
target-version = "py312"
[tool.ruff.lint]
select = ["E","F","I","B","UP","SIM","C4","PT","RUF","TID","N","D","PL","PERF"]
ignore = ["D203","D213","PLR2004","D100","D104"]
[tool.ruff.lint.per-file-ignores]
"tests/**" = ["D","PLR2004","PLR0913"]
[tool.mypy]
python_version = "3.12"
strict = true
plugins = []
[[tool.mypy.overrides]]
module = ["tests.*"]
disallow_untyped_defs = false
[tool.pytest.ini_options]
addopts = "-q --strict-markers --cov-branch"
testpaths = ["tests"]
filterwarnings = ["error"]
[tool.coverage.report]
fail_under = 85
exclude_lines = ["pragma: no cover","if TYPE_CHECKING:"]
```

### 3.2 Rules
1. Type-annotate everything public; `from __future__ import annotations` not required on 3.12.
2. Pure functions in `domain`: no I/O, no globals, no logging; inputs/outputs documented with units.
3. Prefer `pandas` vectorisation; no Python loops over rows except in the independent reference implementation used by tests.
4. Use `Decimal` nowhere (floats suffice); round only at the API boundary.
5. Never use naive datetimes. Dtypes: `datetime64[ns, UTC]`. Convert to London only for date/hour derivations.
6. Exceptions: custom hierarchy `WindLensError → OutOfScopeError | NoDataError | DataIntegrityError | ConfigError`. No bare `except`.
7. Docstrings: Google style; first line imperative; include **Units**, **Sign convention**, **Raises**.
8. Constants in `constants.py` or `config.py`; no magic numbers (500 MW, 0.5 h, 48 periods).
9. No mutable default args; no module-level side effects; dataset access only via the repository.
10. Logging: `logging.getLogger(__name__)`; JSON formatter in `logging.py`; never log full payloads.
11. Complexity: functions ≤ 40 lines, modules ≤ 250 lines, cyclomatic ≤ 10 (ruff `PLR`).
12. Pydantic models: `model_config = ConfigDict(frozen=True, extra="forbid")`; descriptive `Field(description=…)`.
13. Randomness: none in production code; tests that need randomness seed it.
14. Security: validate all query params; no `eval`, no shelling out in the API; pin dependencies.

### 3.3 Docstring example
```python
def select_decision_forecasts(forecasts: pd.DataFrame, cutoff_local: time) -> pd.DataFrame:
    """Return, per target half-hour, the latest forecast published at or before the decision cutoff.

    Args:
        forecasts: Columns ``start_time`` (UTC), ``publish_time`` (UTC), ``generation_mw`` (MW).
        cutoff_local: Wall-clock cutoff on the previous London day (e.g. ``time(9, 0)``).

    Returns:
        One row per target with an eligible vintage: ``start_time``, ``publish_time``,
        ``forecast_mw`` (MW), ``horizon_h`` (hours), ``cutoff_utc``, ``delivery_date``.

    Raises:
        DataIntegrityError: if the no-leakage post-condition fails.

    Notes:
        The boundary is inclusive (``publish_time <= cutoff_utc``).
    """
```

## 4. TypeScript / React standards

1. `strict: true`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`. No `any`; `unknown` + narrowing. ESLint: `@typescript-eslint/recommended-type-checked`, `react-hooks`, `jsx-a11y`, `import/order`.
2. Components: functional, named exports, props typed via interfaces; ≤ 150 lines; presentational vs container split.
3. Data fetching only via `api/hooks.ts` (TanStack Query). No `fetch` in components. Keys: `[endpoint, params]`.
4. URL is the source of truth for filters; derive state from `useSearchParams`; update with `replace` for continuous controls.
5. Formatting: central `lib/format.ts` — `fmtMW(n)` → `8,123 MW`; `fmtPct(n)` → `7.4%`; `fmtMWh`; `fmtTimeLondon(iso)`; **never inline `toFixed` in JSX**.
6. Time: always use `date-fns-tz` with `Europe/London`; show UTC in tooltips; never rely on the browser's local zone.
7. Styling: Tailwind utility classes + CSS variables for tokens; no inline hex colours outside `tokens.css`/`colors.ts`.
8. Accessibility: semantic HTML (`header/nav/main/footer`), one `h1` per page, labelled controls, visible focus, `aria-live="polite"` for data refresh status, charts wrapped in `figure` with `figcaption` + table alternative.
9. Performance: `React.lazy` routes, `useMemo` for chart series, avoid re-render storms (stable callbacks), no animation on large series.
10. Error handling: error boundaries per page; `ErrorState` shows problem+json `title/detail` and a Retry.
11. Tests: React Testing Library queries by role/label; MSW for network; no snapshot tests of large DOM; `vitest-axe` on pages.
12. No `console.*` in production code (ESLint rule `no-console` = error).
13. Dependencies: minimal; justify each in `docs/DECISIONS.md` if > 30 KB gzip.

## 5. Git, review & documentation standards

- **Commits:** Conventional Commits (`feat`, `fix`, `docs`, `test`, `build`, `ci`, `chore`, `refactor`, `perf`). Imperative, ≤ 72 chars subject; body explains *why*. Reference requirement IDs (e.g., `FR-L2`).
- **Branching:** work on `main` with short commits, or short-lived branches merged without squash; history must be readable.
- **PR-style self-review checklist (apply per phase):** correctness, tests, naming, dead code, docs, security, performance, accessibility.
- **Docs:** README = how to run & what it is; `docs/METHODOLOGY.md` = what the numbers mean; `docs/DECISIONS.md` = why; code comments = intent only.
- **ADR template:** `ID · Date · Context · Decision · Consequences · Alternatives`.
- **Anonymity:** author/maintainer fields omitted or "WindLens contributors"; license holder "WindLens contributors"; no personal links; Docker labels neutral; no screenshots with personal browser profiles/bookmarks/tabs.
- **Secrets:** none required; `.env.example` only documents optional tunables.

## 6. Data reference

> **Always verify against the live OpenAPI/spec in Phase 1.** The following is the *expected* contract.

### 6.1 Sources
| Dataset | Docs path | Expected endpoint | Expected key params | Notes |
|---------|-----------|-------------------|---------------------|-------|
| FUELHH | `/api-documentation/endpoint/datasets/FUELHH/stream` | `GET {base}/datasets/FUELHH/stream` | `settlementDateFrom`, `settlementDateTo`, `settlementPeriodFrom/To`, `fuelType` (repeatable) | Half-hourly generation outturn by fuel type. Use `fuelType=WIND`. |
| WINDFOR | `/api-documentation/endpoint/datasets/WINDFOR/stream` | `GET {base}/datasets/WINDFOR/stream` | `publishDateTimeFrom`, `publishDateTimeTo` | Wind generation forecasts with `publishTime`. |
`base = https://data.elexon.co.uk/bmrs/api/v1`. Responses are JSON arrays (stream endpoints). If a param is rejected, consult the spec; record the actual names in `docs/DATA_SOURCES.md`.

### 6.2 Field mapping
| Source field | Dataset | Processed field | Type | Notes |
|--------------|---------|-----------------|------|-------|
| `startTime` | both | `start_time` | UTC timestamp | Period start; 30-min grid |
| `publishTime` | WINDFOR | `publish_time` | UTC timestamp | Vintage |
| `publishTime` | FUELHH | (used only to dedupe) | UTC timestamp | Keep latest per `startTime` |
| `generation` | both | `generation_mw` | float (MW) | Average over the half-hour |
| `fuelType` | FUELHH | filter `== WIND` | str | Case-insensitive match |
| `settlementDate/Period` | FUELHH | (not retained) | — | Cross-check only |

### 6.3 Fixture shapes (use for tests; replace with real samples in Phase 1)
```json
// FUELHH row
{"dataset":"FUELHH","publishTime":"2026-01-14T00:30:00Z","startTime":"2026-01-14T00:00:00Z",
 "settlementDate":"2026-01-14","settlementPeriod":1,"fuelType":"WIND","generation":7421}
// WINDFOR row
{"dataset":"WINDFOR","publishTime":"2026-01-13T08:00:00Z","startTime":"2026-01-14T00:00:00Z","generation":7810.5}
```

### 6.4 `quality_report.json` schema
```json
{
  "schema_version": 1,
  "generated_at": "2026-…Z",
  "actuals": {"rows": 1488, "expected_rows": 1488, "missing_periods": [], "duplicates_dropped": 0, "nan_dropped": 0, "min": 0, "max": 0, "mean": 0},
  "forecasts": {"rows": 0, "vintages": 0, "first_publish": "…", "last_publish": "…", "duplicates_dropped": 0, "nan_dropped": 0, "horizon_h": {"min": 0, "p50": 0, "max": 0}},
  "decision_coverage": {"cutoff": "09:00", "delivery_days": 32, "periods_expected": 1536, "periods_with_forecast": 0, "periods_missing": []},
  "warnings": [], "errors": []
}
```
(`actuals.expected_rows` = 48 × number of days in the actual window.)

### 6.5 Data-handling rules
- Never forward-fill, interpolate or impute. Missing remains missing and is reported.
- Preserve source ordering semantics; sort deterministically `(start_time, publish_time)`.
- Round only for display; processed CSV keeps 3 decimals.
- Size policy and horizon trimming per SAS §12.1; record in manifest which policy was applied.

## 7. API reference (schemas & examples)

Common: all timestamps ISO‑8601 UTC (`Z`); where a London-local rendering is useful, a sibling `*_local` string (`2026-01-15T09:00:00+00:00`, tz database offset applied) is included. All MW values rounded to 1 dp; percentages to 2 dp; `null` for undefined.

### 7.1 `GET /api/v1/health`
```json
{"status":"ok","version":"1.0.0","data_fingerprint":"a1b2c3d4e5f60718","actual_rows":1488,"forecast_rows":123456}
```

### 7.2 `GET /api/v1/meta`
```json
{
  "product":"WindLens","timezone":"Europe/London","default_cutoff":"09:00","cutoff_grid":["06:00","08:00","09:00","09:20","09:50","10:00","12:00"],
  "scope":{"mode":"decision_date","decision_dates":{"start":"2026-01-01","end":"2026-01-31"},"delivery_dates":{"start":"2026-01-02","end":"2026-02-01"}},
  "available_delivery_dates":["2026-01-02","…","2026-02-01"],
  "horizon_buckets_h":[0,6,12,18,24,36,48,72],
  "constants":{"period_minutes":30,"sign_convention":"error = forecast - actual (positive = over-forecast)","mape_min_actual_mw":500},
  "data":{"fingerprint":"…","generated_at":"…Z","source":"Elexon BMRS (FUELHH WIND, WINDFOR)","coverage":{"actual_periods":1488,"forecast_vintages":0}},
  "methodology":{"selection_rule":"latest forecast with publishTime <= cutoff","cutoff_rule":"09:00 Europe/London on the day before delivery"}
}
```

### 7.3 `GET /api/v1/decision-view?delivery_date=2026-01-15&cutoff=09:00&include_actuals=true`
```json
{
  "delivery_date":"2026-01-15",
  "cutoff":{"local":"2026-01-14T09:00:00+00:00","utc":"2026-01-14T09:00:00Z","time":"09:00","timezone":"Europe/London"},
  "points":[
    {"start_time":"2026-01-15T00:00:00Z","forecast_mw":8123.0,"publish_time":"2026-01-14T08:30:00Z","horizon_h":15.5,
     "actual_mw":7900.0,"error_mw":223.0}
  ],
  "summary":{"mean_mw":0.0,"peak_mw":0.0,"peak_time":"…Z","min_mw":0.0,"min_time":"…Z","energy_mwh":0.0,
             "max_ramp_30m_mw":0.0,"max_ramp_3h_mw":0.0,"latest_publish_time":"…Z","earliest_publish_time":"…Z",
             "horizon_h":{"min":15.0,"max":38.5}},
  "coverage":{"expected_periods":48,"with_forecast":48,"with_actual":48,"missing_forecast_periods":[]},
  "day_metrics":{"mae":0.0,"bias":0.0,"nmae_pct":0.0,"rmse":0.0,"n":48}
}
```
`include_actuals=false` omits `actual_mw`, `error_mw`, and `day_metrics` (Decision-time view must not expose hindsight data unless asked).

### 7.4 `GET /api/v1/revisions?target_time=2026-01-15T12:00:00Z&cutoff=09:00`
```json
{
  "target_time":"2026-01-15T12:00:00Z","cutoff":{"utc":"2026-01-14T09:00:00Z","time":"09:00"},
  "vintages":[{"publish_time":"2026-01-13T12:00:00Z","horizon_h":48.0,"forecast_mw":0.0,"eligible":true,"selected":false}],
  "selected_publish_time":"2026-01-14T08:30:00Z","actual_mw":0.0,
  "revision_range_mw":{"min":0.0,"max":0.0,"spread":0.0}
}
```
Include vintages up to `+6h` after the cutoff (marked `eligible:false`) to illustrate what would have been leakage.

### 7.5 `GET /api/v1/accuracy/summary?start=2026-01-02&end=2026-02-01&cutoff=09:00`
```json
{
  "window":{"start":"2026-01-02","end":"2026-02-01","delivery_days":31},"cutoff":"09:00",
  "metrics":{"n":1488,"n_missing_actual":0,"n_missing_forecast":0,"mean_actual_mw":0.0,
    "mae_mw":0.0,"rmse_mw":0.0,"bias_mw":0.0,"nmae_pct":0.0,"wape_pct":0.0,"mape_pct":0.0,"mape_n":0,
    "p50_abs_mw":0.0,"p90_abs_mw":0.0,"p95_abs_mw":0.0,"p5_err_mw":0.0,"p50_err_mw":0.0,"p95_err_mw":0.0,
    "over_forecast_share":0.0,"shortfall_mean_mw":0.0,"shortfall_p90_mw":0.0,"shortfall_p95_mw":0.0,"shortfall_max_mw":0.0,
    "correlation":0.0},
  "baseline":{"name":"persistence_last_actual_at_cutoff","mae_mw":0.0,"skill":0.0,"n":0},
  "horizon_h":{"min":15.0,"mean":0.0,"max":38.5}
}
```

### 7.6 Other accuracy endpoints (shape)
- `/accuracy/daily` → `{"days":[{"delivery_date":"…","n":48,"mae_mw":…,"bias_mw":…,"rmse_mw":…,"max_abs_mw":…,"shortfall_p90_mw":…,"mean_actual_mw":…}]}`
- `/accuracy/by-horizon` → `{"buckets":[{"from_h":0,"to_h":6,"label":"0–6 h","n":…,"mae_mw":…,"bias_mw":…,"rmse_mw":…,"nmae_pct":…}],"decision_band_h":{"min":15.0,"max":38.5},"dropped_negative_horizon":0}`
- `/accuracy/by-hour` → `{"hours":[{"hour":0,"n":62,"mae_mw":…,"bias_mw":…,"rmse_mw":…,"shortfall_p90_mw":…}]}`
- `/accuracy/by-level` → `{"basis":"actual","bins":[{"from_mw":…,"to_mw":…,"label":"Q1 (lowest)","n":…,"mae_mw":…,"bias_mw":…,"nmae_pct":…}]}`
- `/accuracy/distribution` → `{"histogram":[{"from_mw":-3000,"to_mw":-2500,"count":…}],"quantiles":{"p5":…,"p50":…,"p95":…,"shortfall_p90":…},"scatter":[{"forecast_mw":…,"actual_mw":…}]}` (scatter downsampled deterministically to ≤ 1,500 points).
- `/accuracy/worst?n=5&metric=mae` → `{"days":[{"delivery_date":"…","mae_mw":…,"bias_mw":…,"max_abs_mw":…,"max_abs_time":"…Z"}],"periods":[{"start_time":"…Z","forecast_mw":…,"actual_mw":…,"error_mw":…}]}`
- `/accuracy/cutoff-sensitivity` → `{"rows":[{"cutoff":"06:00","n":…,"mae_mw":…,"bias_mw":…,"shortfall_p90_mw":…,"mean_horizon_h":…,"coverage_pct":…}]}`
- `/risk/buffer?levels=0.5,0.75,0.9,0.95` → `{"basis":"in_sample","overall":[{"level":0.9,"buffer_mw":…}],"by_hour":[{"hour":0,"buffers":[{"level":0.9,"buffer_mw":…}]}],"n":…}`
- `/risk/backtest?level=0.9&min_history_days=7` → `{"basis":"walk_forward","level":0.9,"outcome_lag_days":2,"evaluated_days":…,"skipped_days":[…],"coverage":0.0,"target":0.9,"mean_buffer_mw":0.0,"days_with_breach_share":0.0,"daily":[{"delivery_date":"…","buffer_mw":…,"coverage":…}]}`

### 7.7 Errors (RFC 7807)
```json
{"type":"https://windlens/errors/out-of-scope","title":"Delivery date out of scope","status":404,
 "detail":"2026-03-01 is outside 2026-01-02..2026-02-01","instance":"/api/v1/decision-view","valid_range":{"start":"2026-01-02","end":"2026-02-01"}}
```
422 includes `errors:[{loc,msg,type}]`.

### 7.8 Parameter validation rules
`delivery_date`: ISO date in scope. `cutoff`: `HH:MM`, 00:00–23:59, minute granularity. `start ≤ end`, both in scope. `bins`: 3–10. `levels`: each in (0,1). `n`: 1–20. Unknown params ignored (documented) or rejected with 422 (choose **reject**, `extra="forbid"` on query models).

## 8. Metric reference

Let `e = f − a`, `n` = rows with both forecast and actual.

| Metric | Formula | Unit | Interpretation / caveat |
|--------|---------|------|--------------------------|
| MAE | `mean(|e|)` | MW | Typical magnitude of miss |
| RMSE | `sqrt(mean(e²))` | MW | Penalises large misses; RMSE ≥ MAE |
| Bias | `mean(e)` | MW | + = systematic over-forecast |
| nMAE | `MAE / mean(a) × 100` | % | Scale-free; depends on period's mean output |
| WAPE | `Σ|e| / Σa × 100` | % | Same as nMAE if same row set; keep one headline (nMAE) |
| MAPE (guarded) | `mean(|e|/a)` for `a ≥ 500` | % | Unstable near zero → guarded and flagged |
| P50/P90/P95 |e| | linear-interpolated quantiles | MW | "9 of 10 half-hours miss by less than P90" |
| P5/P50/P95 e | quantiles of signed error | MW | Tail asymmetry |
| Over-forecast share | `mean(e > 0)` | % | Direction frequency |
| Shortfall stats | on `max(0, e)` | MW | Buyer's costly side; P90 shortfall ≈ buffer for 90% |
| Correlation | Pearson(f, a) | — | Shape agreement, insensitive to bias |
| Skill | `1 − MAE_f/MAE_p` | — | vs persistence baseline |
| Buffer B_p | `Q_p(e)` | MW | Over-forecast margin exceeded (1−p) of time |
| Coverage | `mean(a ≥ max(0, f − B_p))` | % | Back-test reliability |
| Energy | `Σ f × 0.5` | MWh | Daily energy equivalents |
| Ramp | `max |f_t − f_{t−k}|` | MW | k=1 (30 min) and k=6 (3 h) |

**Quantile method:** NumPy `np.percentile(..., method="linear")` everywhere (domain, tests, JS display must not recompute).
**Rounding:** none inside domain; API rounds at serialisation; tests compare with tolerances (`1e-9` domain, `0.05` MW API).
**Aggregation hierarchy:** metrics over *periods* pooled across the window (not average of daily metrics) unless the endpoint is explicitly per-day.
**Statistical honesty:** periods within a day are strongly autocorrelated; effective sample size ≈ number of days for tail estimates. Wording must reflect this ("based on 31 days").

## 9. Selection logic: edge-case catalogue

| # | Case | Expected behaviour |
|---|------|--------------------|
| E1 | Vintage published exactly at the cutoff | **Included** |
| E2 | Vintage published 1 s after cutoff | Excluded |
| E3 | Several eligible vintages | The one with max `publish_time` |
| E4 | Same `(start_time, publish_time)` twice | Deduped upstream; selection still unique |
| E5 | No eligible vintage for a target | Target absent from Selected; counted in coverage; UI gap |
| E6 | Target at 00:00 on D vs 23:30 on D | Same cutoff (D−1 09:00) |
| E7 | Delivery day crossing DST (23- or 25-hour day) | Day boundaries by London local date; 46/50 periods; no crash; (not in January but tested) |
| E8 | Cutoff at 00:00–01:59 on DST change day | `nonexistent="shift_forward"`; ambiguous raises typed error |
| E9 | Publish after delivery start (post-hoc) | Never selected for decision views; counted but ignored in horizon analysis if `horizon_h < 0` |
| E10 | Actual missing for selected target | Row kept in Decision view with `actual_mw=null`; excluded from metrics; counted |
| E11 | Actual present, forecast missing | Excluded from metrics; counted in `n_missing_forecast` |
| E12 | Cutoff later than delivery start (e.g., 23:59 on D−1 → fine; user cannot set D-day cutoffs) | Allowed range 00:00–23:59 on D−1 only |
| E13 | Forecast values NaN/negative | NaN dropped at ingestion with count; negative → hard validation error |
| E14 | Delivery date out of scope | 404 problem+json |
| E15 | Cutoff changes → different vintages | Results differ deterministically; cache keyed by cutoff |
| E16 | Increase cutoff | Selected `publish_time` is non-decreasing per target (property test) |
| E17 | `scope_mode=delivery_date` | Delivery days Jan 1–31; ingestion window already covers (publish ≥ 2025‑12‑30) |

## 10. UI/UX & chart design reference

### 10.1 Layout grid and spacing
12-column grid, max content width 1280 px, 24 px gutters (16 px mobile). Spacing scale 4/8/12/16/24/32/48. Cards: 12 px radius, 1 px border, subtle shadow in light mode only.

### 10.2 Typography
System UI font stack (no webfont dependency for performance); sizes: 12 (meta), 14 (body), 16, 20 (card titles), 28 (KPIs), 32 (page h1); tabular numerals (`font-variant-numeric: tabular-nums`) for all numbers.

### 10.3 Colour tokens (tune for AA contrast)
| Token | Light | Dark | Use |
|-------|-------|------|-----|
| `--forecast` | #1D4ED8 | #60A5FA | Forecast line |
| `--actual` | #111827 | #E5E7EB | Actual line |
| `--over` | #C2410C | #FB923C | Over-forecast / shortfall |
| `--under` | #0F766E | #2DD4BF | Under-forecast |
| `--band` | rgba(245,158,11,.22) | rgba(245,158,11,.28) | Risk band |
| `--bg`/`--surface`/`--text`/`--muted`/`--border` | neutral set | neutral set | Chrome |
Use dashed vs solid and direct labels so meaning never depends on colour alone.

### 10.4 Component specs
- **Decision banner:** `role="status"`; shows cutoff (local, with UTC in `title`), latest vintage time, horizon range, coverage; amber state when coverage < 100%.
- **KPI card:** label, value (28 px), unit, one-line context (e.g., "vs 7,812 MW avg actual"). Tooltip with definition.
- **ForecastChart:** X = time (London), Y = MW starting at 0; forecast line 2 px; actual 2 px dark; risk band area; demand dashed grey line; residual area hatched; cutoff not shown on X (all points share a cutoff) — banner explains. Tooltip: time, forecast, vintage publish time, horizon; hindsight adds actual & error.
- **VintageStrip:** 48 cells coloured by horizon (sequential scale), tooltip shows publish time.
- **HorizonChart:** columns (MAE) + line (bias) share Y axis; decision band shaded with label "Your decision window 15–39 h".
- **HourChart:** 24 bars (MAE) with bias markers.
- **Distribution:** histogram with vertical lines at P5/P50/P95; shortfall region shaded `--over`.
- **Scatter:** forecast (x) vs actual (y), equal axes, 1:1 line, opacity 0.35.
- **Cutoff sensitivity:** small multiples or table with sparkline; highlight the active cutoff.
- **Risk panel:** level selector (P50/P75/P90/P95), buffer value, back-test coverage vs target as horizontal bars; text: "In back-test, actual wind met or exceeded the risk-adjusted forecast in X% of half-hours (target 90%)."
- **Tables:** sticky header, right-aligned numbers, zebra rows, sortable with `aria-sort`.
- **States:** skeleton with exact layout heights to avoid CLS; empty states have explanation + action.

### 10.5 Interaction rules
Changing cutoff/date updates URL and shows a non-blocking loading indicator on the affected card only; previous data remains visible (`keepPreviousData`). Keyboard: `←/→` change day when the date control or page body is focused (don't hijack when typing). Focus order follows visual order. Dialogs trap focus and restore it.

### 10.6 Dynamic insight copy (templates in `lib/insights.ts`)
- Horizon: "Error grows from **{a} MW** at {bucket1} to **{b} MW** at {bucketN} (**{x}×**)."
- Hour: "Largest average miss at **{HH:00}** ({v} MW); smallest at **{HH:00}** ({w} MW)."
- Direction: "Wind was over-forecast in **{p}%** of half-hours; the P90 shortfall is **{s} MW**."
- Cutoff: "Moving the decision from 09:00 to 06:00 changes MAE by **{Δ} MW** (**{Δ%}%**)."
All values from API; formatters from `lib/format.ts`; unit-tested with fixtures.

### 10.7 Accessibility checklist
Contrast ≥ 4.5:1 (3:1 large text/graphics); focus visible; no keyboard traps; chart alt text summarising min/max/trend; tables alternative; `prefers-reduced-motion`; zoom to 200% without loss; touch targets ≥ 44 px; form labels; error messages tied via `aria-describedby`; language `lang="en-GB"`.

## 11. Testing strategy & catalogue

**Pyramid:** many fast domain unit tests → API contract tests → few UI component tests → thin e2e smoke.

| Layer | Tooling | What | Gate |
|-------|---------|------|------|
| Domain unit | pytest, Hypothesis | Selection, cutoff, metrics, risk, baseline, horizon | ≥ 90% line+branch |
| Ingestion | pytest, respx/pytest-httpx | Retry, split, normalise, validate, idempotence | pass |
| API contract | FastAPI TestClient | Status, schema, errors, caching, CSV, determinism, recompute equality | pass |
| Data audits | pytest on real snapshot | No leakage; 48 periods/day; fingerprint matches manifest | pass |
| Front-end unit | Vitest | `lib/*` formatting, insights, URL state | ≥ 70% |
| Component | RTL + MSW + axe | Pages and key components, states | pass, 0 serious a11y |
| e2e smoke | Playwright | desk→lab→revisions (desktop+mobile), no console errors | pass (P1) |
| Non-functional | Lighthouse, timing script | S2, S7 | meet targets |
| Docker/deploy | shell scripts | Smoke & verify | pass |

**Test data:** tiny hand-made frames (documented in test docstrings with the arithmetic); one "golden day" fixture (48 periods, 3 vintages each) whose expected outputs are committed JSON; real-snapshot tests marked `@pytest.mark.snapshot`.
**Mutation sanity:** manually flip `<=` to `<` in selection and ensure at least one test fails (record in `docs/AUDIT.md`).
**Flakiness:** none allowed; no network in tests; fixed seeds; frozen "now".

## 12. Deployment reference

### 12.1 Docker (local/CI)
See IMPLEMENTATION Phase 7. Port map: API 8000, web 8080. `docker compose logs -f api` for logs. Rebuild after data/code changes: `docker compose up --build`.

### 12.2 Vercel (primary)
1. Push repo to GitHub (public, anonymous name).
2. Vercel → Add New Project → import repo. Framework: **Other**. Root directory: repo root. Build/Output come from `vercel.json`.
3. Environment: none required. Python runtime picks `api/index.py` + root `requirements.txt`.
4. Settings → **Deployment Protection**: disable (or "Only Preview" if production must be public) so the production URL needs no login. Verify in incognito.
5. Deploy; run `scripts/verify_deploy.sh https://<project>.vercel.app`.
6. Check function logs for cold-start time and bundle size; if size error → apply ADR-007.
CLI alternative: `npm i -g vercel && vercel --prod` (human logs in).

### 12.3 Heroku (fallback)
Create `heroku.yml` and a combined Dockerfile that copies `frontend/dist` into the backend image and mounts it via `StaticFiles` at `/` (API remains at `/api`). Steps: `heroku create <anon-name>`; `heroku stack:set container`; `git push heroku main`. Note Heroku has no free tier; Vercel remains primary.

### 12.4 Config reference (env vars; all optional)
| Var | Default | Meaning |
|-----|---------|---------|
| `DATA_DIR` | `<repo>/data` | Location of `processed/` |
| `DEFAULT_CUTOFF` | `09:00` | Default decision cutoff (London) |
| `SCOPE_MODE` | `decision_date` | or `delivery_date` |
| `SCOPE_START` / `SCOPE_END` | `2026-01-01` / `2026-01-31` | Inclusive |
| `CUTOFF_GRID` | `06:00,08:00,09:00,09:20,09:50,10:00,12:00` | Sensitivity grid |
| `MAPE_MIN_ACTUAL_MW` | `500` | MAPE guard |
| `MIN_HISTORY_DAYS` | `7` | Back-test warm-up |
| `OUTCOME_LAG_DAYS` | `2` | Leakage guard for walk-forward |
| `CORS_ORIGINS` | localhost dev origins | Comma-separated |
| `LOG_LEVEL` | `INFO` | Logging |

## 13. Runbooks & troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Elexon 400 on stream call | Wrong param names / range too large | Check spec; reduce chunk to 1 day (client auto-splits) |
| Elexon 429/5xx | Rate limit/outage | Backoff; rerun `make ingest` (idempotent) |
| Empty WINDFOR for a day | Publish window mismatch | Verify `publishDateTimeFrom/To` use UTC `Z`; widen margin |
| Fewer than 48 forecast points for a delivery day | No eligible vintage before cutoff for some targets | Check cadence in quality report; this is a legitimate gap — report, don't fill |
| Selected horizons look wrong (negative) | Using wrong time column or timezone | Confirm UTC dtype; `start_time − publish_time` |
| Metrics differ between API and notebook | Different row set (missing handling) or sign | Use shared domain functions only |
| Vercel 404 on `/api/...` | Rewrite/entrypoint mismatch | Ensure `/api/(.*)` → `/api/index`; FastAPI routes include `/api` prefix |
| Vercel 500 import error | Path/`sys.path` or missing dep | Check `api/index.py` path insertion and root `requirements.txt` |
| Vercel "bundle too large" | pandas/uvicorn/extras | Remove unused deps; ADR-007 fallback |
| Vercel URL asks for login | Deployment Protection on | Disable for production |
| CORS errors in dev | Origin not allowed | Add to `CORS_ORIGINS` or use Vite proxy |
| Docker web 502 | API not healthy / wrong upstream | `docker compose logs api`; confirm service name `api` |
| Charts blank | Empty data or dimension 0 container | Ensure parent has explicit height |
| Time off by one hour in UI | Browser-local formatting | Use `date-fns-tz` with `Europe/London` |
| Types stale | OpenAPI changed | `make types` and commit |

## 14. 100/100 self-scoring rubric (inferred; use for the final audit)

| Area (pts) | Criterion | Evidence required | Full marks when |
|-----------|-----------|-------------------|-----------------|
| **Video (30)** | Within 10:00, two parts, each ≤5:00 overview | Timed script; final upload length | Both parts present, clear audio, ≤ 9:50 total |
| | Part 1 impresses client | Script + demo | Starts with the problem, shows decision-time view, quantified risk, buffer, honest caveats; ≥ 5 numeric insights |
| | Part 2 enables review | Script + repo | Architecture, algorithm, tests, practices, trade-offs, next steps |
| **Analysis (25)** | Correct vintage selection | Code + tests + UI explanation | Cutoff-based, inclusive boundary, no leakage, tested, explained |
| | Right metrics | API/UI | MAE, RMSE, bias, % error, percentiles, shortfall, horizon/hour/level breakdowns |
| | Insight & decision relevance | INSIGHTS.md, UI | Risk buffer + back-test + sensitivity, interpreted for buyers |
| | Assumptions explicit | Methodology | Cutoff, scope, sign, normalisation stated and configurable |
| **Product/UI (15)** | Clarity & hierarchy | UI | Time-to-insight < 30 s; clean layout; consistent terms |
| | Charts quality | UI | Correct axes/units, accessible, table alternatives |
| | Robustness | UI | Loading/empty/error states, responsive, no console errors |
| | Accessibility | axe/Lighthouse | ≥ 95 a11y, keyboard operable |
| **Engineering (10)** | Architecture & separation | Repo | Layered, pure domain, typed |
| | Tests & CI | CI | Meaningful tests, coverage gates, green CI |
| | Code quality | Review | Lint/type clean; small functions; docs |
| **Deploy/Docker (10)** | Docker works first try | Smoke | Compose up; healthchecks |
| | Live deployment | URL | Public, incognito OK, all features work |
| **README/compliance (10)** | README completeness | README | Directory guide, start steps, live link, AI disclosure |
| | Repo hygiene | Repo | Anonymous name/metadata, clean history, no junk |
| | Submission readiness | FORM_ANSWERS | All URLs verified, ≤ 16 h noted |
Penalties to avoid: any anti-pattern in MASTER_PROMPT §8.

## 15. Governance

### 15.1 Risk register (living)
See PRD §13; add during build: bundle size outcome, Elexon limits discovered, forecast cadence, any data gaps found (with counts).

### 15.2 Quality gates
Phase exit requires: lint, types, tests, smoke, docs updated, checklist ticked. CI is the final arbiter; no merging with red CI.

### 15.3 Change control
Any change to definitions (cutoff default, sign convention, metric formulas, scope) requires: ADR entry, updates to PRD §6, SAS §7/§14, METHODOLOGY, tests, UI text, and re-generation of INSIGHTS. Search for all occurrences (`grep -R "09:00"`).

### 15.4 Definition of "no leakage"
For every displayed decision-time number, the underlying forecast has `publish_time ≤ cutoff_utc`. Actuals are shown only in Hindsight mode and in accuracy analyses (evaluation), never mixed into a decision-time computation (risk buffers in walk-forward use outcomes only from days ≤ d − lag).

## 16. FAQ of ambiguities (rulings)

1. **Why 09:00?** Safe assumption before morning gate closures; configurable; sensitivity shown. Never claim it is the client's cutoff.
2. **Why delivery days Jan 2–Feb 1?** Decisions in January → deliveries the following day. Config switch provides the other reading.
3. **Should I evaluate only the selected vintage or all vintages?** Decision-time metrics use the selected vintage; the horizon chart uses all vintages (to show error growth) with the decision window highlighted.
4. **Percent error relative to what?** Mean actual in the evaluated set (no capacity data allowed).
5. **How to handle zero or tiny actuals in % errors?** Guarded MAPE; headline % uses nMAE.
6. **Do I show MWh?** Yes for daily energy; MW elsewhere.
7. **Is demand data allowed?** No. The what-if uses a user-entered number only.
8. **What if WINDFOR vintages don't exist for some targets before the cutoff?** Leave missing; report coverage.
9. **UTC or London time in the UI?** London local primary; UTC in tooltips. In January they coincide, but code must not assume it.
10. **Do I need a database?** No — snapshot files; ADR-005.
11. **Can I fetch from Elexon in the browser or on each request?** No (ADR-004).
12. **Which chart library?** Recharts (ADR-008); do not switch mid-build.
13. **What if Vercel can't run pandas within limits?** ADR-007 fallback; document the measured numbers.
14. **Heroku instead of Vercel?** Only if Vercel blocked; follow §12.3.
15. **How long should the video be?** ≤ 10:00 total; script targets ≤ 9:30.
16. **Where to mention AI tools?** README "AI assistance disclosure" (mandatory) and form answers.
17. **Can I use AI-generated code?** Yes, disclosed; the human must understand and be able to explain every part (video Part 2).
18. **What if two WINDFOR rows share `startTime` and `publishTime` but differ in `generation`?** Keep the last in source order; log count in quality report (anomaly).
19. **Do I compute accuracy for horizons beyond what's available at decision time?** Only in the horizon chart; not in headline metrics.
20. **Is "nowcast" accuracy relevant?** Context only (shows 0–6 h bucket); not decision-relevant.
21. **Does the anonymous repo name make the submission anonymous?** No — it only covers the repo's text contents and commit metadata. The GitHub account that owns the repo, the Vercel project URL/subdomain, and anything visible or audible in the recorded video are separate, unchecked vectors. See `VERIFICATION_GATE.md §3–§4`; this needs an explicit human decision, not a default.
22. **What exactly does the submission form ask for?** This document set doesn't know — the brief's hyperlink to it didn't carry a working URL through. `docs/FORM_ANSWERS.md` is a best-effort draft against the fields the brief implies; the human must open the real form and reconcile before submitting (`VERIFICATION_GATE.md §3` H9).

## 17. Checklists

These are quick-reference subsets. `VERIFICATION_GATE.md` is the authoritative, evidence-based version — it's the one that decides whether a tick here actually counts.

### 17.1 Pre-commit
- [ ] ruff/eslint/prettier pass · [ ] mypy/tsc pass · [ ] tests pass · [ ] no secrets · [ ] no identifying info · [ ] commit message conventional with FR IDs

### 17.2 Pre-deploy
- [ ] Snapshot fingerprint matches manifest · [ ] confirmed built from a real Elexon pull, not fixtures (S8) · [ ] `make lint typecheck test` · [ ] Docker smoke · [ ] `vercel.json` rewrites verified · [ ] Deployment Protection off · [ ] `verify_deploy.sh` green · [ ] Lighthouse run

### 17.3 Pre-record (human)
- [ ] Script read twice, timed ≤ 9:30 (cross-check against the word-count estimate in `VERIFICATION_GATE.md §2.5`, don't rely on the stopwatch alone on the first pass) · [ ] Browser: clean profile, 1080p, zoom 110%, bookmarks hidden, notifications off · [ ] Demo days chosen (a typical day; a bad day; a big-ramp day) from `INSIGHTS.md` · [ ] Tabs preloaded (app, repo, Swagger, key files) · [ ] Mic test
- Anonymity on screen, checked explicitly (not "no personal info on screen" from memory — `check_anonymity.sh` cannot see any of this): [ ] terminal prompt shows no real username/hostname · [ ] no file path on screen contains a real name (clone under a neutral path) · [ ] IDE title bar / recent-projects list clean · [ ] browser profile name, avatar, and autofill suggestions are neutral · [ ] desktop wallpaper, dock/taskbar, and notification banners are neutral · [ ] a decision has been made (and is fine with the human) about whether a recognisable voice counts as identifying

### 17.3b Post-record content QA (human — new; §17.4 only checked length and playback, not content)
Watch the finished upload once, end to end, against `docs/VIDEO_SCRIPT.md` and the rubric in `ENGINEERING_REFERENCE §14`:
- [ ] All ≥ 5 numeric insights promised in Part 1 were actually **spoken**, not just visible on screen
- [ ] Part 2 actually names: architecture/layering, the selection algorithm + its tests, CI, Docker, deployment, and at least one trade-off / next step
- [ ] No section overran enough to push the total past 10:00
- [ ] Audio is intelligible throughout; no dead air longer than a couple of seconds

### 17.4 Pre-submit (human)
- [ ] Repo public, anonymous name, README renders, CI green · [ ] GitHub account/URL and Vercel subdomain checked for identity leakage, not just repo text (`VERIFICATION_GATE.md §3` H2/H5) · [ ] Live URL works in **incognito** · [ ] YouTube **unlisted**, plays in incognito, length ≤ 10:00, 17.3b complete · [ ] README has live link & AI disclosure · [ ] Form fields reconciled against the **real** submission form, not assumed from `FORM_ANSWERS.md` alone (`VERIFICATION_GATE.md §3` H9) · [ ] Time spent is the human's actual hours, honestly stated — not a copy of the 16 h scope cap (`VERIFICATION_GATE.md §5`) · [ ] Submit and screenshot confirmation

## 18. Insight-writing & wording rules

1. Quantify: "MAE 612 MW (7.9% of average output)", never "pretty accurate".
2. State basis: "Based on 31 delivery days (Jan 2–Feb 1, 2026), forecasts available at 09:00 on D−1."
3. Distinguish **in-sample** buffer from **back-tested** coverage.
4. Avoid causal claims (storms, weather regimes) unless computed from the data (e.g., "largest 3-hour ramp on 14 Jan: 4,200 MW").
5. Use buyer language: "over-forecast", "shortfall", "buffer".
6. Always include units and the sign convention near error charts.
7. Prefer ranges and caveats to point promises: "~X MW buffer would have covered ~Y% of half-hours in back-test".
8. Never present results as financial advice or price impact.

## 19. Appendices

### 19.1 Command cheat-sheet
```
make setup | ingest | verify-snapshot | lint | typecheck | test | types | insights | dev | up | smoke
python -m app.ingestion.cli run --force
pytest -m "not snapshot" -q          # fast loop
pytest -m snapshot -q                # audits on real data
npx vitest --run --coverage          # frontend
bash scripts/verify_deploy.sh https://<project>.vercel.app
```

### 19.2 Worked example (use in Methodology page; recompute with real numbers)
Delivery day **15 Jan 2026**, cutoff **09:00** → cutoff instant **14 Jan 2026 09:00 GMT**. For the 12:00 target, vintages published at 14 Jan 06:00, 07:00, 08:00, **09:00 (selected, boundary inclusive)**, 10:00, 11:00… The 10:00 and later vintages are shown greyed as "not available at decision time". Horizon of selected vintage: 27 h. If the forecast is 8,500 MW and the actual 7,900 MW, error = +600 MW (over-forecast, shortfall 600 MW).

### 19.3 Reference algorithm (loop-based, for the independent test oracle)
```python
def reference_select(rows, cutoff_for_target):
    best = {}
    for start, publish, mw in rows:                  # rows: iterable of tuples
        if publish <= cutoff_for_target(start):
            if start not in best or publish > best[start][0]:
                best[start] = (publish, mw)
    return best
```

### 19.4 Done-ness one-pager (print for the final audit)
Selection correct & tested ✔ · Metrics correct & tested ✔ · UI shows vintage, horizon, cutoff ✔ · Hindsight toggle ✔ · Accuracy Lab complete ✔ · Risk buffer + back-test ✔ · Methodology panel ✔ · Data-quality panel ✔ · Docker ✔ · Vercel live ✔ · CI green ✔ · README complete + AI disclosure ✔ · Anonymity ✔ · Video script ≤ 9:30 ✔ · Form answers ✔ · Incognito verification ✔
