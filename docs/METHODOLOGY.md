# Methodology

WindLens evaluates the wind forecast a day-ahead buyer could actually have used,
not the best forecast that exists after the fact. This document defines the
scope, the selection rule, every metric, the risk-buffer calculation, and the
limitations that a reader should carry into the numbers.

The generated analysis is in `docs/INSIGHTS.md`; the machine-readable payloads
are in `docs/insights.json`. The code that produces them is
`analysis/insights.py`, which imports the same domain and service modules as the
API.

## 1. Scope

| Item | Value |
|---|---|
| Brief reading | Decisions made in January 2026 |
| Decision dates | 2026-01-01 to 2026-01-31 inclusive |
| Delivery dates | 2026-01-02 to 2026-02-01 inclusive |
| London delivery days | 31 |
| Expected hourly targets | 744 |
| Default decision cutoff | 09:00 Europe/London on D-1 |
| Forecast dataset | Elexon WINDFOR, hourly |
| Actual dataset | Elexon FUELHH, `fuelType=WIND`, half-hourly averaged in pairs |
| Sign convention | `error = forecast - actual` |

The scope is configurable through `SCOPE_MODE`. The default `decision_date`
reading treats `SCOPE_START` and `SCOPE_END` as decision dates and shifts the
delivery window forward one day. Setting `SCOPE_MODE=delivery_date` reads the
same bounds as delivery dates instead. The committed analysis uses the default,
because the brief says "decisions made in January", not "deliveries in January".

## 2. Decision-time selection

For each target hour `T` on London delivery day `D`:

1. Resolve the decision cutoff `C(D)` as `D-1` at 09:00 Europe/London, converted
   to UTC. In January 2026 London is on GMT, so the cutoff is 09:00 UTC.
2. Collect every WINDFOR vintage whose `publish_time` is less than or equal to
   `C(D)`. The boundary is inclusive: a publication exactly at the cutoff is
   eligible.
3. Select the vintage with the greatest `publish_time` among those rows.
4. Compute `horizon_h = (T - publish_time) / 1 hour`.
5. Join the selected forecast to the hourly actual for `T`.

Formally:

```
P*(T, D) = argmax { p : p in V(T, D) and p <= C(D) }
horizon_h = (T - P*(T, D)) / 1h
```

`V(T, D)` is the set of publication timestamps that contain a forecast for `T`.
If no eligible vintage exists, the target is omitted from the selected frame and
counted as missing coverage. It is not filled from a later vintage, and it is not
interpolated.

The "latest ever" vintage is never used. That distinction is the product: a
revision published after the buyer's gate is hindsight, not information. The
Revisions explorer visualises the eligible and ineligible vintages for a chosen
target.

DST handling is explicit in `backend/app/domain/timeutils.py`. A nonexistent
local cutoff is shifted forward; an ambiguous local cutoff raises a configuration
error rather than silently choosing one of the two possible instants. January
2026 contains no DST transition, so the delivered numbers are unaffected.

## 3. From half-hourly actuals to hourly evaluation

WINDFOR targets are hourly. FUELHH rows are half-hourly. For target hour `T`:

```
A_T = (a(T) + a(T + 30 minutes)) / 2
```

If either half-hour is missing, `A_T` is null and the target cannot be scored.
No interpolation, forward-fill, or model-based imputation is used. In the
committed snapshot both half-hours exist for every one of the 768 hourly actuals
in the wider ingestion window, and all 744 decision-scope targets have an actual.

This averaging is the only transformation applied to actuals. It does not create
a half-hourly forecast, and it does not change the forecast publication time.

## 4. Metric definitions

Let `F_t` be the selected forecast, `A_t` the hourly actual, and
`e_t = F_t - A_t` for the `n` scored hours. Positive error means the forecast was
above outturn: the buyer expected more wind than arrived, so the position is
short. Negative error means the forecast was below outturn.

