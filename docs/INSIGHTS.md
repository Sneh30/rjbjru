# WindLens — Insights

> **Generated artefact.** Produced by `analysis/insights.py` from the committed snapshot; do not edit by hand. Regenerate with `make insights`.
>
> Snapshot fingerprint `331dc8acb133704a` · manifest generated `2026-11-01T18:42:17Z` · source Elexon BMRS `FUELHH` (WIND) + `WINDFOR` · scope **2026-01-02 → 2026-02-01** (31 London delivery days, 744 hourly targets) · default cutoff **09:00 Europe/London on D-1**.

## Key findings

- Across **744 hourly targets**, the selected WINDFOR forecast has MAE **2,038.9 MW** and nMAE **18.07%**.
- Bias is **+1,747.9 MW**; **85.0%** of hours are over-forecast, so the error is directional shortfall risk, not just noise.
- P90 shortfall is **4,097.9 MW** and P95 is **5,283.4 MW** (maximum **6,870.0 MW**).
- The persistence baseline's MAE is **4,125.9 MW**; the forecast's skill score is **0.51**, a **50.58%** MAE reduction.
- Decision horizons are **16.5 h to 39.5 h** (mean **28.0 h**).
- The latest vintage beats the earliest available vintage: **2,038.9 MW** vs **2,422.1 MW** MAE, a **383.2 MW** / **18.79%** advantage.
- At the 0.90 risk level the in-sample buffer is **4,097.9 MW**; walk-forward coverage is **86.0%** over 23 days, with mean buffer **4,051.8 MW** and **22.0%** of days breached.
- The 12:00 cutoff has the lowest MAE (**1,901.0 MW**), **6.76%** below the 09:00 default, but it shortens mean horizon from **28.0 h** to **24.1 h**.
- Coverage is complete: **744/744** forecasts and **744/744** actuals; no missing periods, no interpolation.

## 1. Headline metrics at the default cutoff

The evaluation window is the configured decision scope: decisions taken on 2026-01-01 to 2026-01-31 deliver 2026-01-02 to 2026-02-01. Error is `forecast - actual`; positive is over-forecast and shortfall risk.

| Metric | Value |
| --- | --- |
| Scored hours | 744 |
| Mean actual output | 11,283.6 MW |
| MAE | 2,038.9 MW |
| RMSE | 2,504.8 MW |
| Bias | +1,747.9 MW |
| nMAE | 18.07% |
| WAPE | 18.07% |
| MAPE (actual ≥ 500 MW) | 22.04% |
| Median absolute error | 1,671.0 MW |
| P90 absolute error | 4,097.9 MW |
| P95 absolute error | 5,283.4 MW |
| Correlation (forecast vs actual) | 0.93 |
| Persistence baseline MAE | 4,125.9 MW |
| Forecast skill vs persistence | 0.51 |
| Missing actuals | 0 |

The central result is not that the forecast is noisy — correlation is **0.93** — but that it is biased high. The bias of **+1,747.9 MW** is **15.49%** of mean actual output, and it is larger than the median absolute miss.

## 2. Error direction and shortfall

| Direction | Hours | Share | Conditional mean |
| --- | --- | --- | --- |
| Over-forecast (error > 0) | 632 | 85.0% | 2,228.9 MW |
| Under-forecast (error < 0) | 112 | 15.0% | 966.6 MW |
| Exact | 0 | 0.0% | — |

The signed-error quantiles are P5 **-1,151.4 MW**, median **+1,592.0 MW**, and P95 **+5,283.4 MW**. The shortfall distribution (positive errors only, with zeros retained) has P90 **4,097.9 MW**, P95 **5,283.4 MW**, and a maximum of **6,870.0 MW**. The conditional mean over-forecast is **2,228.9 MW**, more than twice the conditional mean under-forecast of **966.6 MW**.

This is the buyer's problem in one line: the forecast is high in 85.0% of hours, and when it is high the miss is large. A risk buffer, not a symmetric confidence interval, is the appropriate response.

## 3. Horizon and lead time

