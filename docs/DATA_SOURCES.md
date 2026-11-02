# Data sources and verified contracts

This document records what was actually probed against the live Elexon BMRS
Insights Solution on 2026-11-01, before any analysis code was written. It is a
record of observed behaviour, not a copy of an assumed schema.

The serving application never calls Elexon. It reads the committed snapshot in
`data/processed/`. Ingestion is an offline, resumable command (`make ingest`).

## 1. Source identity

| Item | Value |
|---|---|
| Provider | Elexon BMRS Insights Solution |
| Base URL | `https://data.elexon.co.uk/bmrs/api/v1` |
| Dataset 1 | `FUELHH`, filtered to `fuelType=WIND` |
| Dataset 2 | `WINDFOR` |
| API key | None required for the two stream endpoints used here |
| Response shape | JSON array of objects |
| Storage timezone | UTC (`Z` suffixes), with Europe/London used for delivery days and cutoffs |
| Documentation pages | `https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream` and `https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream` |
| Old Swagger URL | `https://data.elexon.co.uk/bmrs/api/v1/swagger/v1/swagger.json` returned HTTP 404 on 2026-11-01; it is not used |

## 2. Verified endpoint contracts

### 2.1 FUELHH actual outturn

```
GET https://data.elexon.co.uk/bmrs/api/v1/datasets/FUELHH/stream
    ?settlementDateFrom=2026-01-15
    &settlementDateTo=2026-01-15
    &fuelType=WIND
```

| Parameter | Type | Required by this build | Observed behaviour |
|---|---|---|---|
| `settlementDateFrom` | ISO date | Yes | Inclusive settlement-date lower bound |
| `settlementDateTo` | ISO date | Yes | Inclusive settlement-date upper bound |
| `fuelType` | string | Yes | `WIND` returns only wind rows; provider casing accepted as documented |
| `settlementPeriodFrom` | integer | No | Not used; the whole day is requested and filtered locally |
| `settlementPeriodTo` | integer | No | Not used |
| `format` | string | No | JSON is the default and is the only format consumed |

Observed response fields: `dataset`, `publishTime`, `startTime`,
`settlementDate`, `settlementPeriod`, `fuelType`, `generation`.

In January 2026 each settlement date returned 48 half-hour rows for WIND.
`generation` was numeric in every fetched row. Non-wind rows are filtered again
during normalisation, so the endpoint filter is defence in depth rather than the
only guard.

### 2.2 WINDFOR forecast vintages

```
GET https://data.elexon.co.uk/bmrs/api/v1/datasets/WINDFOR/stream
    ?publishDateTimeFrom=2026-01-14T00:00:00Z
    &publishDateTimeTo=2026-01-14T23:59:59Z
```

| Parameter | Type | Required by this build | Observed behaviour |
|---|---|---|---|
| `publishDateTimeFrom` | ISO datetime, UTC | Yes | Inclusive publication lower bound |
| `publishDateTimeTo` | ISO datetime, UTC | Yes | Inclusive publication upper bound |
| `format` | string | No | JSON is the default |

Observed response fields: `dataset`, `publishTime`, `startTime`, `generation`.
There is no `settlementPeriod`, no `fuelType`, and no separate target-date field.

The observations that shaped the implementation:

1. **WINDFOR is hourly, not half-hourly.** Each vintage contains 73 hourly
   targets. The task brief's example language implied half-hourly wind data; the
   live feed does not behave that way. The implementation follows the live feed.
2. **Eight publications per UTC publish day.** Across the 34 fetched publish
   days, each day contains 8 vintages and 8 x 73 = 584 rows. The regular
   publication times observed are 02:30, 04:30, 07:30, 09:30, 11:30, 15:30,
   18:30 and 22:30 UTC.
3. **Ad hoc publications exist.** On 2026-01-15 the 11:30 vintage was replaced
   by a 12:25 publication. The selection rule uses publication timestamps, not
   a hard-coded list of clock times, so the ad hoc vintage is handled correctly.
4. **Targets extend beyond the publication day.** A vintage published on
   D-1 covers the following delivery day and beyond; horizons in the snapshot
   reach roughly 16.5 to 39.5 hours for the selected decision rows.
5. **The 09:00 Europe/London cutoff selects the 07:30 UTC vintage in January.**
   The cutoff is exclusive of anything published later; the boundary itself is
   inclusive.
6. **`generation` was numeric in every fetched WINDFOR row.** No nulls or
   negative values were observed in the fetched window; normalisation still
   drops unparseable values rather than imputing them.

### 2.3 Resolution mismatch and how it is handled

