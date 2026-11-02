# Submission form answers

**Status: fresh-account migration pending; video and time are human-only.** The
brief's link to the live submission form did not carry a working URL into this
document set. Open the real form and reconcile every field before pasting
anything. The field names below are a reasonable guess, not a verified schema.
This file is not evidence that the form has been filled.

Fields marked **HUMAN TO FILL** cannot be filled in by the agent. The repository
and live-app URLs are placeholders until the human creates the fresh neutral
accounts (H1/H2/H4); `scripts/set_public_urls.sh` fills them. The migrated
deployment is verified immediately before submission, and the real output is
pasted into the submission notes.

## Repository

**Guessed field:** repository URL

```text
https://github.com/__GITHUB_OWNER__/rjbjru
```

The new repository is created under a fresh neutral account, with no real name,
personal email, personal avatar or link to the retired account. It is published
as a single clean snapshot commit with author `dev <dev@users.noreply.invalid>`
and default branch `main`; the inherited history is not pushed. The repository
name `rjbjru` is neutral.

## Live application

**Guessed field:** deployed application URL

```text
https://__VERCEL_HOST__
```

The migrated deployment is verified with `bash scripts/verify_deploy.sh
"https://__VERCEL_HOST__"` before submission. The script covers the SPA routes,
health, metadata, decision view, accuracy summary, self-hosted docs, security
headers, CSV export, `robots.txt` and `favicon.ico`. The app must open without a
Vercel login wall, and the 11-check Playwright suite is run against the same URL
with its real output pasted into the submission notes.

> The replacement account, project and deployment host are chosen to contain no
> personal handle. The old team-scoped deployment and its alias are retired
> (H2/H4).

## Video

**Guessed field:** video URL

```text
[paste the Unlisted YouTube URL from H8]
```

The video must play in a private window without a Google sign-in.

## Three-sentence solution summary

**Guessed field:** short summary / what did you build?

> WindLens is a decision-time wind forecast explorer for a day-ahead buyer. It
> selects the latest Elexon WINDFOR vintage published at or before 09:00
> Europe/London on D minus one, joins it to hourly FUELHH wind outturn, and reports MAE
> **2,038.9 MW**, bias **+1,747.9 MW**, an over-forecast share of **85.0%**, and a
> P90 shortfall of **4,097.9 MW** across **744** hourly targets. A leakage-safe
> walk-forward back-test shows **86.0%** coverage at the 90th-percentile buffer
> over **23** evaluated days, and the React/FastAPI application exposes the
> decision desk, accuracy lab, revisions and full methodology.

## Assumptions

**Guessed field:** assumptions and interpretation choices

- **Scope.** The brief says decisions in January 2026. I read that as decision
  dates 2026-01-01 to 2026-01-31, delivering 2026-01-02 to 2026-02-01. The
  alternative delivery-date reading is available through `SCOPE_MODE`.
- **Cutoff.** 09:00 Europe/London on D minus one, inclusive at the boundary. This is a
  conservative default relative to common day-ahead gates and is configurable in
  the API and UI.
- **Resolution.** WINDFOR is hourly in the live feed, despite the brief's
  half-hourly example. Each hourly actual is the mean of the two FUELHH
  half-hours; missing pairs are excluded, never interpolated.
- **Sign.** `error = forecast − actual`; positive is over-forecast and shortfall
  risk. The risk buffer is subtracted from the forecast.
- **Comparison.** WINDFOR and FUELHH wind are compared directly. I did not
  rescale the forecast, fit a bias correction, or substitute another wind series.
  The large positive bias is reported as measured risk.
- **Capacity.** nMAE uses mean actual output because installed capacity is
  outside the two permitted datasets.
- **No imputation.** Missing actuals are excluded and counted; missing forecasts
  are omitted and counted.

## AI tools used

**Guessed field:** AI assistance disclosure

> This project was built with AI assistance. **DeepSeek V4.1 Flash Free**,
> running in the **OpenCode** agent harness, was used for planning, scaffolding,
> writing and reviewing code, tests and documentation. The human author is
> responsible for reviewing the work, validating the data and results, and
> handling the deployment, video and submission steps. The author confirms that
> this disclosure is accurate before publishing the repository.

The long form is in `docs/AI_DISCLOSURE.md`. If the real form has a free-text
field, use this paragraph; if it has a yes/no field, answer yes and paste the
paragraph into the explanation box if one exists.

## Time spent

**Guessed field:** hours spent / time budget

```text
HUMAN TO FILL: report the human's actual review, deployment, recording,
upload and form time. Do not copy the brief's sixteen-hour scope budget and do not
report the model's compute time.
```

The brief's sixteen hours is a scope budget for the build, not a stopwatch reading. If
AI assistance substantially reduced the human time, say so; the README discloses
it and the honesty is more credible than a rounded claim.

## What I would do next

**Guessed field:** next steps / improvements

- Extend the evaluation beyond one January and report seasonal and annual
  distributions instead of a 31-day slice.
- Investigate the level difference between WINDFOR and FUELHH wind: confirm
  whether the two series cover the same portfolio, and whether a
  capacity-normalised comparison is possible within the client's data policy.
- Add probabilistic or ensemble forecasts if the client permits another dataset,
  and evaluate them with proper scoring rules rather than a point-error buffer.
- Add scheduled snapshot refresh and drift alerts so the decision desk can run
  against the latest published data without a manual ingest.
- Add a buyer-facing scenario tool with a real demand forecast and reserve
  constraints, rather than the flat what-if input used here.

## Notes for the human

- The repository and app URLs above are placeholders until H1/H4 create the fresh
  neutral accounts. Fill them with `scripts/set_public_urls.sh`, then run
  `bash scripts/verify_deploy.sh "https://__VERCEL_HOST__"` immediately before
  submitting and paste the real output.
- Do not paste the video URL until H8 uploads it as Unlisted and H7 passes.
- Save the final form answers locally, outside the repository. The public repo
  should not contain private form fields or the human's time estimate.
- If the real form asks a question that is not covered here, answer it directly
  rather than forcing it into one of these guessed sections.
