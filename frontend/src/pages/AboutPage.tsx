import { Link } from "react-router-dom";

import { useMeta } from "../api/hooks";
import { humaniseProblem } from "../api/client";
import { PageHeader } from "../components/Metric";
import { ErrorState, PageSkeleton } from "../components/States";
import { formatDateTime, formatNumber, shortHash } from "../lib/format";

const GLOSSARY: { term: string; definition: string }[] = [
  {
    term: "Day-ahead",
    definition:
      "The trading cycle in which power for delivery day D is bought on D−1. WindLens evaluates the information set available before that day's decision cutoff.",
  },
  {
    term: "Decision cutoff",
    definition:
      "The instant after which a forecast could not have been used. Default 09:00 Europe/London on D−1; configurable because the client's real gate is unknown.",
  },
  {
    term: "Vintage",
    definition:
      "One publication of WINDFOR, identified by its publishTime. The same target hour has many vintages as the forecast is revised.",
  },
  {
    term: "Horizon",
    definition:
      "Target start time minus publish time, in hours. A forecast published at 07:30 for 12:00 the next day has a 28.5 h horizon.",
  },
  {
    term: "FUELHH",
    definition:
      "Elexon's half-hourly generation-by-fuel dataset. WindLens keeps fuelType=WIND and averages the two settlement periods inside each hour.",
  },
  {
    term: "WINDFOR",
    definition:
      "Elexon's national wind generation forecast. In the verified January 2026 feed it is hourly, with eight publication vintages per day.",
  },
  {
    term: "MW and MWh",
    definition:
      "MW is instantaneous or hourly-average power. MWh is energy: an hourly average of 1,000 MW delivers 1,000 MWh over that hour.",
  },
  {
    term: "Over-forecast",
    definition:
      "Forecast above actual. For a buyer this creates shortfall risk: less wind than expected, so more power must be bought elsewhere.",
  },
  {
    term: "nMAE",
    definition:
      "Mean absolute error divided by mean actual output, expressed as a percentage. It avoids installed-capacity data, which is outside the permitted scope.",
  },
  {
    term: "Persistence baseline",
    definition:
      "Hold the last complete hourly actual known at the cutoff flat across the delivery day. Skill = 1 − MAE_forecast / MAE_persistence.",
  },
  {
    term: "Risk buffer",
    definition:
      "An empirical quantile of signed error (forecast − actual). Risk-adjusted wind = max(0, forecast − buffer).",
  },
  {
    term: "Walk-forward",
    definition:
      "A back-test in which each delivery day's buffer is estimated only from outcomes that would have been known before that day. The implementation uses a two-day outcome lag and a seven-day minimum history.",
  },
];