WINDFOR is hourly. FUELHH is half-hourly. The evaluation therefore does one
thing only: for each target hour, average the two FUELHH half-hours that start at
the top of the hour and at half past. If either half-hour is missing, the hour is
null and is excluded from metrics, never interpolated. This is recorded in the
manifest policy and implemented in `backend/app/data/loader.py`.

The model does not resample WINDFOR to half-hours, because that would invent
information that was never published.

## 3. Pull window and snapshot provenance

The ingestion CLI requests day-sized chunks and stores the raw responses in
`data/raw/` (not committed). The committed snapshot is built from those chunks:

| Dataset | Raw chunks | Rows fetched | Snapshot rows | Missing rows |
|---|---:|---:|---:|---:|
| FUELHH WIND | 32 daily files, 2026-01-01 to 2026-02-01 | 1,536 | 1,536 half-hours | 0 |
| WINDFOR | 34 publish-day files, 2025-12-30 to 2026-02-01 | 19,856 | 19,856 forecast rows | 0 |

Observed fetch timestamps:

| Dataset | First chunk fetched | Last chunk fetched |
|---|---|---|
| FUELHH | 2026-11-01T18:10:28Z | 2026-11-01T18:10:42Z |
| WINDFOR | 2026-11-01T18:10:43Z | 2026-11-01T18:10:58Z |

Snapshot identity:

| Check | Value |
|---|---|
| Manifest generated at | `2026-11-01T18:42:17Z` |
| Data fingerprint | `331dc8acb133704a` |
| `actuals.csv.gz` SHA-256 | `587408a3105a7405ed66bcd7ad7386d1c6f1ad11d22fbf151b610e4963d5183d` |
| `forecasts.csv.gz` SHA-256 | `31c554443803a5a59ec9dd47fcc772c50750e6e1c480a819c911d4209930a42d` |

The per-chunk URLs, parameters, row counts, SHA-256 hashes and fetch timestamps
are in `data/processed/manifest.json`. `make verify-snapshot` re-hashes the two
processed files and fails if they no longer match the manifest.

Coverage in the decision scope:

| Check | Value |
|---|---:|
| Decision dates | 2026-01-01 to 2026-01-31 |
| Delivery dates | 2026-01-02 to 2026-02-01 |
| London delivery days | 31 |
| Expected hourly targets | 744 |
| Targets with a selected forecast | 744 |
| Targets with an actual | 744 |
| Missing forecasts | 0 |
| Missing actuals | 0 |

The raw sample fixtures under `backend/tests/fixtures/` are deliberately small
(4 rows each) and are test inputs only. They are not the source of any product
number. Every number in `docs/INSIGHTS.md` comes from the committed processed
snapshot, which came from the live pulls recorded above.

## 4. Why the comparison is direct

WINDFOR is the forecast series the brief permits. FUELHH WIND is the outturn
series the brief permits. The product compares them directly and reports the
error that results, including a large positive level bias. It does **not**
rescale WINDFOR to FUELHH, fit a bias correction, shift timestamps to search for
a better match, or substitute a different wind series.

This is the honest choice for a decision-support product: the buyer would have
used the published WINDFOR number, so the published number is what gets scored.
A level difference between the two series is part of the measured risk, not
something to hide with a calibration that the brief did not authorise.

The consequence is documented in `docs/METHODOLOGY.md` and in the UI: the
+1,747.9 MW bias is large, and the product treats it as shortfall risk rather
than as a reason to distrust the whole exercise. A future iteration should
investigate whether the two series cover the same wind portfolio and whether a
capacity-normalised comparison is possible within the client's data policy.

## 5. Reproducing the snapshot

```bash
make setup          # backend venv + frontend dependencies
make ingest         # live fetch, normalise, validate, write data/processed/
make verify-snapshot
make insights       # regenerate docs/INSIGHTS.md and docs/insights.json
```

`make ingest` reuses existing raw chunks unless they are removed. To rebuild
from the committed cache without network access:

```bash
make build-snapshot
make verify-snapshot
```

The manifest records absolute source URLs and per-chunk hashes, so a changed
upstream response is visible rather than silently absorbed. Ingestion retries
HTTP 429 and 5xx responses with exponential backoff (six attempts), pauses 0.2 s
between requests, and refuses malformed payloads.

## 6. Terms and attribution

Elexon publishes BMRS data and the endpoint documentation. This repository stores
a derived snapshot for an evaluation build; it does not claim ownership of the
source data. Anyone redistributing the snapshot should check the current Elexon
terms of use and attribution requirements. The application displays the source
names and the snapshot fingerprint in its footer and About page.