| Horizon from publication | Rows | MAE | Bias | RMSE | nMAE |
| --- | --- | --- | --- | --- | --- |
| 0-6 h | 1,488 | 1,660.0 MW | +1,427.7 MW | 2,120.0 MW | 14.76% |
| 6-12 h | 1,488 | 1,734.5 MW | +1,502.8 MW | 2,192.4 MW | 15.32% |
| 12-18 h | 1,488 | 1,837.0 MW | +1,634.3 MW | 2,309.8 MW | 16.21% |
| 18-24 h | 1,488 | 1,949.4 MW | +1,771.8 MW | 2,424.9 MW | 17.36% |
| 24-36 h | 2,976 | 2,018.8 MW | +1,717.9 MW | 2,480.8 MW | 17.89% |
| 36-48 h | 2,945 | 2,249.8 MW | +1,905.0 MW | 2,789.2 MW | 19.95% |
| 48-72 h | 2,510 | 2,317.3 MW | +1,402.6 MW | 2,925.4 MW | 20.35% |
| 72+ h | 0 | — | — | — | — |

The table covers every vintage in the snapshot, not only the selected one. The selected decision rows span **16.5 h to 39.5 h** (mean **28.0 h**). The first populated bucket has MAE **1,660.0 MW**; the last has **2,317.3 MW**, a **39.60%** increase. No vintage reaches the 72+ h bucket in this snapshot, so that row is empty.

The all-vintage frame contains **18,080** rows; **3,697** rows with a negative horizon were dropped from the horizon table because the target had already begun at publication. They can never be selected for a decision.

## 4. Best and worst hours of the day

Best three London hours by MAE:

| Hour | Hours | MAE | Bias | Mean actual |
| --- | --- | --- | --- | --- |
| 21:00 | 31 | 1,785.6 MW | +1,544.2 MW | 11,783.2 MW |
| 22:00 | 31 | 1,792.5 MW | +1,635.8 MW | 11,691.9 MW |
| 15:00 | 31 | 1,817.5 MW | +1,247.0 MW | 11,273.4 MW |

Worst three London hours by MAE:

| Hour | Hours | MAE | Bias | Mean actual |
| --- | --- | --- | --- | --- |
| 05:00 | 31 | 2,429.9 MW | +2,358.1 MW | 10,793.3 MW |
| 03:00 | 31 | 2,413.1 MW | +2,321.7 MW | 11,024.8 MW |
| 04:00 | 31 | 2,405.2 MW | +2,334.6 MW | 10,932.6 MW |

The best hour is **21:00** at **1,785.6 MW**; the worst is **05:00** at **2,429.9 MW**. The spread is **644.3 MW** (**36.08%** of the best hour), so the intraday shape matters but does not explain the overall bias.

## 5. Wind-level analysis

| Actual-output bin | Range | Hours | MAE | Bias | nMAE |
| --- | --- | --- | --- | --- | --- |
| Q1 (lowest) | 1,711.5 MW - 7,473.5 MW | 149 | 2,027.8 MW | +1,799.3 MW | 39.57% |
| Q2 | 7,477.5 MW - 9,851.0 MW | 149 | 1,550.7 MW | +1,028.6 MW | 18.13% |
| Q3 | 9,865.5 MW - 13,671.5 MW | 149 | 1,722.1 MW | +1,148.0 MW | 14.84% |
| Q4 | 13,727.5 MW - 15,478.0 MW | 149 | 2,737.2 MW | +2,693.8 MW | 18.62% |
| Q5 | 15,482.0 MW - 17,755.5 MW | 148 | 2,157.5 MW | +2,072.0 MW | 13.10% |

The largest absolute error is in **Q4** (13,727.5 MW - 15,478.0 MW): MAE **2,737.2 MW**, bias **+2,693.8 MW**. The highest relative error is in **Q1 (lowest)** at **39.57%**, because low-output hours make the same absolute miss look larger. The largest absolute bias is in **Q4** at **+2,693.8 MW**.

## 6. Worst delivery days and demo-day picks

