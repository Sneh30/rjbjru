# Human actions

This file separates completed, agent-executed steps from the work that remains
human-only. The recorded H2 decision is **real account, account URL is
acceptable**. The public repository and deployment therefore use the existing
public `Sneh30` account and the existing `windlens-vhdegk` Vercel project. The
public account URL and deployment host are accepted.

The agent has **not** recorded a video, uploaded a video, opened the real
submission form or submitted anything. Those actions, and the final human review,
remain yours.

| ID | Action | Status |
|---|---|---|
| H1 | Public GitHub repository and clean snapshot | **DONE** — force-pushed `main`; old remote history replaced |
| H2 | Account-level anonymity decision | **RESOLVED** — real account URL accepted; recorded in `.anonymity-decision` |
| H3 | Refresh the snapshot | Not needed; T1 snapshot is current |
| H4 | Existing Vercel project production deployment | **DONE** — `vercel --prod` CLI deployment |
| H5 | Production URL verification | **RESOLVED** — verify, Lighthouse, Playwright and numbers evidence in `docs/AUDIT.md` §14 |
| H6 | Record the video | **HUMAN** |
| H7 | Post-record content QA | **HUMAN** |
| H8 | Upload the video as Unlisted | **HUMAN** |
| H9 | Reconcile the real submission form | **HUMAN** |
| H10 | Report actual human time | **HUMAN** |
| H11 | Final incognito pass | **HUMAN** |

## Completed public link and deployment work — H1, H2, H4 and H5

- Repository: **<https://github.com/Sneh30/rjbjru>**, branch `main`. The public
  branch was force-pushed from a clean local tree, so the repository's previous
  history is no longer served. Commits use the neutral author
  `dev <dev@users.noreply.invalid>`.
- Decision: `.anonymity-decision` records
  `H2: real account, account URL is acceptable`.
- Deployment: **<https://windlens-vhdegk.vercel.app>**, produced by the existing
  linked Vercel project `windlens-vhdegk` with `vercel --prod`. This was a CLI
  deployment, not a Git-integration auto-deploy.
- Production checks: `scripts/verify_deploy.sh`, Lighthouse, the Playwright e2e
  suite and `scripts/check_numbers_consistency.sh` were run against the live URL.
  The full output is in `docs/AUDIT.md` §14.
- The public account URL and deployment host are the accepted public artefacts.

The deployed function is built on Python 3.12 through `build.env.UV_PYTHON` in
`vercel.json`, because the pinned `pydantic-core` has no Python 3.14 wheel. The
expected function size is about 71 MB, inside Vercel's 250 MB limit.

## H3 — Refresh the snapshot only if you re-ingest

The committed snapshot in `data/processed/` came from the live Elexon pull
recorded in `docs/DATA_SOURCES.md`: 1,536 FUELHH rows and 19,856 WINDFOR rows,
manifest generated at `2026-11-01T18:42:17Z`, fingerprint `331dc8acb133704a`.
Tier-1 item T1 is therefore satisfied. This step is needed only if you want to
refresh the data.

```bash
rm -rf data/raw
make ingest
make verify-snapshot
git add data/processed
git commit -m "chore(data): refresh Elexon snapshot"
make insights
git add docs/INSIGHTS.md docs/insights.json
git commit -m "docs: regenerate insights for refreshed snapshot"
```

The second commit is not optional: the insight files are generated from the
snapshot and the contract test will fail if they drift. Re-run the number
consistency check and the full test suite after a refresh.

## H6 — Record the video

Follow `docs/VIDEO_SCRIPT.md`. Read it once end to end before recording, then use
the timed sections as a guide rather than a teleprompter.

Pre-record checks:

- Clone the repository to a neutral path such as `/tmp/windlens`. Do not show a
  home-directory path that contains your real username.
- Use a fresh browser profile with no bookmarks, no history suggestions, no
  saved-password icon and no personal avatar. Hide the bookmarks bar.
- Set browser zoom to 110% for legibility. Use the light theme. Set the viewport
  to 1920×1080 and record at 1080p.
- Turn off notifications and any app that can display your name.
- Check the terminal prompt: `whoami` and `hostname` must not appear on camera.
  Change `PS1` or crop the terminal if needed.
- Test the microphone and do a 20-second rehearsal. Listen for clipping.
- Decide whether your voice is in scope for anonymity. A recognisable voice is
  itself identifying; the brief does not rule on it, but the choice should be
  deliberate.
