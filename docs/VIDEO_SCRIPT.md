# Video script

**Target length:** 9:00 spoken, with a hard cap of 9:30 and the submission cap at
10:00. The timing table below is a planning target, not a claim about a recording
that has not been made. The words in blockquotes are the spoken narration; the
`On screen` lines are directions and are not read aloud.

Every numeric claim in the narration traces to `docs/INSIGHTS.md`. Run
`python3 scripts/check_video_timing.py` and
`bash scripts/check_numbers_consistency.sh` after editing this file.

## Timing plan

| Section | Video time | Spoken budget | Content |
|---|---:|---:|---|
| S1 | 0:00–0:25 | 25 s | Problem, promise, who it is for |
| S2 | 0:25–1:25 | 60 s | Decision Desk, cutoff, vintage selection |
| S3 | 1:25–2:05 | 40 s | Hindsight, typical day, bad day |
| S4 | 2:05–3:15 | 70 s | Accuracy Lab headline, horizon, hour, level |
| S5 | 3:15–4:00 | 45 s | Risk buffer, walk-forward, demand what-if |
| S6 | 4:00–4:30 | 30 s | Cutoff sensitivity, value proposition, close Part 1 |
| S7 | 4:30–5:05 | 35 s | Repository and architecture |
| S8 | 5:05–6:05 | 60 s | Selection algorithm and leakage tests |
| S9 | 6:05–6:45 | 40 s | Metrics, sign convention and risk back-test |
| S10 | 6:45–7:15 | 30 s | Ingestion, manifest and fingerprint |
| S11 | 7:15–7:45 | 30 s | API, errors, caching, generated types |
| S12 | 7:45–8:15 | 30 s | Frontend state, accessibility and tests |
| S13 | 8:15–9:00 | 45 s | CI, Docker, deployment, trade-offs, next steps |

Total spoken budget: 540 s. The checker uses 130 words per minute for the
conservative estimate and flags any section over its budget by more than 10%.

---

## Part 1 — Client pitch

### 0:00–0:25 · Problem and promise

<!-- section: S1 budget=25 title="Problem and promise" -->

**On screen:** Title card with the WindLens wordmark, then a hard cut to the
Decision Desk for 2026-01-17. No terminal, no file paths.

> A day-ahead wind buyer does not need the best forecast that will exist
> tomorrow. They need the forecast that was actually in hand at the moment they
> had to decide, and they need to know how wrong it tends to be. WindLens makes
> that decision-time view visible, scores it, and turns the error into a
> shortfall buffer.

### 0:25–1:25 · The Decision Desk

<!-- section: S2 budget=60 title="Decision Desk" -->

**On screen:** `/desk?date=2026-01-17&cutoff=09:00`. Point to the cutoff banner,
the selected vintage time, the horizon range and the coverage tiles. Then change
the cutoff control from 09:00 to 06:00 and back. Keep the pointer movement slow.

> This is the Decision Desk for the seventeenth of January. The cutoff is nine in
> the morning on the previous London day. WindLens finds the latest WINDFOR
> vintage published at or before that instant. Here that is the 07:30
> publication, with horizons from 16.5 to 39.5 hours. Coverage is full at
> 744 of 744 hourly targets, each with a selected forecast and an actual. The rule is
> inclusive at the boundary and it never reaches forward to a later revision.
> That is the difference between "latest available at the decision" and "latest
> ever". Changing the cutoff changes which vintage is in hand, and it changes the
> measured MAE from 2,038.9 to 2,016.1 megawatts. Same data, different decision
> time.

### 1:25–2:05 · Hindsight

<!-- section: S3 budget=40 title="Hindsight" -->

**On screen:** Toggle **Hindsight** on for 2026-01-17. Point to the error colours,
then switch the date to 2026-01-28 and let the chart redraw. Keep the P90 band
visible.

> Toggle hindsight and the actual outturn appears. On this typical low-wind day,
> the seventeenth of January, the day MAE is 1,726.8 megawatts, with a mean actual of 5,647.0
> megawatts, and all 24 hours are over-forecast. The forecast is not noisy in
> both directions; it is high. The twenty-eighth is the bad day: 5,374.8
> megawatts of MAE and the same amount of positive bias. The buyer who planned
> against that forecast was short every hour.

### 2:05–3:15 · Accuracy Lab

<!-- section: S4 budget=70 title="Accuracy Lab" -->

**On screen:** `/lab?cutoff=09:00&risk=0.9`. Start on the scorecard, scroll to the
horizon chart, then the hour chart, then the wind-level chart. Do not scroll past
the risk section yet.

