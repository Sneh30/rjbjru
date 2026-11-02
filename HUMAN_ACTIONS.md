# Human actions

This file separates completed, agent-executed steps from the work that remains
human-only. The earlier public repository and deployment used identifying account
handles and have been retired. The public submission moves to fresh, neutral
GitHub and Vercel accounts created by the human; the agent cannot create accounts
or complete CAPTCHA, email or phone verification.

The agent has **not** recorded a video, uploaded a video, opened the real
submission form or submitted anything. Those actions, and the final human review,
remain yours.

| ID | Action | Status |
|---|---|---|
| H1 | Fresh GitHub repository and clean public snapshot | **HUMAN** — account creation, then `scripts/publish_clean_snapshot.sh` |
| H2 | Fresh-account anonymity decision | **DECIDED** — recorded in `.anonymity-decision`; accounts pending |
| H3 | Refresh the snapshot | Not needed; T1 snapshot is current |
| H4 | Fresh Vercel project and production deployment | **HUMAN** — account and project creation |
| H5 | New URL, old-alias removal and slug check | **PENDING** H4 |
| H6 | Record the video | **HUMAN** |
| H7 | Post-record content QA | **HUMAN** |
| H8 | Upload the video as Unlisted | **HUMAN** |
| H9 | Reconcile the real submission form | **HUMAN** |
| H10 | Report actual human time | **HUMAN** |
| H11 | Final incognito pass | **HUMAN** |

Do not use the old `gh` or `vercel` sessions for any step below. They are tied to
the identifying accounts and must not be reused.

## H1 — Create the fresh GitHub repository and push a clean snapshot

The existing local history contains the retired account URLs in old documentation
commits. Do **not** push that history to the new repository. Publish a single
clean snapshot commit instead.

1. Create a new GitHub account with a neutral username, no real name, no linked
   personal email, no personal avatar and no public link to the old account.
2. Create an empty **private** repository named `rjbjru`. Do not add a README,
   licence or `.gitignore` through the browser.
3. Authenticate `git` for the new account (credential helper or a fresh SSH key).
   Do not run `gh auth login` over the old session; use a separate key or helper.
4. Insert the new owner into the tracked documentation and commit it:
   ```bash
   bash scripts/set_public_urls.sh --github-owner <new-github-owner>
   git add README.md docs/AUDIT.md docs/FORM_ANSWERS.md HUMAN_ACTIONS.md
   git commit -m "docs: set migrated repository owner"
   ```
5. Point `origin` at the new empty repository:
   ```bash
   git remote set-url origin https://github.com/<new-github-owner>/rjbjru.git
   git remote -v
   ```
6. Run the anonymity gate, then publish the initial clean snapshot while the
   repository is still private:
   ```bash
   bash scripts/check_anonymity.sh
   bash scripts/publish_clean_snapshot.sh --allow-pending-host
   ```
   The publish script creates an orphan commit containing only the current tree,
   so no retired URL or old commit message enters the new history. The
   `--allow-pending-host` flag is only for this private first push, before H4 has
   a Vercel hostname; the second push in H4 must pass the full URL gate.
7. In the old GitHub account's web UI, change the old `rjbjru` repository to
   **private**. The agent will not use the old CLI session to do this.
8. Keep the new repository private until H4 has filled the production host. Then
   change its visibility to public.

The repository name is neutral; the new account handle must also be neutral.

## H2 — Decide account-level anonymity (decided)

The recorded decision, in the gitignored `.anonymity-decision`, is:

```text
H2: fresh neutral GitHub and Vercel accounts (decision 2026-11-02, supersedes the earlier existing-account acceptance)
```

Consequences:

- The GitHub account is created for this submission only, with no real name,
  personal email, personal avatar or link to other accounts.
- The Vercel account/project is created for this submission only. No identifying
  team slug appears in the project, dashboard URL or deployment host.
- The old repository becomes private and the old Vercel project is deleted, or at
  minimum its team-scoped alias is removed, so the retired deployment stops
  resolving.
- README, form answers, video description and hand-off docs reference only the
  new repository and production URLs.
- `.anonymity-denylist` is populated and gitignored. `scripts/check_anonymity.sh`
  scans every tracked file and every commit author.

The literal old account, project and alias identifiers are recorded only in the
gitignored decision and private evidence files, never in public documentation.

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

## H4 — Create the fresh Vercel project and deploy

Do this only after H1 has pushed the clean snapshot.

1. Sign in to Vercel through the new neutral account. Do not reuse the old
   `vercel` CLI session or the old team.
2. Import the new GitHub repository `rjbjru`. Use a neutral project name that
   does not contain a person's name or handle. Framework preset: **Other**, root
   directory `.`; `vercel.json` supplies the build.
3. Deploy to production and record the assigned host, for example
   `<neutral-project>.vercel.app`.
4. Insert the host into the tracked documentation, commit, then replace the
   private placeholder snapshot with the final clean one:
   ```bash
   bash scripts/set_public_urls.sh --vercel-host <neutral-project>.vercel.app
   git add README.md docs HUMAN_ACTIONS.md
   git commit -m "docs: record migrated production URL"
   bash scripts/publish_clean_snapshot.sh
   ```
   The second publish force-pushes another parentless snapshot, now with both
   real URLs and no placeholders. The public history is one commit.
5. Delete the old Vercel project. If deletion is not possible, open
   **Settings → Domains** on the old project and remove the team-scoped alias so
   it stops resolving. The literal alias is in the private evidence file; it must
   not appear in the new repository.
6. Make the new GitHub repository public if it was created private.

The deployed function is built on Python 3.12 through `build.env.UV_PYTHON` in
`vercel.json`, because the pinned `pydantic-core` has no Python 3.14 wheel. The
expected function size is about 71 MB, inside Vercel's 250 MB limit.

## H5 — Check the new URL, old aliases and slug

- Run the full verifier against the new host:
  ```bash
  bash scripts/verify_deploy.sh "https://<neutral-project>.vercel.app"
  ```
  It now checks the SPA routes, API, self-hosted docs, security headers, CSV
  export, `robots.txt` and `favicon.ico`.
- Run Lighthouse against the same URL and keep the full JSON/HTML report,
  including failed audits.
- Confirm the retired team-scoped alias no longer resolves (the literal is in the
  private evidence file; do not paste it into tracked docs).
- Confirm the new dashboard, deployment-specific URLs and repository URL contain
  no personal handle.
- Confirm the page title, footer, Open Graph tags and README contain no personal
  name, email or avatar.
- Run `bash scripts/check_anonymity.sh` and `scripts/check_public_urls.sh`, then
  run the full incognito pass (H11) against the new links only.

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
- No personal name, username, employer, email, account URL, browser profile or
  notification appears in any frame.
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

Check the repository README, the app footer, the video frames and the form for
any real name, handle, email, employer, location, school or account slug. Check
that the live app has no Vercel protection wall and that the video is playable
without signing in. Only after this pass is the project submitted.

If a leak is found, fix it at the source (account profile, Vercel team, YouTube
channel or repository text), redeploy or re-upload, and repeat H11. Do not patch
the symptom in one place while leaving the account-level leak in another.