- Have the Docker stack running (`docker compose up --build`) or the deployed URL
  open, and pre-load the three demo dates: 2026-01-17, 2026-01-28 and 2026-01-08.
- Close any editor tab whose title bar shows a real name, employer or recent
  project.

Record Part 1 and Part 2 as separate takes if that is easier. Keep the total
spoken length under 9:30; the hard cap is 10:00.

## H7 — Post-record content QA

Watch the recorded video once, end to end, with the script beside you. Confirm:

- At least five numeric insights are actually **spoken**, not only shown on
  screen: MAE, bias, shortfall percentile, persistence skill, horizon range,
  vintage value, risk coverage or cutoff sensitivity.
- Part 1 shows the decision-time view, the hindsight toggle, the accuracy lab,
  the risk buffer and the cutoff sensitivity.
- Part 2 names the architecture, the selection algorithm, the tests, CI, Docker,
  the deployment path and at least one trade-off or next step.
- Every number spoken matches `docs/INSIGHTS.md`. If a number changed after a
  snapshot refresh, re-record that segment.
- No personal name, employer, email, browser profile or notification appears in
  any frame. The public `Sneh30` account URL is accepted by H2 and is not a
  failure.
- The total length is under 10:00, and preferably under 9:30.

If any item fails, fix it before uploading. Do not rely on a viewer to ignore a
leak.

## H8 — Upload the video as Unlisted

- Title: neutral and descriptive, for example `WindLens — day-ahead wind
  decision support`. Do not include your name or employer.
- Description: a short neutral description, the repository URL and the live app
  URL from `docs/FORM_ANSWERS.md`. Do not include an email address, phone number,
  location, school or personal social links.
- Visibility: **Unlisted**, not Public and not Private. The reviewer must be able
  to open it without a Google account.
- Audience: mark it as not made for kids if YouTube asks.
- Comments: disable them, or leave them off. There is no reason to invite
  personal replies.
- Captions: upload or auto-generate English captions. Check that the auto-caption
  does not insert a real name from the audio.
- Thumbnail: use a neutral frame or a simple title card. Do not use a personal
  photo.

Open the uploaded video in a private window and confirm it plays and that the
description contains only the links you intend to publish.

## H9 — Reconcile the real submission form

`docs/FORM_ANSWERS.md` is written against the fields named in the brief, which
did not include a working link to the live form in this document set. Treat every
field as a guess until you open the real form.

1. Open the submission form from the brief.
2. Compare its fields with the headings in `docs/FORM_ANSWERS.md`.
3. Add, remove or merge answers so the wording matches the real field labels.
4. Paste the repository URL and live URL from `docs/FORM_ANSWERS.md`; paste the
   video URL only after H8.
5. Replace the time-spent placeholder with your actual review, recording, upload
   and submission time. Do not copy the brief's 16-hour scope budget and do not
   report the model's compute time.
6. Check the AI-disclosure answer against `docs/AI_DISCLOSURE.md`. Add any tool
   the document omits.
7. Save a copy of the final answers locally, outside the repository, so the
   public repo does not reveal the form's private fields.

## H10 — Report actual time spent honestly

The brief's "≤ 16 hours" is a scope budget, not a stopwatch reading. Report the
human time actually spent: reading and reviewing the generated work, fixing what
needed fixing, reviewing the deployment, recording, uploading and filling in the
form. If AI assistance substantially reduced that time, say so; the README
discloses it anyway. Do not present the agent's wall-clock runtime as your own
work time.

## H11 — Final incognito pass

After H6–H10, open every submitted URL in a fresh incognito window:

- The GitHub repository, including the profile link in the URL.
- The live deployment, including its API health endpoint and `/api/docs`.
- The YouTube video, including playback and the description.
- The submission form's confirmation page, if the form shows one.

Check the repository README, the app footer, the video frames and the form for any
real name, personal email, employer, location or school. The public `Sneh30`
account URL is accepted by H2 and is not a failure. Check that the live app has no
Vercel protection wall and that the video is playable without signing in. Only
after this pass is the project submitted.

If a leak is found, fix it at the source (account profile, Vercel team, YouTube
channel or repository text), redeploy or re-upload, and repeat H11. Do not patch
the symptom in one place while leaving the account-level leak in another.