> The Accuracy Lab scores every decision in the window. Across 744 hourly
> targets, MAE is 2,038.9 megawatts and nMAE is 18.07 percent. Bias is plus
> 1,747.9 megawatts, and 85.0 percent of hours are over-forecast. The P90
> shortfall is 4,097.9 megawatts; the maximum is 6,870.0. Persistence scores
> 4,125.9 megawatts of MAE, so the forecast skill is 0.51, a 50.58 percent
> reduction. Error grows with lead time: the first populated horizon bucket is
> 1,660.0 megawatts and the last is 2,317.3, a 39.60 percent increase across
> horizons that run from 16.5 to 39.5 hours. The worst hour is 05:00 at 2,429.9
> megawatts, and the largest absolute error is in the fourth wind quintile at
> 2,737.2 megawatts. This is a forecast with useful shape and a persistent high
> bias, not a forecast that is simply unusable.

### 3:15–4:00 · Risk buffer and what-if

<!-- section: S5 budget=45 title="Risk buffer and what-if" -->

**On screen:** Scroll to **Risk buffer and calibration**. Point to the P90 card,
the walk-forward row and the coverage bar. Then enter `24000` in **Demand
what-if** and show the residual and risk-adjusted figures.

> The product response is a one-sided buffer, not a symmetric confidence
> interval. At the 90th-percentile level the in-sample buffer is 4,097.9
> megawatts. That is optimistic by construction, so WindLens also runs a
> walk-forward back-test with a two-day outcome lag. It covers 86.0 percent of
> hours over 23 evaluated days, with a mean buffer of 4,051.8 megawatts, and
> 22.0 percent of days contain at least one breach. The target is 90.0 percent;
> the gap is the honest out-of-sample cost, on a small sample. Enter a demand
> scenario and the desk shows the residual to procure after applying the buffer.

### 4:00–4:30 · Cutoff sensitivity and close

<!-- section: S6 budget=30 title="Cutoff sensitivity and close" -->

**On screen:** Scroll to **Cutoff sensitivity**. Highlight the 09:00 and 12:00
rows, then cut back to the Decision Desk title area.

> Waiting until noon would lower MAE to 1,901.0 megawatts, 6.76 percent below the
> default. It also cuts mean horizon from 28.0 to 24.1 hours. That is the
> trade-off, not a free win. WindLens gives a buyer a defensible view of the
> forecast they had, the size of the miss, and the buffer the record supports.

---

## Part 2 — Technical review

### 4:30–5:05 · Repository and architecture

<!-- section: S7 budget=35 title="Repository and architecture" -->

**On screen:** GitHub-style repository tree, then `docs/ARCHITECTURE.md`'s
container diagram. Highlight `backend/app/domain`, `backend/app/api` and
`data/processed`.

> The repository is one React single-page app, one FastAPI service and one
> immutable Elexon snapshot. Ingestion is offline; the request path never calls
> Elexon. The API reads the snapshot once, validates its hashes and serves
> selection and analysis from memory. That is a reliability choice and a
> reproducibility choice: the demo works without the upstream feed, and every
> number has a manifest timestamp and a fingerprint.

### 5:05–6:05 · Selection algorithm and leakage tests

<!-- section: S8 budget=60 title="Selection algorithm" -->

**On screen:** `backend/app/domain/selection.py`, then the matching test file.
Show the cutoff comparison and the assertion that no selected publication is
after the cutoff. Run one focused test if the terminal is already prepared.

> The core is deliberately small. For each target hour, resolve the cutoff to
> UTC, keep every vintage whose publish time is less than or equal to it, and
> take the maximum publish time. The boundary is inclusive. If no vintage is
> eligible, the target is omitted and counted as missing; it is never filled from
> later information. The tests assert that no selected row is after the cutoff,
> that the selected row is the latest eligible one, that an exact-boundary
> publication is accepted, and that the London conversion behaves correctly
> around a daylight-saving transition. The real snapshot also has a leakage audit
> that walks every selected row, not a fixture. The Revisions explorer exposes
> the same boundary visually: later vintages are shown, but they are marked as
> information the decision could not use.

### 6:05–6:45 · Metrics and risk

<!-- section: S9 budget=40 title="Metrics and risk" -->

**On screen:** `backend/app/domain/metrics.py` and `risk.py`. Point to the error
sign, the percentile calculation and the walk-forward lag.

> Metrics use error equals forecast minus actual, so positive means the buyer is
> short. MAE, RMSE, bias, nMAE, WAPE, percentiles and shortfall all come from the
> same joined frame. The risk buffer is the empirical quantile of signed error,
> subtracted from the forecast and floored at zero. The back-test uses only
> outcomes from at least two days earlier and requires seven history days before
> it evaluates a day. That is why it reports 86.0 percent rather than the
> nominal 90.0: the in-sample quantile is not allowed to grade its own homework.

### 6:45–7:15 · Ingestion and provenance

<!-- section: S10 budget=30 title="Ingestion and provenance" -->

**On screen:** `docs/DATA_SOURCES.md` and `data/processed/manifest.json`. Point
to the fetched-at timestamps, the 1,536 actual rows and the 19,856 forecast rows.

> Ingestion fetches day-sized chunks with retries for rate limits and server
> errors. It normalises only wind rows, checks duplicates and unparseable values,
> and writes a manifest with per-chunk hashes. This snapshot has 1,536 half-hour
> actuals and 19,856 forecast rows across 272 vintages. The processed files are
> hashed at startup, and the fingerprint changes if either changes. Test fixtures
> are not the source of any product number.

