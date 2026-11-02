import { Link, useLocation } from "react-router-dom";

import { PageHeader } from "../components/Metric";

export function NotFoundPage() {
  const location = useLocation();

  return (
    <>
      <PageHeader
        eyebrow="404 · no such view"
        title="This page is outside the snapshot"
        description={
          <>
            WindLens has four views: the Decision Desk, the Accuracy Lab, the Revisions explorer
            and the methodology page. The address <code>{location.pathname}</code> is not one of
            them.
          </>
        }
      />
      <section className="card p-6" aria-labelledby="not-found-title">
        <h2 className="text-2xl" id="not-found-title">
          Try one of these instead
        </h2>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <Link className="card-quiet block p-4 no-underline" to="/desk">
            <p className="eyebrow">Decision Desk</p>
            <p className="mt-1 font-display text-xl text-ink">Tomorrow&apos;s wind, at the cutoff</p>
            <p className="mt-1 text-sm text-soft">
              The selected forecast, the risk-adjusted view and the hourly table for one delivery
              day.
            </p>
          </Link>
          <Link className="card-quiet block p-4 no-underline" to="/lab">
            <p className="eyebrow">Accuracy Lab</p>
            <p className="mt-1 font-display text-xl text-ink">How wrong, and in which direction</p>
            <p className="mt-1 text-sm text-soft">
              Errors by day, horizon and hour, plus the buffer calibration back-test.
            </p>
          </Link>
          <Link className="card-quiet block p-4 no-underline" to="/revisions">
            <p className="eyebrow">Revisions explorer</p>
            <p className="mt-1 font-display text-xl text-ink">Which vintage was in hand?</p>
            <p className="mt-1 text-sm text-soft">
              Every WINDFOR publication for one target hour, with the cutoff drawn in.
            </p>
          </Link>
          <Link className="card-quiet block p-4 no-underline" to="/about">
            <p className="eyebrow">Methodology</p>
            <p className="mt-1 font-display text-xl text-ink">Assumptions, formulas and limits</p>
            <p className="mt-1 text-sm text-soft">
              Data mapping, the cutoff rule, metric definitions, caveats and provenance.
            </p>
          </Link>
        </div>
        <p className="mt-4 text-xs text-muted">
          If a link inside WindLens brought you here, that is a bug worth reporting.
        </p>
      </section>
    </>
  );
}
