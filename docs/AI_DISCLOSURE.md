# AI assistance disclosure

This file records, in plain language, which AI tools were used to build WindLens
and what the human author remains responsible for. It is the long form of the
disclosure in the README and in the submission answers.

## Tools used

| Tool | Role in this build |
|---|---|
| **DeepSeek V4.1 Flash Free** | The language model that planned, wrote and reviewed the code, tests, analysis and documentation in this repository. Accessed through the provider identified in the build session as `opencode`. |
| **OpenCode** | The agent harness used to run the model with file editing, shell, browser automation and Docker access. It is the environment in which the commands in `docs/AUDIT.md` were executed. |
| **Playwright 1.64.1** | Browser automation used by the agent to run the smoke and axe suites and to capture the screenshots in `docs/img/`. Playwright is a project dependency, not an AI service. |

No other AI coding assistant, hosted code-generation service or model was used
for the implementation. The application itself does not call an AI service at
runtime.

## What the AI did

- Read the supplied brief and produced the build plan, architecture notes,
  methodology, decision records and this disclosure.
- Wrote the ingestion client, normalisation, validation, snapshot builder,
  domain calculations, service layer, FastAPI routes, response schemas and
  error handling.
- Wrote the React application, charts, tables, routing, URL state, styles and
  accessible chart frames.
- Wrote the backend and frontend tests, the Playwright suites, the Docker files,
  the nginx configuration, the CI workflow and the deployment configuration.
- Ran the test, lint, type-check, build, Docker and browser commands recorded in
  `docs/AUDIT.md`, and fixed the failures it found.
- Generated `docs/INSIGHTS.md` and `docs/insights.json` from the committed
  snapshot.
- Captured the screenshots in `docs/img/` from the running Docker stack.

## What the AI did not do

- It did not create a GitHub account or repository, push code, configure a
  remote, or make any decision about account-level anonymity.
- It did not create or configure a Vercel project, deploy the application, or
  choose a public URL.
- It did not record, edit, upload or publish a video.
- It did not submit the project or fill the real submission form.
- It did not invent a time-spent figure, an identity, a testimonial or a
  customer result.
- It did not observe a hosted cold start or a production Vercel bundle size.
  Those measurements remain human actions if the hosted path is used.

## What the human author must do

The human author is responsible for reviewing the generated work, confirming
that the disclosure above is accurate, and validating the final repository
before any public push, deployment, recording or submission. In particular:

1. Read the README, methodology, decision records and key findings, and check
   that they describe the project the author is willing to defend.
2. Confirm the AI-tool statement is accurate. If another tool was used outside
   this build session, add it.
3. Run or review the verification commands in `docs/AUDIT.md`, and confirm the
   numbers in `docs/INSIGHTS.md` against the committed snapshot.
4. Complete the human-only items in `HUMAN_ACTIONS.md`, including the anonymity
   decisions, deployment, video and submission form.
5. Decide how much of the AI-assisted build to describe in the submission's
   time-spent field. Report the human's actual review, deployment and recording
   time, not the model's compute time and not a copy of the brief's 16-hour
   scope budget.

## Honest limitations of AI-generated work

AI-generated code can look confident while being wrong. The mitigations in this
repository are tests against the real snapshot, independent recomputation of
the insight payloads, linting and strict type checks, a leakage audit, a
walk-forward back-test, and pasted command output in the audit. Those checks
reduce the risk; they do not replace the author's review. The product also has
substantive limitations (one month, one season, hourly resolution, a large
direct-comparison bias, a 23-day walk-forward sample), which are stated in
`docs/METHODOLOGY.md` rather than hidden.

## Disclosure text used in the README

> **AI assistance disclosure.** This project was built with AI assistance:
> **DeepSeek V4.1 Flash Free**, running in the **OpenCode** agent harness, was
> used for planning, scaffolding, writing and reviewing code, tests and
> documentation. The human author is responsible for reviewing the work,
> validating the data and results, and handling the deployment, video and
> submission steps. The author confirms that this disclosure is accurate before
> publishing the repository.

The human author should edit the confirmation sentence if the tool list changes.