### 7:15–7:45 · API and contracts

<!-- section: S11 budget=30 title="API and contracts" -->

**On screen:** `/api/docs`, then one request in the browser or a prepared curl
showing the ETag and request id. Show the generated TypeScript file briefly.

> The API is read-only and versioned under `/api/v1`. Decision responses hide
> actuals unless the caller opts in, so hindsight is an explicit choice. Errors
> are problem+json with a request id; data responses carry an ETag derived from
> the snapshot fingerprint and the query. The OpenAPI schema is the contract, and
> the TypeScript types are generated from it in CI, so a frontend field cannot
> silently drift from the backend.

### 7:45–8:15 · Frontend and accessibility

<!-- section: S12 budget=30 title="Frontend and accessibility" -->

**On screen:** Change a filter and show the URL update. Open one chart's **View
as table** alternative, then show a focus ring on a table scroller.

> The URL owns the delivery date, cutoff, lab window, chart basis and risk level,
> so a view is shareable and reproducible. The demand what-if stays local because
> it is a scenario, not a server fact. Every chart has a heading, summary and table
> alternative; chart internals are hidden from assistive technology. The browser
> and unit suites both run axe.

### 8:15–9:00 · Engineering, trade-offs and next steps

<!-- section: S13 budget=45 title="Engineering and next steps" -->

**On screen:** CI workflow, Docker Compose, then `vercel.json`. Finish on the
About page's AI disclosure and the repository README.

> CI runs Ruff, strict mypy, pytest with a coverage gate, ESLint, TypeScript,
> Vitest, a generated-types diff and both Docker builds. Compose runs the API as
> a non-root user with a read-only root filesystem, behind nginx. Vercel is the
> primary hosted path; deployment is a human step because the account and URL
> need an anonymity check. The trade-offs are deliberate: a direct
> WINDFOR-to-FUELHH comparison keeps a large bias rather than hiding it with an
> unauthorised calibration; evaluation is hourly because the forecast is; and
> the walk-forward sample is small. Next: more seasons, portfolio coverage, and
> capacity normalisation if permitted.

---

## Pre-record checklist

- [ ] Clone the repository to `/tmp/windlens`, not a home-directory path that
      contains the local username.
- [ ] `docker compose up --build` is healthy, or the verified deployment is open.
- [ ] Browser: fresh profile, no bookmarks bar, no saved-password icon, no
      personal avatar, zoom 110%, light theme, viewport 1920×1080.
- [ ] Notifications off. Desktop wallpaper and dock are neutral.
- [ ] Terminal prompt has no real username or hostname. `PS1` is changed or the
      terminal is cropped.
- [ ] IDE title bar and recent-projects list show no real name or employer.
- [ ] Microphone tested; a 20-second rehearsal has been listened to for clipping.
- [ ] The three demo dates are pre-loaded: 2026-01-17 (typical), 2026-01-28
      (bad), 2026-01-08 (big ramp).
- [ ] The voice-anonymity decision has been made deliberately; a recognisable
      voice is identifying.
- [ ] The script has been read once end to end and the numbers checked against
      `docs/INSIGHTS.md`.

## Caption outline

Use these phrases for the caption track if the platform auto-caption is poor:

1. "Decision-time wind forecast, not the latest revision."
2. "Latest vintage published at or before the cutoff."
3. "744 hourly targets; MAE 2,038.9 megawatts; bias plus 1,747.9."
4. "P90 shortfall 4,097.9 megawatts."
5. "Walk-forward coverage 86.0 percent over 23 days."
6. "No look-ahead: the selected publication never exceeds the cutoff."
7. "Snapshot-based serving; ingestion is offline."
8. "React, FastAPI, Docker, Vercel; tests and generated contracts in CI."

## YouTube settings

- **Visibility:** Unlisted. The reviewer must be able to open it without a
  Google account.
- **Title:** `WindLens — day-ahead wind decision support`. No personal name.
- **Description:** one neutral paragraph, the repository URL and the verified
  live URL from `docs/FORM_ANSWERS.md`. No email, phone, location, school,
  employer or personal social links.
- **Audience:** not made for kids, if asked.
- **Comments:** off.
- **Captions:** English, reviewed for names and numbers.
- **Thumbnail:** a neutral title card or a chart frame. No personal photo.
- **Playback check:** open the uploaded video in a private window and confirm it
  plays, the description is correct and the length is under 10:00.

## Post-record QA

Watch the recording once with this file open. Confirm that at least five numeric
insights are spoken, that Part 2 names the architecture, selection algorithm,
tests, CI/Docker/deploy path and a trade-off or next step, and that no section
ran long enough to push the total past 9:30. Check every frame for a real name,
username, employer, email, account URL, browser profile or notification. If a
number changed after a snapshot refresh, re-record that segment.
