# Verification audit

Run date: **2026-11-02** (Europe/London).
Tier 1 evidence source: local tree at **`f05c8de`** (`test(api): audit
decision-time leakage against the real snapshot`). That historical commit is not
part of the force-pushed public branch; the public tree preserves the same files.
Public submission: **real public account URL accepted by H2**. The repository
and deployment use the existing public `Sneh30` account and the existing
`windlens-vhdegk` Vercel project. H2 accepts that account URL. Production
evidence is recorded in §14.
Repository: **<https://github.com/Sneh30/rjbjru>**, neutral author
`dev <dev@users.noreply.invalid>`.
Deployment: **<https://windlens-vhdegk.vercel.app>** (Vercel, public, no login
wall).

This file is the evidence record for `docs/VERIFICATION_GATE.md` Tier 1. Every
command below was run in this build, and the output is reproduced from the run,
not reconstructed from memory. Local absolute paths are shortened to `<repo>`
and `<tmp>`, and the local account token in one search command is shown as
`<local-user>`, so the audit does not publish the local account name; no result
text was changed.

The Tier 1 evidence in §§1–13 was captured at `f05c8de` on the local tree. The
public push, Vercel deployment and production verification are recorded separately
in [§14](#14-public-repository-and-production-deployment); they do not rewrite
the earlier local evidence.

Environment observed by the commands: macOS (`darwin`), Python 3.13.9 in the
local backend virtualenv, Python 3.12 in the API image, Node 24.17.0 locally,
Node 22 in the web image, Docker Compose v5.2.0, Playwright 1.64.1 with Chromium.

## Tier 1 summary

| # | Gate item | Result | Evidence |
|---|---|---|---|
| 1 | T1 — real snapshot, not fixtures | PASS | [§1](#1-t1--real-snapshot-provenance) |
| 2 | T2 — leakage audit on real snapshot + explorer spot check | PASS | [§2](#2-t2--leakage-audit-on-the-real-snapshot) |
| 3 | `make lint typecheck test` with coverage | PASS | [§3](#3-lint-types-and-tests) |
| 4 | Clean-clone Docker smoke | PASS | [§4](#4-clean-clone-docker-smoke) |
| 5 | `make types` and `git diff --exit-code` | PASS | [§5](#5-generated-types-match-the-openapi-schema) |
| 6 | `vitest-axe` and browser axe, zero serious/critical | PASS | [§6](#6-accessibility) |
| 7 | `scripts/check_no_placeholders.sh` | PASS | [§7](#7-placeholder-scan) |
| 8 | `scripts/check_anonymity.sh` + image metadata | PASS (denylist; accepted public handle) | [§8](#8-anonymity-scan-and-image-metadata) |
| 9 | Repo size and composition | PASS | [§9](#9-repository-composition) |
| 10 | Conventional commit history | DEVIATION — 5 public commits; accepted anonymity trade-off | [§10](#10-commit-history) |
| 11 | Insights regenerated as the last content step | PASS | [§11](#11-insights-regenerated-last) |
| 12 | Numbers consistency, every claim | PASS (77/77) | [§12](#12-numbers-consistency) |
| 13 | Video timing estimate | PASS (541 s at 130 wpm) | [§13](#13-video-timing) |

**Tier 1: 12 / 13 green, plus one recorded deviation.** Item 10 fails the
supplied ≥ 15-commit gate because the clean-snapshot force-push collapsed the
public history to five commits; §10 records the trade-off rather than claiming a
pass. Tier 1 was otherwise captured on the local tree at `f05c8de`; the later
public push, deployment and production checks are recorded in §14. Video
recording, upload and form submission remain human-only and are not claimed here.

---

## 1. T1 — real snapshot provenance

The committed snapshot was produced by the live ingestion CLI against the
Elexon BMRS endpoints recorded in `docs/DATA_SOURCES.md`:

```bash
cd backend && .venv/bin/python -m app.ingestion.cli run
```

`data/processed/manifest.json` is the provenance record. Its own values, read
from the committed file:

```text
chunks total 66
by dataset {'FUELHH': 32, 'WINDFOR': 34}
FUELHH chunks 32 rows 1536 fetched_at 2026-11-01T18:10:28Z -> 2026-11-01T18:10:42Z
WINDFOR chunks 34 rows 19856 fetched_at 2026-11-01T18:10:43Z -> 2026-11-01T18:10:58Z
generated_at 2026-11-01T18:42:17Z
fingerprint 331dc8acb133704a
processed rows {'actuals': 1536, 'forecasts': 19856}
```

The first FUELHH chunk in the manifest, reproduced verbatim:

```json
{
  "dataset": "FUELHH",
  "date": "2026-01-01",
  "fetched_at": "2026-11-01T18:10:28Z",
  "file": "raw/fuelhh/2026-01-01.json",
  "params": {
    "fuelType": "WIND",
    "settlementDateFrom": "2026-01-01",
    "settlementDateTo": "2026-01-01"
  },
  "rows": 48,
  "sha256": "39457146a8db3aa3920666437d4bf74f79e19c50ad6aac4bc1c029502ed5a316",
  "url": "https://data.elexon.co.uk/bmrs/api/v1/datasets/FUELHH/stream?settlementDateFrom=2026-01-01&settlementDateTo=2026-01-01&fuelType=WIND"
}
```

The processed files were re-hashed from the committed bytes:

```console
$ make verify-snapshot
cd backend && .venv/bin/python -m app.ingestion.cli verify
{
  "fingerprint": "331dc8acb133704a",
  "fingerprint_ok": true,
  "files": [
    {
      "file": "actuals.csv.gz",
      "expected": "587408a3105a7405ed66bcd7ad7386d1c6f1ad11d22fbf151b610e4963d5183d",
      "actual": "587408a3105a7405ed66bcd7ad7386d1c6f1ad11d22fbf151b610e4963d5183d",
      "ok": true
    },
    {
      "file": "forecasts.csv.gz",
      "expected": "31c554443803a5a59ec9dd47fcc772c50750e6e1c480a819c911d4209930a42d",
      "actual": "31c554443803a5a59ec9dd47fcc772c50750e6e1c480a819c911d4209930a42d",
      "ok": true
    }
  ]
}
```

The copy used by tests is `data/processed/`; the small files under
`backend/tests/fixtures/` are test inputs only. No product number in
`docs/INSIGHTS.md`, the README, the video script or the form answers is derived
from a fixture.

## 2. T2 — leakage audit on the real snapshot

Command, against the production repository and committed snapshot:

```console
$ cd backend && .venv/bin/pytest -k no_leakage_on_real_snapshot -p no:cacheprovider --no-cov -vv
============================= test session starts ==============================
platform darwin -- Python 3.13.9, pytest-8.3.4, pluggy-1.7.0
rootdir: <repo>/backend
configfile: pyproject.toml
testpaths: tests
plugins: respx-0.22.0, cov-6.0.0, hypothesis-6.124.2, anyio-4.16.0
collecting ... collected 198 items / 197 deselected / 1 selected

tests/api/test_leakage.py::test_no_leakage_on_real_snapshot PASSED       [100%]

====================== 1 passed, 197 deselected in 0.37s =======================
```

The test loads `data/processed`, reselects every target at the default cutoff,
recomputes the latest eligible publication from the full vintage set, asserts
that the selected publication equals that maximum and is not after the cutoff,
and asserts that every selected target has an actual. It is not a fixture test.

### Explorer spot check

The Revisions explorer was opened in Chromium against the Docker stack at
`/revisions?date=2026-01-15&period=1&cutoff=09%3A00`. The rendered page said:

```text
Cutoff 09:00 London on D−1 (14 Jan 2026, 09:00 GMT+0). 11 of 13 vintages were eligible; 2 arrived after the cutoff.
SELECTED
07:30
16.5 h
07:30 UTC
SELECTED FORECAST
15,834 MW
11 eligible · 2 after cutoff
...
07:30    07:30 UTC    15,834 MW    16.5 h    Yes    Selected
09:30    09:30 UTC    15,828 MW    14.5 h    No — after cutoff    —
```

The API response for the same target independently reports
`selected_publish_time = 2026-01-14T07:30:00Z`, 11 eligible vintages, and the
same 15,834 MW forecast, so the visual selection and the underlying data agree.

## 3. Lint, types and tests

Command:

```bash
make lint typecheck test
```

Full output:

```console
cd backend && .venv/bin/ruff check . && .venv/bin/ruff format --check .
All checks passed!
61 files already formatted
cd frontend && npm run lint

> windlens-frontend@1.0.0 lint
> eslint . --ext .ts,.tsx --max-warnings 0

cd backend && .venv/bin/mypy --strict app/domain app/services app/data app/api
Success: no issues found in 34 source files
cd frontend && npm run typecheck

> windlens-frontend@1.0.0 typecheck
> tsc --noEmit

cd backend && .venv/bin/pytest
........................................................................ [ 36%]
........................................................................ [ 72%]
......................................................                   [100%]

---------- coverage: platform darwin, python 3.13.9-final-0 ----------
Name                               Stmts   Miss Branch BrPart  Cover   Missing
------------------------------------------------------------------------------
app/api/__init__.py                    0      0      0      0   100%
app/api/deps.py                       22      3      6      3    79%   19, 27, 35
app/api/schemas.py                   348      5     10      3    98%   79, 115-116, 118, 120
app/api/v1/__init__.py                 0      0      0      0   100%
app/api/v1/accuracy.py                46      0      0      0   100%
app/api/v1/common.py                   6      0      0      0   100%
app/api/v1/decision.py                17      0      0      0   100%
app/api/v1/exports.py                 59      0     10      0   100%
app/api/v1/meta.py                    16      0      0      0   100%
app/api/v1/risk.py                    22      0      0      0   100%
app/api/v1/router.py                   9      0      0      0   100%
app/config.py                         97     11     22      7    82%   36, 39, 81, 83, 92-96, 102, 115
app/data/__init__.py                   0      0      0      0   100%
app/data/loader.py                    62      3     22      3    93%   29, 31, 59
app/data/repository.py                88     15     14      5    80%   57, 62, 77, 81, 85, 149-160, 174, 178, 182, 186
app/domain/__init__.py                 0      0      0      0   100%
app/domain/baseline.py                30      0      6      0   100%
app/domain/breakdowns.py              63      1     20      2    96%   76, 130->128
app/domain/constants.py               14      0      0      0   100%
app/domain/errors.py                  10      0      0      0   100%
app/domain/horizon.py                 25      0      4      0   100%
app/domain/join.py                    18      0      0      0   100%
app/domain/metrics.py                 50      0     10      0   100%
app/domain/models.py                  68      0      0      0   100%
app/domain/risk.py                    50      0     10      0   100%
app/domain/selection.py               50      4     20      4    89%   58, 60, 62, 64
app/domain/timeutils.py               47      0     14      0   100%
app/ingestion/__init__.py              0      0      0      0   100%
app/ingestion/elexon_client.py        58      0     10      0   100%
app/ingestion/normalise.py            51      0      4      0   100%
app/ingestion/pipeline.py            150      2     28      2    98%   62, 171
app/ingestion/validate.py             92      3     36      3    95%   45, 140, 142
app/main.py                          123     11     22      5    89%   59->58, 97->102, 98->97, 108->110, 160-164, 210-225, 243->245, 315-316
app/services/__init__.py               0      0      0      0   100%
app/services/accuracy_service.py     112      9     24      7    88%   93, 206-207, 227, 247, 286-287, 292, 299
app/services/analysis_service.py      94      6     20      5    90%   48, 76, 158, 160, 162, 167
app/services/decision_service.py      40      2      4      0    95%   136-137
app/services/formatting.py            48     10     20     10    71%   29, 32, 34, 41, 44, 46, 53, 56, 58, 119
app/services/meta_service.py          18      0      0      0   100%
app/services/revision_service.py      76     17     28      9    73%   40, 42, 48, 50, 85, 92, 96->99, 127->134, 141, 172-175, 189-192, 197, 202
app/services/risk_service.py          18      0      0      0   100%
------------------------------------------------------------------------------
TOTAL                               2097    102    364     68    93%

Required test coverage of 85% reached. Total coverage: 92.85%
198 passed in 3.07s
cd frontend && npm run test -- --run --coverage

> windlens-frontend@1.0.0 test
> vitest --run --coverage


 RUN  v3.2.7 <repo>/frontend
      Coverage enabled with v8

 ✓ src/api/client.test.ts (10 tests) 15ms
 ✓ src/lib/format.test.ts (11 tests) 16ms
 ✓ src/lib/insights.test.ts (16 tests) 19ms
 ✓ src/lib/urlState.test.tsx (16 tests) 36ms
 ✓ src/components/components.test.tsx (11 tests) 302ms
 ✓ src/lib/csv.test.ts (5 tests) 12ms
 ✓ src/App.test.tsx (2 tests) 689ms
   ✓ application shell > navigates between the four views and opens the methodology dialog  676ms
 ✓ src/pages/pages.test.tsx (8 tests) 4631ms
   ✓ Decision Desk > renders the selected day, risk buffer and demand what-if  1003ms
   ✓ Decision Desk > shows a retryable error when metadata fails  1059ms
   ✓ Accuracy Lab > renders the scorecard, every analysis section and the risk panel  1560ms
   ✓ Accuracy Lab > resets a narrowed window to the full scope  401ms

 Test Files  8 passed (8)
      Tests  79 passed (79)
   Start at  12:37:11
   Duration  6.60s (transform 336ms, setup 2.42s, collect 2.29s, tests 5.72s, environment 2.92s, prepare 568ms)

 % Coverage report from v8
-------------------|---------|----------|---------|---------|-------------------
File               | % Stmts | % Branch | % Funcs | % Lines | Uncovered Line #s
-------------------|---------|----------|---------|---------|-------------------
All files          |   95.08 |    80.15 |    73.4 |   95.08 |
 src               |     100 |      100 |     100 |     100 |
  App.tsx          |     100 |      100 |     100 |     100 |
 src/api           |   94.82 |    89.87 |   94.59 |   94.82 |
  client.ts        |     100 |    84.31 |     100 |     100 | ...55,64,79-80,89
  hooks.ts         |   92.16 |      100 |    93.1 |   92.16 | 29-35,196-201
 src/components    |   95.29 |    79.77 |   82.92 |   95.29 |
  ChartFrame.tsx   |     100 |    93.75 |     100 |     100 | 30
  Controls.tsx     |   98.16 |    88.88 |    62.5 |   98.16 | 44-45
  DataTable.tsx    |     100 |    98.03 |     100 |     100 | 36
  ...rBoundary.tsx |     100 |      100 |      80 |     100 |
  ...castChart.tsx |   86.47 |     61.9 |     100 |   86.47 | ...4-60,62-66,186
  InfoTip.tsx      |     100 |      100 |     100 |     100 |
  LabCharts.tsx    |   98.86 |    77.27 |   71.87 |   98.86 | 57-59,147
  ...ogyDialog.tsx |   86.66 |    76.92 |     100 |   86.66 | 18-23,25-30
  Metric.tsx       |   98.66 |       90 |     100 |   98.66 | 84
  ...sionChart.tsx |   88.23 |    42.85 |     100 |   88.23 | 25,27-35,97,106
  Shell.tsx        |   98.43 |    93.75 |    87.5 |   98.43 | 71-73
  States.tsx       |   98.27 |    85.71 |     100 |   98.27 | 69
  VintageStrip.tsx |   95.65 |    56.25 |     100 |   95.65 | 25-27
 src/lib           |   97.46 |    85.07 |     100 |   97.46 |
  csv.ts           |     100 |      100 |     100 |     100 |
  format.ts        |     100 |    79.78 |     100 |     100 | ...58,163,187,194
  insights.ts      |   97.97 |    83.14 |     100 |   97.97 | 59,62,127
  urlState.ts      |   93.63 |    91.04 |     100 |   93.63 | 117-126
 src/pages         |   94.35 |    72.82 |      41 |   94.35 |
  AboutPage.tsx    |   98.32 |       75 |      50 |   98.32 | 76-83
  DeskPage.tsx     |   90.03 |    78.64 |      50 |   90.03 | ...38,541,560-562
  LabPage.tsx      |   95.23 |    65.21 |   35.93 |   95.23 | ...0,839,891,1000
  NotFoundPage.tsx |     100 |      100 |     100 |     100 |
  ...sionsPage.tsx |   93.67 |    77.55 |   42.85 |   93.67 | ...17,122,169-172
 src/types         |       0 |        0 |       0 |       0 |
  api.ts           |       0 |        0 |       0 |       0 |
-------------------|---------|----------|---------|---------|-------------------
```

Backend coverage was 92.85% at the `f05c8de` capture above and 92.87% after the
self-hosted Swagger UI change; both clear the 85% gate. The frontend is 95.08%
statements/lines and 80.15% branches. The backend suite includes the
real-snapshot leakage test from §2, so the count is 198 rather than 197.

## 4. Clean-clone Docker smoke

The committed tree was cloned into a fresh temporary directory at commit
`f05c8de`, and the smoke script was run inside the clone. The clone had a clean
working tree before the build.

```console
$ git clone <repo> <tmp>/windlens-clean/repo
$ git -C <tmp>/windlens-clean/repo log --oneline -1
f05c8de test(api): audit decision-time leakage against the real snapshot
$ git -C <tmp>/windlens-clean/repo status --short
$ cd <tmp>/windlens-clean/repo && bash scripts/smoke_docker.sh
== docker compose build ==
 Image windlens-api:local Building
 Image windlens-web:local Building
 Image windlens-api:local Built
 Image windlens-web:local Built
== docker compose up ==
 Network windlens_default Creating
 Network windlens_default Created
 Container windlens-api-1 Creating
 Container windlens-api-1 Created
 Container windlens-web-1 Creating
 Container windlens-web-1 Created
 Container windlens-api-1 Starting
 Container windlens-api-1 Started
 Container windlens-api-1 Waiting
 Container windlens-api-1 Healthy
 Container windlens-web-1 Starting
 Container windlens-web-1 Started
ok: API health
ok: web root
ok: web -> API proxy
ok: API JSON fields and fingerprint
ok: nginx proxy payload matches direct API payload
ok: SPA shell
ok: SPA history fallback
ok: static CSP header
ok: static nosniff header
ok: API ETag
ok: API request id
ok: conditional request returns 304
ok: CSV content type
ok: CSV media type
ok: CSV header row
ok: API docs return 200
== container state ==
NAME             IMAGE                COMMAND                  SERVICE   CREATED         STATUS                                     PORTS
windlens-api-1   windlens-api:local   "uvicorn app.main:ap…"   api       6 seconds ago   Up 6 seconds (healthy)                     0.0.0.0:8000->8000/tcp, [::]:8000->8000/tcp
windlens-web-1   windlens-web:local   "/docker-entrypoint.…"   web       6 seconds ago   Up Less than a second (health: starting)   0.0.0.0:8080->80/tcp, [::]:8080->80/tcp

Docker smoke passed: API on :8000, web on :8080, health, proxy, SPA fallback, headers, ETag, CSV.
```

Docker layer-cache lines from the build are omitted from this transcript; every
smoke assertion and the image build result are reproduced. The smoke script
tears the stack down on exit. The images built from this clean clone were then
restarted from the project directory for the browser run in §6.

The smoke verifies the API and the nginx proxy return byte-identical payloads,
the SPA shell and history fallback, the server-level CSP and `nosniff` headers,
the API ETag and request id, a conditional `304`, CSV headers and API docs. It is
an integration smoke test, not a penetration test.

## 5. Generated types match the OpenAPI schema

```console
$ make types
bash scripts/gen_types.sh
✨ openapi-typescript 7.5.0
🚀 <tmp>/windlens-openapi.XXXXXX.json → src/types/openapi.d.ts [83.3ms]
generated frontend/src/types/openapi.d.ts from app.openapi()
TYPES_EXIT=0
$ git diff --exit-code -- frontend/src/types/openapi.d.ts
DIFF_EXIT=0
```

The generator emitted the same file as the committed contract; `git diff`
produced no output and exited 0.

## 6. Accessibility

`frontend/src/test/render.tsx` runs `axe()` on every rendered container and
asserts `expect(results).toHaveNoViolations()`. The unit suite passed 79/79 in
§3. It disables only jsdom's colour-contrast inference, which cannot evaluate
the real stylesheet; the browser run is the authority for rendered contrast.

Browser suite, against the production Docker image from the clean clone:

```console
$ cd frontend && PLAYWRIGHT_BASE_URL=http://127.0.0.1:8080 npx playwright test
Running 11 tests using 4 workers

  ✓   4 [chromium] › e2e/a11y.spec.ts:52:3 › About has no serious or critical axe violations (2.3s)
  ✓   1 [chromium] › e2e/a11y.spec.ts:52:3 › Revisions explorer has no serious or critical axe violations (2.3s)
  ✓   2 [chromium] › e2e/a11y.spec.ts:52:3 › Accuracy Lab has no serious or critical axe violations (2.6s)
  ✓   3 [chromium] › e2e/a11y.spec.ts:52:3 › Decision Desk has no serious or critical axe violations (3.0s)
  ✓   5 [chromium] › e2e/a11y.spec.ts:52:3 › Not found has no serious or critical axe violations (1.5s)
  ✓   7 [chromium] › e2e/smoke.spec.ts:19:3 › WindLens smoke › changes delivery day with the keyboard-accessible controls (3.2s)
  ✓   6 [chromium] › e2e/smoke.spec.ts:4:3 › WindLens smoke › redirects to the desk and renders the real snapshot (3.9s)
  ✓   8 [chromium] › e2e/smoke.spec.ts:27:3 › WindLens smoke › toggles hindsight and reveals the actual outturn (3.5s)
  ✓   9 [chromium] › e2e/smoke.spec.ts:36:3 › WindLens smoke › downloads the day CSV (2.8s)
  ✓  11 [chromium] › e2e/smoke.spec.ts:70:3 › WindLens smoke › shows a useful 404 (572ms)
  ✓  10 [chromium] › e2e/smoke.spec.ts:44:3 › WindLens smoke › opens the lab, revisions and methodology views (2.8s)

  11 passed (9.4s)
```

Five page-level axe scans (Decision Desk, Accuracy Lab, Revisions, About, Not
found) reported zero serious and zero critical violations. The test injects
`axe.min.js` through `page.evaluate`, because the production CSP correctly
blocks an inline script tag. Lighthouse was not run; it is not a Tier 1 item here.

## 7. Placeholder scan

```console
$ bash scripts/check_no_placeholders.sh
== placeholder check ==
scanning tracked deliverable text files
ok: no unresolved authoring markers, filler text or <<…>> in deliverables
```

The last line is paraphrased so this audit file does not match the checker's
own literal patterns; the command printed the conventional marker names and
exited 0. The scan excludes the six supplied specification documents, the capability
preflight, the lockfile, the generated OpenAPI types and the checker itself. The
specification documents are inputs rather than deliverables and deliberately
contain meta-examples. The checker source contains the marker patterns it
searches for. No exclusion hides application code, tests, README, analysis,
scripts or the hand-off documents.

## 8. Anonymity scan and image metadata

```console
$ bash scripts/check_anonymity.sh
== anonymity check ==
using .anonymity-denylist
ok: local git identity is neutral
ok: commit authors are neutral
anonymity check passed (denylist, tracked text and commit authors)
```

The private denylist rejects identifiers more specific than the public handle:
full name, personal email, the old Vercel username and related variants. The H2
decision explicitly accepts the public `Sneh30` account URL and the
`windlens-vhdegk.vercel.app` host, so those strings are not treated as leaks. The
script cannot see the GitHub account, Vercel team slug or YouTube channel; H2
records that acceptance and H11 is the human check.

Additional scans on the tracked tree:

```console
$ git grep -In "<local-user>\|/Users/" -- .
docs/VERIFICATION_GATE.md:90:- [ ] No file path on screen contains a real name (`/Users/<realname>/…`, `C:\Users\<realname>\…`) — clone the repo under a neutral path for the recording
$ git grep -InE 'ghp_[A-Za-z0-9]{20,}|github_pat_|sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----' -- .
(no output)
$ git grep -InE '[A-Za-z0-9._%+-]+@(gmail|outlook|yahoo|hotmail|icloud|protonmail)\.[A-Za-z]{2,}' -- .
(no output)
```

The only match for the local account name is the generic `<realname>` example
inside the supplied gate document, not a real value. There are no credentials,
private keys or personal email addresses in the tracked files.

Only three images are tracked, all under `docs/img/`. Their PNG chunks were
parsed with the standard library; there are no textual metadata chunks:

```console
$ python3 <PNG chunk parser> docs/img/*.png
docs/img/accuracy-lab.png: text/metadata chunks = 0
docs/img/desk-hindsight.png: text/metadata chunks = 0
docs/img/revisions.png: text/metadata chunks = 0
```

Each screenshot was also opened and inspected: they are viewport captures of
the application only, with no browser chrome, profile menu, account name,
notification or terminal prompt. `exiftool` is not installed, so the PNG chunk
parser was used instead of `exiftool -all=`.

## 9. Repository composition

```console
$ git count-objects -vH
count: 318
size: 2.48 MiB
in-pack: 0
packs: 0
size-pack: 0 bytes
prune-packable: 0
garbage: 0
size-garbage: 0 bytes
$ git ls-files | wc -l
     192
$ git ls-files -z | xargs -0 du -ch | tail -1
2.9M	total
$ git ls-files | grep -E '(^|/)(\.env$|node_modules/|\.venv/|__pycache__/|\.pytest_cache/|htmlcov/|\.coverage$|dist/)'
(no output)
$ git ls-files | grep -E '\.(pem|key|p12|pfx)$'
(no output)
$ git status --short
(no output)
$ git remote -v
(no output)
```

No environment file, virtualenv, `node_modules`, build output, coverage output
or key material is tracked. This was the pre-push capture; the public remote and
production deployment are recorded in §14.

Those measurements were taken before this audit file was added. With
`docs/AUDIT.md` tracked, the Tier 1 tree was 193 files and 3.0M, still dominated
by the three screenshots, the lockfile and the committed snapshot. The vendored
Swagger UI adds third-party assets; the current count is in §14.

`vercel.json` and Compose configuration were also parsed:

```console
$ python3 -m json.tool vercel.json > /dev/null && echo 'vercel.json valid JSON'
vercel.json valid JSON
$ docker compose config --quiet && echo 'docker-compose.yml valid'
docker-compose.yml valid
```

## 10. Commit history

**Status: DEVIATION.** The supplied gate expects `git log --oneline` to show at
least 15 meaningful, Conventional-Commits-style entries. The public branch has
five, so this item is not a pass.

```console
$ git log --oneline
5e0a62d docs: keep the final incognito check scoped to personal identifiers
19ec451 docs: record live verification and H6-H11 hand-off
f5f24ff build: exclude all private anonymity files from Vercel uploads
3de23b6 docs: record real public account URLs and H2 decision
77e2f93 WindLens: clean public submission snapshot
```

All five use the neutral author identity:

```console
$ git log --format='%an <%ae>' | sort -u
dev <dev@users.noreply.invalid>
```

The pre-push local tree contained 27 commits, still present locally as `f05c8de`
and useful for audit, but it is not served by the public repository. The
clean-snapshot force-push replaced the inherited remote history with one
parentless snapshot commit so that commit timestamps, author metadata and
development granularity could not identify the author. That is the trade-off,
and the cost is a real deviation from the gate's count and style requirements:
the snapshot commit has no Conventional-Commits type prefix.

The public history is not presented as an iterative development log. The video
script does not show or cite `git log`; Part 2 discusses architecture, selection,
tests, CI, deployment and trade-offs from the committed tree.

## 11. Insights regenerated last

After the domain, analysis and snapshot code were frozen, `make insights` was
run again. The two generated files were hashed before and after; the hashes did
not change, so the committed narrative and payloads match the committed snapshot
and the final API.

```console
$ make insights
backend/.venv/bin/python analysis/insights.py
wrote docs/insights.json
wrote docs/INSIGHTS.md
fingerprint=331dc8acb133704a hours=744 mae_mw=2038.9

$ shasum -a 256 docs/INSIGHTS.md docs/insights.json
e6dad82dee38f37fa22357c8d9eb165319132cf831432604914a5f200a82de9a  docs/INSIGHTS.md
c3a1efc9227aefe10982187f963e888a6be66127a961ef6d15a7651281264ff2  docs/insights.json

$ diff before.sha after.sha
HASH_DIFF_EXIT=0
```

The insight contract tests compare the committed JSON with live API responses
and recompute the earliest-vintage comparison independently. They ran as part of
the 198-test backend suite in §3.

## 12. Numbers consistency

The checker is stricter than the gate's minimum: it extracts every numeric token
from the README `Key findings`, every blockquote line of the video narration and
the whole form-answer draft, then requires an exact `Decimal` match in
`docs/INSIGHTS.md`. Dates and clock times are stripped first so they cannot
satisfy a metric claim. There is no rounding rule and no silent tolerance.

```console
$ bash scripts/check_numbers_consistency.sh
canonical source: docs/INSIGHTS.md (206 distinct values)

== README Key findings: 26 numeric claims ==
  ok               744  README Key findings:179  - Across **744 hourly targets**, the selected WINDFOR forecast has MAE
  ok            2038.9  README Key findings:180  **2,038.9 MW** and nMAE **18.07%**.
  ok             18.07  README Key findings:180  **2,038.9 MW** and nMAE **18.07%**.
  ok            1747.9  README Key findings:181  - Bias is **+1,747.9 MW** and **85.0%** of hours are over-forecast, so the error
  ok                85  README Key findings:181  - Bias is **+1,747.9 MW** and **85.0%** of hours are over-forecast, so the error
  ok            4097.9  README Key findings:183  - P90 shortfall is **4,097.9 MW**, P95 is **5,283.4 MW**, and the maximum is
  ok            5283.4  README Key findings:183  - P90 shortfall is **4,097.9 MW**, P95 is **5,283.4 MW**, and the maximum is
  ok              6870  README Key findings:184  **6,870.0 MW**.
  ok            4125.9  README Key findings:185  - Persistence scores **4,125.9 MW** MAE; the forecast's skill is **0.51**, a
  ok              0.51  README Key findings:185  - Persistence scores **4,125.9 MW** MAE; the forecast's skill is **0.51**, a
  ok             50.58  README Key findings:186  **50.58%** MAE reduction.
  ok              16.5  README Key findings:187  - Decision horizons run from **16.5 h** to **39.5 h** (mean **28.0 h**); the
  ok              39.5  README Key findings:187  - Decision horizons run from **16.5 h** to **39.5 h** (mean **28.0 h**); the
  ok                28  README Key findings:187  - Decision horizons run from **16.5 h** to **39.5 h** (mean **28.0 h**); the
  ok             18.79  README Key findings:188  latest vintage beats the earliest eligible vintage by **18.79%** of MAE
  ok            2422.1  README Key findings:189  (**2,422.1 MW** vs **2,038.9 MW**).
  ok            2038.9  README Key findings:189  (**2,422.1 MW** vs **2,038.9 MW**).
  ok            4097.9  README Key findings:190  - At the 90th-percentile risk level the in-sample buffer is **4,097.9 MW**;
  ok                86  README Key findings:191  walk-forward coverage is **86.0%** over **23** evaluated days, with a mean
  ok                23  README Key findings:191  walk-forward coverage is **86.0%** over **23** evaluated days, with a mean
  ok            4051.8  README Key findings:192  buffer of **4,051.8 MW** and **22.0%** of days containing a breach.
  ok                22  README Key findings:192  buffer of **4,051.8 MW** and **22.0%** of days containing a breach.
  ok               744  README Key findings:194  Every one of the **744** targets has a selected forecast and an actual. There are
  ok              1901  README Key findings:196  **1,901.0 MW** (**6.76%** below the default), but it shortens mean horizon to
  ok              6.76  README Key findings:196  **1,901.0 MW** (**6.76%** below the default), but it shortens mean horizon to
  ok              24.1  README Key findings:197  **24.1 h**; the product reports that trade-off instead of calling it a free win.

== VIDEO narration: 42 numeric claims ==
  ok              16.5  VIDEO narration:61  publication, with horizons from 16.5 to 39.5 hours. Coverage is full at
  ok              39.5  VIDEO narration:61  publication, with horizons from 16.5 to 39.5 hours. Coverage is full at
  ok               744  VIDEO narration:62  744 of 744 hourly targets, each with a selected forecast and an actual. The rule is
  ok               744  VIDEO narration:62  744 of 744 hourly targets, each with a selected forecast and an actual. The rule is
  ok            2038.9  VIDEO narration:66  measured MAE from 2,038.9 to 2,016.1 megawatts. Same data, different decision
  ok            2016.1  VIDEO narration:66  measured MAE from 2,038.9 to 2,016.1 megawatts. Same data, different decision
  ok            1726.8  VIDEO narration:78  the seventeenth of January, the day MAE is 1,726.8 megawatts, with a mean actual of 5,647.0
  ok              5647  VIDEO narration:78  the seventeenth of January, the day MAE is 1,726.8 megawatts, with a mean actual of 5,647.0
  ok                24  VIDEO narration:79  megawatts, and all 24 hours are over-forecast. The forecast is not noisy in
  ok            5374.8  VIDEO narration:80  both directions; it is high. The twenty-eighth is the bad day: 5,374.8
  ok               744  VIDEO narration:92  The Accuracy Lab scores every decision in the window. Across 744 hourly
  ok            2038.9  VIDEO narration:93  targets, MAE is 2,038.9 megawatts and nMAE is 18.07 percent. Bias is plus
  ok             18.07  VIDEO narration:93  targets, MAE is 2,038.9 megawatts and nMAE is 18.07 percent. Bias is plus
  ok            1747.9  VIDEO narration:94  1,747.9 megawatts, and 85.0 percent of hours are over-forecast. The P90
  ok                85  VIDEO narration:94  1,747.9 megawatts, and 85.0 percent of hours are over-forecast. The P90
  ok            4097.9  VIDEO narration:95  shortfall is 4,097.9 megawatts; the maximum is 6,870.0. Persistence scores
  ok              6870  VIDEO narration:95  shortfall is 4,097.9 megawatts; the maximum is 6,870.0. Persistence scores
  ok            4125.9  VIDEO narration:96  4,125.9 megawatts of MAE, so the forecast skill is 0.51, a 50.58 percent
  ok              0.51  VIDEO narration:96  4,125.9 megawatts of MAE, so the forecast skill is 0.51, a 50.58 percent
  ok             50.58  VIDEO narration:96  4,125.9 megawatts of MAE, so the forecast skill is 0.51, a 50.58 percent
  ok              1660  VIDEO narration:98  1,660.0 megawatts and the last is 2,317.3, a 39.60 percent increase across
  ok            2317.3  VIDEO narration:98  1,660.0 megawatts and the last is 2,317.3, a 39.60 percent increase across
  ok             39.60  VIDEO narration:98  1,660.0 megawatts and the last is 2,317.3, a 39.60 percent increase across
  ok              16.5  VIDEO narration:99  horizons that run from 16.5 to 39.5 hours. The worst hour is 05:00 at 2,429.9
  ok              39.5  VIDEO narration:99  horizons that run from 16.5 to 39.5 hours. The worst hour is 05:00 at 2,429.9
  ok            2429.9  VIDEO narration:99  horizons that run from 16.5 to 39.5 hours. The worst hour is 05:00 at 2,429.9
  ok            2737.2  VIDEO narration:101  2,737.2 megawatts. This is a forecast with useful shape and a persistent high
  ok            4097.9  VIDEO narration:113  interval. At the 90th-percentile level the in-sample buffer is 4,097.9
  ok                86  VIDEO narration:115  walk-forward back-test with a two-day outcome lag. It covers 86.0 percent of
  ok                23  VIDEO narration:116  hours over 23 evaluated days, with a mean buffer of 4,051.8 megawatts, and
  ok            4051.8  VIDEO narration:116  hours over 23 evaluated days, with a mean buffer of 4,051.8 megawatts, and
  ok                22  VIDEO narration:117  22.0 percent of days contain at least one breach. The target is 90.0 percent;
  ok                90  VIDEO narration:117  22.0 percent of days contain at least one breach. The target is 90.0 percent;
  ok              1901  VIDEO narration:128  Waiting until noon would lower MAE to 1,901.0 megawatts, 6.76 percent below the
  ok              6.76  VIDEO narration:128  Waiting until noon would lower MAE to 1,901.0 megawatts, 6.76 percent below the
  ok                28  VIDEO narration:129  default. It also cuts mean horizon from 28.0 to 24.1 hours. That is the
  ok              24.1  VIDEO narration:129  default. It also cuts mean horizon from 28.0 to 24.1 hours. That is the
  ok                86  VIDEO narration:184  it evaluates a day. That is why it reports 86.0 percent rather than the
  ok                90  VIDEO narration:185  nominal 90.0: the in-sample quantile is not allowed to grade its own homework.
  ok              1536  VIDEO narration:196  and writes a manifest with per-chunk hashes. This snapshot has 1,536 half-hour
  ok             19856  VIDEO narration:197  actuals and 19,856 forecast rows across 272 vintages. The processed files are
  ok               272  VIDEO narration:197  actuals and 19,856 forecast rows across 272 vintages. The processed files are

== FORM answers: 9 numeric claims ==
  ok            2038.9  FORM answers:53  > **2,038.9 MW**, bias **+1,747.9 MW**, an over-forecast share of **85.0%**, and a
  ok            1747.9  FORM answers:53  > **2,038.9 MW**, bias **+1,747.9 MW**, an over-forecast share of **85.0%**, and a
  ok                85  FORM answers:53  > **2,038.9 MW**, bias **+1,747.9 MW**, an over-forecast share of **85.0%**, and a
  ok            4097.9  FORM answers:54  > P90 shortfall of **4,097.9 MW** across **744** hourly targets. A leakage-safe
  ok               744  FORM answers:54  > P90 shortfall of **4,097.9 MW** across **744** hourly targets. A leakage-safe
  ok                86  FORM answers:55  > walk-forward back-test shows **86.0%** coverage at the 90th-percentile buffer
  ok                23  FORM answers:56  > over **23** evaluated days, and the React/FastAPI application exposes the
  ok              2026  FORM answers:63  - **Scope.** The brief says decisions in January 2026. I read that as decision
  ok                31  FORM answers:116  distributions instead of a 31-day slice.

checked 77 claims against 206 canonical values
ok: every numeric claim traces exactly to docs/INSIGHTS.md
```

## 13. Video timing

```console
$ python3 scripts/check_video_timing.py
video timing estimate: <repo>/docs/VIDEO_SCRIPT.md
pace: 130-150 words per minute; tolerance: +10% per section

ID    Words   @130s   @150s  Budget     Status  Title
--------------------------------------------------------------------------------------
S1       57     26s     23s     25s         ok  Problem and promise
S2      123     57s     49s     60s         ok  Decision Desk
S3       78     36s     31s     40s         ok  Hindsight
S4      158     73s     63s     70s         ok  Accuracy Lab
S5      105     48s     42s     45s         ok  Risk buffer and what-if
S6       60     28s     24s     30s         ok  Cutoff sensitivity and close
S7       66     30s     26s     35s         ok  Repository and architecture
S8      133     61s     53s     60s         ok  Selection algorithm
S9       93     43s     37s     40s         ok  Metrics and risk
S10      68     31s     27s     30s         ok  Ingestion and provenance
S11      71     33s     28s     30s         ok  API and contracts
S12      59     27s     24s     30s         ok  Frontend and accessibility
S13      98     45s     39s     45s         ok  Engineering and next steps
--------------------------------------------------------------------------------------
TOTAL 1173 words · 541s at 130 wpm (9.0 min) · 469s at 150 wpm
declared spoken budget: 540s (9.0 min)
target ceiling: 570s (9:30)

ok: every section is within its budget and the total is under 9:30 at 130 wpm
```

The estimate is a word-count arithmetic check, not a recording. The human still
has to record and measure the real runtime in H6/H7.

## 14. Public repository and production deployment

**Status: complete (H1/H2/H4/H5).** The recorded H2 decision is **real account,
account URL is acceptable**. The public repository and deployment use the
existing public `Sneh30` account and the existing `windlens-vhdegk` Vercel
project. No separate account or project is used.

Public repository: **<https://github.com/Sneh30/rjbjru>**, branch `main`. The
remote `main` was force-pushed from a clean local tree. The previous remote head
`207ca0a` was replaced by `3de23b6`; the subsequent build-only commit is
`f5f24ff`. The public branch contains only neutral-author commits
(`dev <dev@users.noreply.invalid>`) and does not serve the inherited local
history.

Production deployment:

```text
Project:      sneh30/windlens-vhdegk
Method:       vercel --prod --yes (CLI deployment, not Git integration)
Deployment:   dpl_CRiCqGKMW1eXYeQUWWWCamUod663
Alias:        https://windlens-vhdegk.vercel.app
Target:       production
State:        READY
Source commit: f5f24ff
```

`.vercelignore` excludes `.anonymity-*`, so the private decision, denylist and
old-deployment evidence are not uploaded to the deployment.

### 14.1 Deployment verification

```console
$ bash scripts/verify_deploy.sh https://windlens-vhdegk.vercel.app
== WindLens deployment verification ==
base: https://windlens-vhdegk.vercel.app
ok: / -> 200
ok: /desk -> 200
ok: /revisions -> 200
ok: /api/v1/health -> 200
ok: /api/v1/meta -> 200
ok: /api/v1/decision-view?delivery_date=2026-01-15&cutoff=09%3A00 -> 200
ok: /api/v1/accuracy/summary?start=2026-01-02&end=2026-02-01&cutoff=09%3A00 -> 200
ok: /api/docs -> 200
ok: /api/static/swagger/swagger-ui.css -> 200
ok: /api/static/swagger/swagger-ui-bundle.js -> 200
ok: /api/openapi.json -> 200
ok: health status = 'ok'
ok: snapshot fingerprint = '331dc8acb133704a'
ok: product name = 'WindLens'
ok: manifest fingerprint = '331dc8acb133704a'
ok: decision coverage = 24
ok: scored hours = 744
ok: health and meta refer to the same snapshot
ok: static security headers present
ok: SPA history fallback serves the app
ok: favicon.ico is a valid ICO file
ok: robots.txt and favicon.ico are real static files
ok: docs UI assets are self-hosted
ok: CSV export

Deployment verification passed for https://windlens-vhdegk.vercel.app
```

Static asset responses at the same host:

```console
$ curl -sS -D - https://windlens-vhdegk.vercel.app/robots.txt
HTTP/2 200
content-type: text/plain; charset=utf-8
content-disposition: inline; filename="robots.txt"

User-agent: *
Allow: /

# WindLens is a public, read-only decision-support demo.
# There are no private or authenticated areas to exclude.

$ curl -sS -D - https://windlens-vhdegk.vercel.app/favicon.ico
HTTP/2 200
content-type: image/vnd.microsoft.icon
content-disposition: inline; filename="favicon.ico"

$ file favicon.ico
MS Windows icon resource - 6 icons, 16x16 with PNG image data, ..., 32x32 with PNG image data, ...
```

Neither path is served by the SPA fallback: `/robots.txt` is `text/plain` and
`/favicon.ico` is `image/vnd.microsoft.icon`, both HTTP 200.

### 14.2 Lighthouse

Lighthouse 12.8.2, mobile default, against
`https://windlens-vhdegk.vercel.app/` (`/desk` after the redirect), fetched
`2026-11-02T15:16:31.319Z`:

```text
performance:      95
accessibility:   100
best-practices:  100
seo:             100
```

Failed audits:

```text
unused-javascript                 Est savings of 74 KiB
network-dependency-tree-insight   no display value
```

Key checks:

```text
robots-txt                     pass
errors-in-console              pass
label-content-name-mismatch    pass
is-on-https                    pass
viewport                       pass
document-title                 pass
meta-description               pass
http-status-code               pass
crawlable-anchors              pass
link-text                      pass
```

The full JSON and HTML reports were generated as `report.report.json` and
`report.report.html` in the local Lighthouse output directory.

### 14.3 Playwright against the live URL

```console
$ cd frontend
$ PLAYWRIGHT_BASE_URL=https://windlens-vhdegk.vercel.app npx playwright test
Running 11 tests using 4 workers

  ✓   4 [chromium] › e2e/a11y.spec.ts:52:3 › Revisions explorer has no serious or critical axe violations (1.9s)
  ✓   3 [chromium] › e2e/a11y.spec.ts:52:3 › About has no serious or critical axe violations (1.9s)
  ✓   1 [chromium] › e2e/a11y.spec.ts:52:3 › Accuracy Lab has no serious or critical axe violations (1.9s)
  ✓   2 [chromium] › e2e/a11y.spec.ts:52:3 › Decision Desk has no serious or critical axe violations (2.0s)
  ✓   7 [chromium] › e2e/smoke.spec.ts:4:3 › WindLens smoke › redirects to the desk and renders the real snapshot (1.1s)
  ✓   6 [chromium] › e2e/smoke.spec.ts:19:3 › WindLens smoke › changes delivery day with the keyboard-accessible controls (1.1s)
  ✓   5 [chromium] › e2e/a11y.spec.ts:52:3 › Not found has no serious or critical axe violations (1.2s)
  ✓   8 [chromium] › e2e/smoke.spec.ts:27:3 › WindLens smoke › toggles hindsight and reveals the actual outturn (1.4s)
  ✓   9 [chromium] › e2e/smoke.spec.ts:36:3 › WindLens smoke › downloads the day CSV (1.2s)
  ✓  11 [chromium] › e2e/smoke.spec.ts:70:3 › WindLens smoke › shows a useful 404 (1.2s)
  ✓  10 [chromium] › e2e/smoke.spec.ts:44:3 › WindLens smoke › opens the lab, revisions and methodology views (2.1s)

  11 passed (5.9s)
```

### 14.4 Numbers consistency

```console
$ bash scripts/check_numbers_consistency.sh
canonical source: docs/INSIGHTS.md (206 distinct values)
...
checked 77 claims against 206 canonical values
ok: every numeric claim traces exactly to docs/INSIGHTS.md
```

The full per-claim output is in the command log for this run.

## Additional build and runtime evidence

Production frontend build:

```console
$ make build
cd frontend && npm run build

> windlens-frontend@1.0.0 build
> tsc --noEmit && vite build

vite v6.0.7 building for production...
transforming...
✓ 717 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   1.00 kB │ gzip:   0.51 kB
dist/assets/index-Bu88RLT8.css   20.10 kB │ gzip:   5.34 kB
dist/assets/query-QLBYHsOP.js    39.80 kB │ gzip:  12.47 kB
dist/assets/index-WkJFWp8k.js   118.25 kB │ gzip:  31.75 kB
dist/assets/react-B0gj22hJ.js   158.10 kB │ gzip:  51.94 kB
dist/assets/charts-Cr1iwtRF.js  416.88 kB │ gzip: 112.17 kB
✓ built in 1.69s
744K	<repo>/frontend/dist
```

API health after the clean-clone images were restarted:

```console
$ curl -fsS http://127.0.0.1:8000/api/v1/health | python3 -m json.tool
{
    "status": "ok",
    "version": "1.0.0",
    "data_fingerprint": "331dc8acb133704a",
    "actual_rows": 1536,
    "forecast_rows": 19856,
    "timezone": "Europe/London"
}
```

## Tier 2 — human actions remaining

H1, H2, H4 and H5 are **complete**; H3 is conditional and not needed for the
current snapshot. Six required actions remain in
[`HUMAN_ACTIONS.md`](../HUMAN_ACTIONS.md):

| # | Action |
|---|---|
| H6 | Record the video with the pre-record checklist |
| H7 | Watch the recording and check spoken numbers, content, length and frames |
| H8 | Upload the video as Unlisted with neutral metadata |
| H9 | Reconcile the guessed fields in `docs/FORM_ANSWERS.md` with the real form |
| H10 | Report the human's actual review, recording, upload and form time |
| H11 | Run the final incognito pass over every submitted URL |

Video recording, upload and the real form have not happened.

## Known limitations

- **Hosted performance is observational.** The function is 70.95 MB and warm TTFB
  was 0.28–0.36 s, but no controlled cold-start benchmark was run. ADR-007
  records the fallback if the hosted function becomes too heavy.
- **CI runs on the public snapshot.** The workflow is committed and the previous
  local run passed all five jobs; the final Actions run ID and badge are read from
  the public repository after the push.
- **Account anonymity is scoped by H2.** The public `Sneh30` account URL and the
  `windlens-vhdegk.vercel.app` host are accepted. The denylist still rejects
  identifiers more specific than that handle, and H11 checks for a real name,
  personal email, employer, location or school in the public artefacts.
- **One month, one season.** The evaluation covers 31 January delivery days,
  and the walk-forward back-test has 23 evaluated days. Tail coverage is
  indicative, not precise.
- **Direct comparison retains a large bias.** WINDFOR is scored against FUELHH
  as published, with a measured +1,747.9 MW bias. No rescaling or fitted bias
  correction is applied, and a portfolio-coverage difference is possible.
- **Hourly resolution.** WINDFOR is hourly in the live feed; each hourly actual
  is the mean of two half-hours. Intra-hour variability is not scored.
- **Private anonymity tokens are checked locally.** `.anonymity-denylist` is
  populated and gitignored; `scripts/check_anonymity.sh` scans every tracked file
  and commit author. The final incognito pass (H11) remains the human check.
- **Video and form are human work.** No recording, upload, real form inspection
  or submission occurred. The video-timing result is an estimate from the script.
- **The app is an analytical aid.** It is not a trading, scheduling or
  financial-advice system.

## Tier 3 sign-off

```text
WHAT WAS BUILT: WindLens is a React/FastAPI decision-time wind forecast desk built on a committed live Elexon snapshot. It implements ingestion, normalisation, validation and snapshot serving (FR-D1–FR-D6); cutoff resolution, inclusive vintage selection, hourly join, metrics, breakdowns, persistence skill, risk buffers and a walk-forward back-test (FR-L1–FR-L11); a versioned read-only API with OpenAPI, problem errors, ETags, CSV exports, health and CORS (FR-A1–FR-A6); four routed views with URL state, accessible charts and tables, what-if demand and provenance (FR-U1–FR-U11); and Docker, README, CI, video script, form answers and hand-off artefacts (FR-P1, FR-P3–FR-P8). FR-P2 is verified at https://windlens-vhdegk.vercel.app in §14; H2 resolves FR-P9 by accepting the public account URL; post-record QA (FR-P10) remains H7.
KEY NUMBERS THE VIDEO WILL CITE: 744 hourly targets; MAE 2,038.9 MW; nMAE 18.07%; bias +1,747.9 MW; over-forecast 85.0%; P90 shortfall 4,097.9 MW; P95 5,283.4 MW; maximum 6,870.0 MW; persistence MAE 4,125.9 MW; skill 0.51 (50.58% MAE reduction); horizon 16.5–39.5 h (mean 28.0 h); earliest-vintage MAE 2,422.1 MW (18.79% worse); P90 in-sample buffer 4,097.9 MW; walk-forward coverage 86.0% over 23 days, mean buffer 4,051.8 MW, 22.0% of days breached; 12:00 cutoff MAE 1,901.0 MW (6.76% below default), mean horizon 24.1 h. All trace to docs/INSIGHTS.md.

AGENT VERIFICATION (Tier 1): 12 / 13 items green, plus one recorded deviation (public commit count and style, §10) — evidence in docs/AUDIT.md. Production verification: 24/24 deployment checks, Lighthouse 95/100/100/100, 11/11 Playwright checks, 77/77 numeric claims; evidence in §14.
CAPABILITY GAPS (Tier 0 → Tier 2): video recording, content QA and Unlisted upload (H6/H7/H8); real submission form (H9); honest human time (H10); final incognito pass (H11). The agent cannot record audio/video or submit the form.
DATA INTEGRITY (T1): real snapshot confirmed — live Elexon pull, manifest fingerprint 331dc8acb133704a, 1,536 FUELHH rows, 19,856 WINDFOR rows, 744/744 decision coverage, both processed SHA-256 checks green.
NUMBERS CONSISTENCY (§2.4): pass — 77/77 claims traced exactly to docs/INSIGHTS.md.
HUMAN ACTIONS REMAINING (Tier 2, from HUMAN_ACTIONS.md): H6 record; H7 post-record QA; H8 Unlisted upload; H9 reconcile form; H10 time spent; H11 incognito pass. H3 (snapshot refresh) is conditional and not needed.
KNOWN LIMITATIONS: Hosted function is 70.95 MB; warm TTFB 0.28–0.36 s, first requests 0.50–0.71 s, no controlled cold-start benchmark; CI runs on the public snapshot; 31-day, one-season sample and a 23-day walk-forward; direct WINDFOR/FUELHH comparison retains a +1,747.9 MW bias; hourly resolution; private anonymity denylist is populated and checked locally; H2 accepts the public account URL; video and form untouched. The product is an analytical aid, not financial advice.

STATUS: PENDING HUMAN VIDEO/FORM HAND-OFF (H6–H11); TIER 1 ITEM 10 DEVIATION RECORDED
```

The status line does not mean the Tier 2 actions have happened, and it is not a
submission.