| Metric | Definition | Interpretation |
|---|---|---|
| MAE | `mean(abs(e_t))` | Average absolute miss in MW |
| RMSE | `sqrt(mean(e_t^2))` | Penalises large misses more than MAE |
| Bias | `mean(e_t)` | Signed direction; positive is over-forecast |
| nMAE | `MAE / mean(A_t) * 100` | Scale-free absolute error without installed-capacity data |
| WAPE | `sum(abs(e_t)) / sum(A_t) * 100` | Weighted absolute percentage error |
| MAPE | `mean(abs(e_t) / A_t) * 100` for `A_t >= 500 MW` | Guarded relative error; avoids dividing by near-zero output |
| P50/P90/P95 absolute error | Linear-interpolated percentiles of `abs(e_t)` | Tail size in MW |
| P5/P50/P95 signed error | Linear-interpolated percentiles of `e_t` | Directional distribution |
| Over-forecast share | `mean(e_t > 0)` | Fraction of hours with shortfall risk |
| Shortfall | `max(e_t, 0)` | Positive error only; zeros retained |
| Shortfall P90/P95/max | Percentiles and maximum of shortfall | Buffer sizing inputs |
| Correlation | Pearson correlation of `F_t` and `A_t` | Shape agreement, not calibration |
| Persistence MAE | MAE of the last complete hourly actual at the cutoff, held flat | Naive decision-time baseline |
| Skill | `1 - MAE_forecast / MAE_persistence` | Fraction of baseline MAE removed |

Percent values are in percentage points (0-100). `over_forecast_share` is a
fraction in the API and is displayed as a percentage in prose. Percentiles use
NumPy's linear interpolation. MW values are rounded once at the API boundary to
one decimal place; percentages to two decimal places.

The persistence baseline is constructed only from information available at the
cutoff: the most recent hourly actual whose one-hour window ends at or before
`C(D)`, repeated across the delivery day. It uses only the two permitted Elexon
datasets.

## 5. Worked example

Take delivery day 2026-01-15, cutoff 09:00 Europe/London on 2026-01-14, and the
target hour starting 2026-01-15T00:00:00Z.

| Step | Value |
|---|---|
| Cutoff instant | 2026-01-14T09:00:00Z |
| Selected publication | 2026-01-14T07:30:00Z (the 07:30 vintage) |
| Forecast `F` | 15,834.0 MW |
| FUELHH half-hour 00:00 | 14,602.0 MW |
| FUELHH half-hour 00:30 | 14,311.0 MW |
| Hourly actual `A` | (14,602.0 + 14,311.0) / 2 = 14,456.5 MW |
| Error `F - A` | +1,377.5 MW |
| Horizon | 16.5 h |
| Direction | Over-forecast; 1,377.5 MW of shortfall risk |

Two more rows from the same day show the direction is not a one-hour accident:

| Target (UTC) | Forecast MW | Actual MW | Error MW | Horizon h |
|---|---:|---:|---:|---:|
| 2026-01-15T09:00 | 12,576.0 | 12,193.0 | +383.0 | 25.5 |
| 2026-01-15T12:00 | 11,049.0 | 9,790.5 | +1,258.5 | 28.5 |

For the whole delivery day the selected forecast has MAE 1,041.8 MW, bias
+1,041.8 MW, and an over-forecast share of 1.0 across 24 scored hours. The day is
not the worst day in the window; it is a useful illustration because the sign is
consistent and the half-hour arithmetic is easy to check by hand.

## 6. Horizon analysis

The API's horizon table covers **every vintage in the snapshot**, not only the
selected rows. That is deliberate: it shows how error grows with lead time across
the full publication history, while the headline metrics remain decision-time
specific. The selected decision rows span 16.5 to 39.5 hours, with a mean of 28.0
hours at the default cutoff.

The horizon buckets are `0-6`, `6-12`, `12-18`, `18-24`, `24-36`, `36-48`,
`48-72` and `72+` hours. The final bucket is open-ended and is serialised with
`to_h = null`; it is not a 72-to-infinity numeric sentinel. In this snapshot no
vintage reaches the 72+ bucket, so that row has `n = 0` and null metrics. Rows
with a negative horizon are dropped from the horizon table and counted in
`dropped_negative_horizon`; a target that had already begun at publication can
never be selected for a decision.

## 7. Cutoff sensitivity

The sensitivity grid is `06:00`, `08:00`, `09:00`, `09:20`, `09:50`, `10:00`
and `12:00` Europe/London. Each row re-runs selection at that cutoff over the same
delivery window. It is a sensitivity analysis, not a causal claim: a later cutoff
can use a later vintage, but it also shortens the buyer's lead time and may not
be operationally available.