| Delivery day | Hours | MAE | Bias | Mean actual | Max 1 h ramp | Computed description |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-01-28 | 24 | 5,374.8 MW | +5,374.8 MW | 5,759.8 MW | 1,747.5 MW | low-wind lull (daily mean 5,759.8 MW); over-forecast in all 24 hours (bias +5,374.8 MW); max 1 h actual ramp 1,747.5 MW (top-decile ramp). |
| 2026-01-12 | 24 | 4,868.2 MW | +4,868.2 MW | 14,452.2 MW | 678.5 MW | mid-range wind (daily mean 14,452.2 MW); over-forecast in all 24 hours (bias +4,868.2 MW); max 1 h actual ramp 678.5 MW. |
| 2026-01-11 | 24 | 4,801.6 MW | +4,801.6 MW | 13,557.4 MW | 1,131.0 MW | mid-range wind (daily mean 13,557.4 MW); over-forecast in all 24 hours (bias +4,801.6 MW); max 1 h actual ramp 1,131.0 MW. |
| 2026-01-21 | 24 | 3,658.3 MW | +3,658.3 MW | 15,731.7 MW | 1,182.5 MW | strong-wind day (daily mean 15,731.7 MW); over-forecast in all 24 hours (bias +3,658.3 MW); max 1 h actual ramp 1,182.5 MW. |
| 2026-01-27 | 24 | 3,479.1 MW | +3,479.1 MW | 16,408.5 MW | 1,525.0 MW | strong-wind day (daily mean 16,408.5 MW); over-forecast in all 24 hours (bias +3,479.1 MW); max 1 h actual ramp 1,525.0 MW. |

**Demo-day picks for the video.** Typical: **2026-01-17** (MAE 1,726.8 MW, mean actual 5,647.0 MW, max 1 h ramp 837.5 MW). Bad day: **2026-01-28** (MAE 5,374.8 MW, bias +5,374.8 MW). Big-ramp day: **2026-01-08** (max 1 h actual ramp 2,395.5 MW, max 3 h ramp 5,729.5 MW, MAE 1,949.2 MW).

The worst day, **2026-01-28**, has MAE **5,374.8 MW** and bias **+5,374.8 MW**. Its computed description is: *low-wind lull (daily mean 5,759.8 MW); over-forecast in all 24 hours (bias +5,374.8 MW); max 1 h actual ramp 1,747.5 MW (top-decile ramp).*

## 7. Cutoff sensitivity

| Cutoff (D-1) | Hours | MAE | Bias | P90 shortfall | Mean horizon | Coverage |
| --- | --- | --- | --- | --- | --- | --- |
| 06:00 | 744 | 2,016.1 MW | +1,671.0 MW | 4,157.9 MW | 31.0 h | 100.00% |
| 08:00 | 744 | 2,038.9 MW | +1,747.9 MW | 4,097.9 MW | 28.0 h | 100.00% |
| 09:00 | 744 | 2,038.9 MW | +1,747.9 MW | 4,097.9 MW | 28.0 h | 100.00% |
| 09:20 | 744 | 2,038.9 MW | +1,747.9 MW | 4,097.9 MW | 28.0 h | 100.00% |
| 09:50 | 744 | 2,013.0 MW | +1,729.9 MW | 4,143.9 MW | 26.0 h | 100.00% |
| 10:00 | 744 | 2,013.0 MW | +1,729.9 MW | 4,143.9 MW | 26.0 h | 100.00% |
| 12:00 | 744 | 1,901.0 MW | +1,687.2 MW | 3,847.2 MW | 24.1 h | 100.00% |

The lowest MAE is 1,901.0 MW at 12:00, 137.9 MW (6.76%) below the 09:00 default. It shortens mean horizon from 28.0 h to 24.1 h. The grid spans 137.9 MW; the curve is flat near the default, which stays because it aligns with the 07:30 WINDFOR vintage and preserves lead time.

The full grid spans **137.9 MW** of MAE. The default row is **09:00** with MAE **2,038.9 MW**; the best row is **12:00** with **1,901.0 MW**. The interpretation is not “later is better”: the gain is modest, and it is bought with less lead time.

## 8. Vintage value: latest, earliest and persistence

| Vintage | Horizon | MAE | Bias | nMAE | Skill |
| --- | --- | --- | --- | --- | --- |
| Latest eligible | 16.5-39.5 h | 2,038.9 MW | +1,747.9 MW | 18.07% | 0.51 |
| Earliest eligible | 43.5-66.5 h | 2,422.1 MW | +1,598.9 MW | 21.47% | 0.41 |
| Persistence | — | 4,125.9 MW | — | — | 0.00 |

All three rows use the same **744** scored hours. The earliest eligible vintage is **383.2 MW** (**18.79%**) worse than the latest one. The latest forecast reduces MAE by **2,087.0 MW** (**50.58%**) against persistence; the earliest vintage still reduces it by **1,703.8 MW** (**41.30%**).