export function AboutPage() {
  const meta = useMeta();

  if (meta.isError) {
    return (
      <ErrorState
        title="The snapshot metadata did not load"
        message={humaniseProblem(meta.error)}
        onRetry={() => void meta.refetch()}
      />
    );
  }
  if (!meta.data) return <PageSkeleton label="Loading methodology" />;

  const data = meta.data;

  return (
    <>
      <PageHeader
        eyebrow="About WindLens · methodology and provenance"
        title="A decision-time desk, not a forecast model"
        description={
          <>
            WindLens does not predict wind. It reconstructs the forecast a buyer could actually
            have used, scores it honestly against outturn, and turns the error distribution into a
            transparent buffer. This page states the assumptions, formulas and limits.
          </>
        }
        actions={
          <>
            <a className="btn" href="/api/docs">
              API reference
            </a>
            <a className="btn btn-ghost" href="/api/v1/meta">
              Raw metadata
            </a>
          </>
        }
      />

      <div className="grid gap-6 lg:grid-cols-[15rem_minmax(0,1fr)]">
        <aside className="lg:sticky lg:top-4 lg:self-start" aria-label="On this page">
          <nav className="card p-3 text-sm">
            <p className="eyebrow px-2 pb-1">On this page</p>
            <ul className="space-y-0.5">
              {[
                ["question", "The question"],
                ["data", "Data and field mapping"],
                ["cutoff", "Cutoff and a worked example"],
                ["resolution", "Hourly evaluation"],
                ["metrics", "Metrics"],
                ["risk", "Risk buffer"],
                ["caveats", "Known caveats"],
                ["quality", "Provenance and quality"],
                ["glossary", "Glossary"],
                ["reproduce", "Reproduce"],
                ["ai", "AI disclosure"],
              ].map(([id, label]) => (
                <li key={id}>
                  <a className="block rounded px-2 py-1 hover:bg-sunken" href={`#${id}`}>
                    {label}
                  </a>
                </li>
              ))}
            </ul>
          </nav>
        </aside>

        <article className="prose-wind min-w-0">
          <section className="card p-5" id="question">
            <h2 className="mt-0 text-2xl">The question</h2>
            <p>
              A day-ahead buyer needs to know how much wind will serve demand tomorrow, and how
              wrong that view is likely to be. Two things matter more than a single point forecast:
              <strong> which vintage was available at the decision instant</strong> and{" "}
              <strong>the direction and tail of the error</strong>.
            </p>
            <p>
              The scope is deliberately narrow. WindLens uses only Elexon <code>FUELHH</code> WIND
              outturn and <code>WINDFOR</code> forecasts. It does not ingest demand, price, weather,
              capacity or other fuels, and it does not train a new forecasting model.
            </p>
          </section>

          <section className="card mt-4 p-5" id="data">
            <h2 className="mt-0 text-2xl">Data and field mapping</h2>
            <div className="table-wrap mt-3" tabIndex={0} role="region" aria-label="Source datasets and field mapping">
              <table className="data-table">
                <caption className="sr-only">Source datasets and field mapping</caption>
                <thead>
                  <tr>
                    <th scope="col">Source</th>
                    <th scope="col">Raw fields used</th>
                    <th scope="col">Normalised fields</th>
                    <th scope="col">Role</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>FUELHH · fuelType=WIND</td>
                    <td>
                      <code>startTime</code>, <code>publishTime</code>, <code>generation</code>
                    </td>
                    <td>
                      <code>start_time</code>, <code>generation_mw</code>
                    </td>
                    <td>Half-hourly actual outturn; duplicate stamps keep the latest publication.</td>
                  </tr>
                  <tr>
                    <td>WINDFOR</td>
                    <td>
                      <code>startTime</code>, <code>publishTime</code>, <code>generation</code>
                    </td>
                    <td>
                      <code>start_time</code>, <code>publish_time</code>,{" "}
                      <code>generation_mw</code>
                    </td>
                    <td>Hourly national wind forecast; each publication is a vintage.</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p className="mt-3">
              Source timestamps are UTC. Delivery days and hour-of-day labels use{" "}
              <strong>Europe/London</strong>; January is GMT, but the code is DST-safe. The verified
              live feed showed WINDFOR publishing eight vintages per day at 02:30, 04:30, 07:30,
              09:30, 11:30, 15:30, 18:30 and 22:30 UTC. That is an observation about this snapshot,
              not a promise about future publication behaviour.
            </p>
            <p>
              FUELHH reports national transmission-metered wind generation. WINDFOR is Elexon's
              national wind forecast. The two series are compared directly; the snapshot shows a
              persistent level difference, and WindLens reports it rather than rescaling either
              series. See <a href="#caveats">Known caveats</a>.
            </p>
          </section>

          <section className="card mt-4 p-5" id="cutoff">
            <h2 className="mt-0 text-2xl">Cutoff and a worked example</h2>
            <p>
              The cutoff for delivery day <em>D</em> is <strong>D−1 at the chosen local time</strong>{" "}
              in Europe/London. The default is 09:00. For each target hour, the selected forecast is
              the row with the greatest <code>publish_time</code> that is{" "}
              <strong>less than or equal to</strong> the cutoff. If no vintage qualifies, the hour is
              omitted and counted; no value is filled from a later publication.
            </p>
            <div className="card-quiet mt-3 p-4 font-mono text-xs leading-relaxed">
              delivery day: 2026-01-15
              <br />
              cutoff: 2026-01-14 09:00 Europe/London = 2026-01-14T09:00:00Z (January, GMT)
              <br />
              target: 2026-01-15T12:00:00Z = 12:00 London
              <br />
              latest publish ≤ cutoff: 2026-01-14T07:30:00Z
              <br />
              horizon: (2026-01-15T12:00Z − 2026-01-14T07:30Z) = 28.5 h
            </div>
            <p className="mt-3">
              The 09:30Z publication is visible in the Revisions explorer but is ineligible for a
              09:00 cutoff. That contrast is the point of the explorer. A publication exactly at the
              cutoff is eligible; the boundary is inclusive.
            </p>
            <p>
              The exact client gate is unknown. 09:00 is a documented, conservative assumption, not
              a claim about the client's actual auction process. The Lab exposes cutoff sensitivity
              at 06:00, 08:00, 09:00, 09:20, 09:50, 10:00 and 12:00 London.
            </p>
          </section>

          <section className="card mt-4 p-5" id="resolution">
            <h2 className="mt-0 text-2xl">Hourly evaluation, without interpolation</h2>
            <p>
              FUELHH is half-hourly; the verified WINDFOR feed is hourly. WindLens evaluates at the
              forecast's native hourly resolution. Each hourly actual is the{" "}
              <strong>arithmetic mean of the two half-hour FUELHH periods</strong> starting at the
              top of the hour. If either half-hour is missing, the hourly actual is missing: it is
              counted and excluded from metrics, never imputed.
            </p>
            <p>
              Energy uses one hour per hourly average, so MWh equals the sum of hourly MW values.
              The API exposes 1 h and 3 h maximum ramps, not a half-hour ramp, because the decision
              series is hourly. The original product brief's half-hour ramp was not implementable
              against an hourly forecast without inventing resolution.
            </p>
          </section>

          <section className="card mt-4 p-5" id="metrics">
            <h2 className="mt-0 text-2xl">Metrics</h2>
            <p>
              Sign convention: <code>error = forecast − actual</code>. Positive is over-forecast.
            </p>
            <div className="table-wrap mt-3" tabIndex={0} role="region" aria-label="Metric definitions">
              <table className="data-table">
                <caption className="sr-only">Metric definitions</caption>
                <thead>
                  <tr>
                    <th scope="col">Metric</th>
                    <th scope="col">Definition</th>
                    <th scope="col">Why it is here</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>MAE</td>
                    <td>mean(|error|)</td>
                    <td>Typical absolute miss in MW.</td>
                  </tr>
                  <tr>
                    <td>RMSE</td>
                    <td>sqrt(mean(error²))</td>
                    <td>Penalises large misses more heavily.</td>
                  </tr>
                  <tr>
                    <td>Bias</td>
                    <td>mean(error)</td>
                    <td>Direction: over- or under-forecast on average.</td>
                  </tr>
                  <tr>
                    <td>nMAE</td>
                    <td>MAE / mean(actual) × 100</td>
                    <td>Scale-free error without installed capacity.</td>
                  </tr>
                  <tr>
                    <td>P50/P90/P95 |error|</td>
                    <td>empirical quantiles of |error|</td>
                    <td>Tail size in MW.</td>
                  </tr>
                  <tr>
                    <td>Shortfall</td>
                    <td>max(0, forecast − actual)</td>
                    <td>Buyer-relevant over-forecast tail.</td>
                  </tr>
                  <tr>
                    <td>Over-forecast share</td>
                    <td>share of hours with error &gt; 0</td>
                    <td>Frequency, not just magnitude.</td>
                  </tr>
                  <tr>
                    <td>MAPE</td>
                    <td>mean(|error| / actual) for actual ≥ 500 MW</td>
                    <td>Reported but guarded; unstable at low output.</td>
                  </tr>
                  <tr>
                    <td>Correlation</td>
                    <td>Pearson correlation of forecast and actual</td>
                    <td>Shape agreement, independent of level bias.</td>
                  </tr>
                  <tr>
                    <td>Skill</td>
                    <td>1 − MAE_forecast / MAE_persistence</td>
                    <td>Value added over a defensible naive baseline.</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p className="mt-3">
              Missing actuals and forecasts are excluded pairwise and counted. Correlation is
              undefined rather than one when either series has zero variance. All percentile
              calculations use linear interpolation.
            </p>
          </section>

          <section className="card mt-4 p-5" id="risk">
            <h2 className="mt-0 text-2xl">Risk buffer and calibration</h2>
            <p>
              For level <em>p</em>, the buffer is the empirical <em>p</em>-quantile of historical
              signed error. The risk-adjusted forecast is <code>max(0, forecast − buffer)</code>.
              This is intentionally simple: it is an empirical margin, not a probabilistic
              guarantee, and it is not a trading recommendation.
            </p>
            <p>
              In-sample quantiles can flatter themselves. WindLens therefore also runs a
              walk-forward back-test. For each evaluated delivery day, the buffer is estimated only
              from earlier delivery days whose outcomes would have been known with a two-day lag;
              the first seven history days are skipped. Empirical coverage is the share of hours in
              which actual output met or exceeded the risk-adjusted forecast. The UI compares that
              with the nominal target and shows the shortfall.
            </p>
            <p>
              Results from this snapshot are deliberately reported without a victory lap: coverage
              can miss the target, and a 31-day winter window is not enough to claim stable
              calibration across seasons.
            </p>
          </section>

          <section className="card mt-4 p-5" id="caveats">
            <h2 className="mt-0 text-2xl">Known caveats</h2>
            <ul>
              <li>
                <strong>Level bias.</strong> The verified snapshot shows a large positive mean bias
                in WINDFOR versus FUELHH. Timestamp shifts and DST handling were checked; they do
                not explain it. WindLens reports measured error and does not rescale the forecast.
              </li>
              <li>
                <strong>31 delivery days, one winter.</strong> The accuracy and calibration evidence
                covers 2 January–1 February 2026 only. Seasonality, regime change and extreme events
                are not represented.
              </li>
              <li>
                <strong>Scope difference.</strong> FUELHH WIND is transmission-metered national wind
                generation; WINDFOR is Elexon's national wind forecast. Any difference in
                definition is a limitation of the comparison, not something the UI can correct.
              </li>
              <li>
                <strong>Assumed cutoff.</strong> The client's real decision gate is unknown. Results
                are conditional on the selected cutoff, and the sensitivity table shows that
                conditioning matters.
              </li>
              <li>
                <strong>In-sample headline buffer.</strong> The headline empirical quantile uses the
                same window it describes. The walk-forward back-test is the honest calibration
                check.
              </li>
              <li>
                <strong>No demand, price or capacity.</strong> The demand input is a user-entered
                what-if. Residual-to-procure is arithmetic, not a market optimisation.
              </li>
              <li>
                <strong>Not financial advice.</strong> This is an analytical decision aid built for a
                take-home evaluation.
              </li>
            </ul>
          </section>

          <section className="card mt-4 p-5" id="quality">
            <h2 className="mt-0 text-2xl">Provenance and data quality</h2>
            <dl className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              <div className="card-quiet p-3">
                <dt className="text-[11px] uppercase tracking-wide text-muted">Fingerprint</dt>
                <dd className="font-mono text-sm">{data.data.fingerprint}</dd>
              </div>
              <div className="card-quiet p-3">
                <dt className="text-[11px] uppercase tracking-wide text-muted">Snapshot ingested</dt>
                <dd className="text-sm">{formatDateTime(data.data.generated_at)}</dd>
              </div>
              <div className="card-quiet p-3">
                <dt className="text-[11px] uppercase tracking-wide text-muted">Source</dt>
                <dd className="text-sm">{data.data.source}</dd>
              </div>
              <div className="card-quiet p-3">
                <dt className="text-[11px] uppercase tracking-wide text-muted">Datasets</dt>
                <dd className="text-sm">{data.data.datasets.join(" · ")}</dd>
              </div>
              <div className="card-quiet p-3">
                <dt className="text-[11px] uppercase tracking-wide text-muted">Scope mode</dt>
                <dd className="text-sm">{data.scope.mode}</dd>
              </div>
              <div className="card-quiet p-3">
                <dt className="text-[11px] uppercase tracking-wide text-muted">Delivery days</dt>
                <dd className="text-sm">
                  {data.scope.delivery_dates.start} → {data.scope.delivery_dates.end} (
                  {data.scope.delivery_days})
                </dd>
              </div>
            </dl>
            <div className="mt-3 table-wrap" tabIndex={0} role="region" aria-label="Data quality counters">
              <table className="data-table">
                <caption className="sr-only">Data quality counters</caption>
                <thead>
                  <tr>
                    <th scope="col">Counter</th>
                    <th scope="col" className="text-right">
                      Value
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(data.data.quality).map(([key, value]) => (
                    <tr key={key}>
                      <td>{key.replaceAll("_", " ")}</td>
                      <td className="num">{formatNumber(value ?? null)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="mt-3 text-sm">
              Snapshot hash shown throughout the UI:{" "}
              <span className="font-mono">{shortHash(data.data.fingerprint)}</span>. The processed
              files are committed, so the app runs without outbound network access. Rebuilding from
              cached raw chunks is byte-deterministic apart from the ingestion timestamp.
            </p>
          </section>

          <section className="card mt-4 p-5" id="glossary">
            <h2 className="mt-0 text-2xl">Glossary</h2>
            <dl className="mt-3 space-y-3">
              {GLOSSARY.map((item) => (
                <div key={item.term}>
                  <dt className="font-semibold text-ink">{item.term}</dt>
                  <dd className="text-sm text-soft">{item.definition}</dd>
                </div>
              ))}
            </dl>
          </section>

          <section className="card mt-4 p-5" id="reproduce">
            <h2 className="mt-0 text-2xl">Reproduce the numbers</h2>
            <p>
              The repository runs the same code locally, in Docker and in the API deployment. The UI
              reads the committed snapshot; the ingestion CLI is separate and is not exposed in
              production.
            </p>
            <pre className="overflow-auto rounded-lg bg-sunken p-3 text-xs">
              {`make install          # backend venv + frontend deps
make dev              # FastAPI on :8000 and Vite on :5173
make test             # backend pytest + frontend vitest
make lint             # ruff, mypy, eslint, tsc
docker compose up --build   # UI on :8080, API on :8000`}
            </pre>
            <p>
              The API contract is at <a href="/api/docs">/api/docs</a> and the machine-readable
              schema at <a href="/api/openapi.json">/api/openapi.json</a>. Accuracy CSVs are served
              from <code>/api/v1/export/accuracy.csv</code>; the desk CSV from{" "}
              <code>/api/v1/export/decision-view.csv</code>.
            </p>
            <p>
              <Link className="underline" to="/lab">
                Open the Accuracy Lab
              </Link>{" "}
              to see every statistic in context.
            </p>
          </section>

          <section className="card mt-4 p-5" id="ai">
            <h2 className="mt-0 text-2xl">AI disclosure</h2>
            <p>
              WindLens was implemented with an AI coding agent (DeepSeek V4.1 Flash via OpenCode)
              working under explicit human direction on scope, data-source verification, product
              choices and review. The agent wrote the application, tests, analysis and documentation
              drafts. It did not invent the dataset: every processed row comes from a live Elexon
              pull recorded in the committed manifest, and every displayed number is computed from
              that snapshot by the same code the tests exercise.
            </p>
            <p>
              The human owner remains responsible for reviewing the output, deciding the anonymity
              posture, recording the walkthrough video, and making the final submission. Known
              limitations are listed above rather than smoothed over.
            </p>
          </section>

          <p className="mt-6 text-xs text-muted">
            WindLens v{data.version} · {data.product} · timezone {data.timezone} · default cutoff{" "}
            {data.default_cutoff}. <a href="#main">Back to top</a>.
          </p>
        </article>
      </div>
    </>
  );
}