At the default 09:00 cutoff the MAE is 2,038.9 MW. The 12:00 row has the lowest
MAE at 1,901.0 MW, 6.76% below the default, but its mean horizon is 24.1 hours
instead of 28.0. The 06:00 row has MAE 2,016.1 MW. The full grid spans 137.9 MW.
The default remains 09:00 because it aligns with the 07:30 WINDFOR vintage, keeps
a realistic lead time, and the gain from waiting is modest relative to the loss
of decision time.

## 8. Risk buffer

For a risk level `p` in `(0, 1)`, the empirical buffer is the `p`-th percentile of
the signed error distribution:

```
b_p = Q_p(e)
risk_adjusted_forecast = max(0, F - b_p)
```

The buyer plans against the risk-adjusted forecast. If the buffer is 4,097.9 MW
at `p = 0.90`, the plan uses `max(0, F - 4,097.9 MW)`. This is a one-sided
shortfall buffer, not a symmetric confidence interval, because 85.0% of the
errors are positive. The buffer is subtracted from forecast generation; it is not
added to demand and it is not a weather forecast.

The in-sample buffer is an empirical quantile of the same errors used to evaluate
it, so its in-sample coverage is nominal by construction. The honest estimate is
the walk-forward back-test:

- For delivery day `d`, estimate the buffer using only delivery days on or before
  `d - 2`.
- Require at least 7 usable history days.
- For each evaluated day, compute the buffer, apply it to that day's forecasts,
  and count an hour as covered when `actual >= max(0, forecast - buffer)`.
- Report pooled hour coverage, the mean daily buffer, and the share of evaluated
  days with at least one breach.

The two-day outcome lag is deliberate. The previous day's actuals are not fully
known at 09:00 on `d - 1`, so using them would leak outcomes into the buffer. At
`p = 0.90` the walk-forward result is 86.0% coverage over 23 evaluated days (8
days skipped for insufficient history), with a mean buffer of 4,051.8 MW and
22.0% of evaluated days containing a breach. The target is 90.0%; the gap is the
out-of-sample cost of the rule, and the sample is small.

## 9. What the numbers do and do not mean

- **Decision-time, not best-case.** Every headline metric uses the latest vintage
  published at or before the cutoff. The horizon table is the only place where
  all vintages are pooled, and it is labelled as such.
- **Direct comparison, no rescaling.** WINDFOR and FUELHH WIND are compared as
  published. The +1,747.9 MW bias is retained. It may reflect a genuine forecast
  bias, a difference in the wind portfolio each series covers, or both. The
  product does not fit a correction that the brief did not authorise.
- **One month, one season.** The window is 31 delivery days in January 2026.
  It is enough to demonstrate the method, not enough to claim a seasonal or
  annual error distribution. A 23-day walk-forward sample is indicative at the
  tail, not precise.
- **Hourly resolution.** WINDFOR is hourly, so the evaluation is hourly. Intra-hour
  variability is invisible to the headline metrics; the half-hourly FUELHH pairs
  are averaged before scoring.
- **No installed-capacity normalisation.** nMAE uses mean actual output because
  capacity data is outside the two permitted datasets. A capacity-normalised
  error would answer a different question and is not computed.
- **Correlation is not calibration.** The 0.93 correlation says the forecast
  follows the shape of outturn. The bias and shortfall percentiles say it is not
  calibrated for a buyer who needs a conservative plan.
- **Snapshot, not live feed.** The app serves the committed snapshot and does not
  call Elexon at request time. `make ingest` refreshes it. The fingerprint and
  manifest timestamps make the version explicit.
- **No missing-data heroics.** Missing actuals are excluded and counted. Missing
  forecasts are omitted and counted. Nothing is imputed.

## 10. Reproducibility

```bash
make setup
make ingest             # live Elexon pull; writes data/raw and data/processed
make verify-snapshot    # re-hash processed files against the manifest
make insights           # writes docs/INSIGHTS.md and docs/insights.json
make test               # backend + frontend suites, including insight contract tests
```

The insight generator is deterministic for a fixed snapshot and configuration:
it writes no wall-clock timestamp, only the manifest timestamp. Re-running it
against the same snapshot produces byte-identical files. The contract test
`backend/tests/api/test_insights.py` compares the committed JSON with live API
payloads from the same snapshot, so a stale analysis fails the suite rather than
silently drifting.

The data-source contracts and the live-pull provenance are in
`docs/DATA_SOURCES.md`. The architectural decisions are in `docs/DECISIONS.md`.