The practical reading: WINDFOR adds real information beyond persistence, and waiting for the latest eligible vintage is worth 18.79% of MAE at this cutoff. The earliest row is included to show that the gain is not an artefact of comparing against a weak baseline.

## 9. Risk-buffer calibration

| Level | In-sample buffer | In-sample coverage | Walk-forward coverage | Walk-forward mean buffer | Days with breach | Evaluated days |
| --- | --- | --- | --- | --- | --- | --- |
| 0.50 | 1,592.0 MW | 50.0% | 43.0% | 1,426.0 MW | 91.0% | 23 |
| 0.75 | 2,775.1 MW | 75.0% | 71.0% | 2,658.8 MW | 57.0% | 23 |
| 0.90 | 4,097.9 MW | 90.0% | 86.0% | 4,051.8 MW | 22.0% | 23 |
| 0.95 | 5,283.4 MW | 95.0% | 89.0% | 4,986.1 MW | 17.0% | 23 |

At level 0.90 the in-sample buffer is 4,097.9 MW. Walk-forward coverage is 86.0% over 23 evaluated days (8 skipped), with a mean buffer of 4,051.8 MW and 22.0% of days breached. The target is 90.0%; the gap is the honest out-of-sample cost, and the day count is small.

In-sample coverage is nominal by construction because the buffer is an empirical quantile. The walk-forward column is the honest estimate: each day's buffer uses only outcomes from at least two days earlier. With 23 evaluated days, treat the tail coverage as indicative rather than precise.

## 10. Data coverage and provenance

| Check | Value |
| --- | --- |
| Snapshot fingerprint | `331dc8acb133704a` |
| Manifest generated at | `2026-11-01T18:42:17Z` |
| Delivery window | 2026-01-02 → 2026-02-01 |
| Delivery days | 31 |
| Expected hourly targets | 744 |
| With forecast | 744 |
| With actual | 744 |
| Decision coverage | 100.00% |
| Missing forecasts | 0 |
| Missing actuals | 0 |
| FUELHH actual rows | 1,536 |
| FUELHH expected rows | 1,536 |
| FUELHH missing rows | 0 |
| Hourly actual rows | 768 |
| Incomplete hours | 0 |
| WINDFOR rows | 19,856 |
| WINDFOR vintages | 272 |
| WINDFOR targets | 865 |
| WINDFOR first publish | `2025-12-30T02:30:00Z` |
| WINDFOR last publish | `2026-02-01T22:30:00Z` |
| WINDFOR target range | `2025-12-29T21:00:00Z` → `2026-02-03T21:00:00Z` |
| Vintages per publish day | 8-8 |

Every one of the **744** in-scope hourly targets has a selected forecast and an actual. The two FUELHH half-hours behind each hourly actual are averaged; if either were missing the hour would be null and excluded, never interpolated. There are no missing periods in this snapshot.

The snapshot was built from live Elexon BMRS pulls, not fixtures. The manifest records the source URLs, per-chunk fetch timestamps, row counts, and SHA-256 hashes of both processed files. See `docs/DATA_SOURCES.md` for the endpoint contracts and `data/processed/manifest.json` for the full provenance record.

## Method and reproducibility

- **Unit of evaluation.** WINDFOR is hourly; FUELHH is half-hourly. Each hourly actual is the arithmetic mean of its two half-hour settlement periods. No interpolation or imputation is used.
- **Decision selection.** For each target hour, use the latest WINDFOR vintage published at or before 09:00 Europe/London on the previous London day. The cutoff is inclusive. This is a no-look-ahead rule.
- **Error sign.** `error = forecast - actual`; positive means over-forecast and shortfall risk. The risk buffer is subtracted from the forecast: `risk_adjusted = max(0, forecast - buffer)`.
- **Rounding.** MW values are rounded once at the output boundary to one decimal place; percentages to two decimal places; shares are displayed as percentages with one decimal place. The JSON retains the same rounded API values.
- **Determinism.** The output contains no wall-clock timestamp. Re-running `make insights` against the same snapshot produces byte-identical files.
- **Contract check.** `backend/tests/api/test_insights.py` compares the committed JSON payloads with live API responses, so a stale insight file fails the test suite.
