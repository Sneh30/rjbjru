import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";

import backtest from "./fixtures/backtest.json";
import buffer from "./fixtures/buffer.json";
import daily from "./fixtures/daily.json";
import decision from "./fixtures/decision.json";
import decisionNoActuals from "./fixtures/decision_no_actuals.json";
import distribution from "./fixtures/distribution.json";
import health from "./fixtures/health.json";
import horizon from "./fixtures/horizon.json";
import hours from "./fixtures/hours.json";
import levelsActual from "./fixtures/levels_actual.json";
import levelsForecast from "./fixtures/levels_forecast.json";
import meta from "./fixtures/meta.json";
import revisions from "./fixtures/revisions.json";
import sensitivity from "./fixtures/sensitivity.json";
import summary from "./fixtures/summary.json";
import worstBias from "./fixtures/worst_bias.json";
import worstMae from "./fixtures/worst_mae.json";

export {
  backtest,
  buffer,
  daily,
  decision,
  decisionNoActuals,
  distribution,
  health,
  horizon,
  hours,
  levelsActual,
  levelsForecast,
  meta,
  revisions,
  sensitivity,
  summary,
  worstBias,
  worstMae,
};

export const fixtures = {
  backtest,
  buffer,
  daily,
  decision,
  decisionNoActuals,
  distribution,
  health,
  horizon,
  hours,
  levelsActual,
  levelsForecast,
  meta,
  revisions,
  sensitivity,
  summary,
  worstBias,
  worstMae,
} as const;

export const handlers = [
  http.get("/api/v1/health", () => HttpResponse.json(health)),
  http.get("/api/v1/meta", () => HttpResponse.json(meta)),
  http.get("/api/v1/decision-view", ({ request }) => {
    const includeActuals = new URL(request.url).searchParams.get("include_actuals") === "true";
    return HttpResponse.json(includeActuals ? decision : decisionNoActuals);
  }),
  http.get("/api/v1/revisions", () => HttpResponse.json(revisions)),
  http.get("/api/v1/accuracy/summary", () => HttpResponse.json(summary)),
  http.get("/api/v1/accuracy/daily", () => HttpResponse.json(daily)),
  http.get("/api/v1/accuracy/by-horizon", () => HttpResponse.json(horizon)),
  http.get("/api/v1/accuracy/by-hour", () => HttpResponse.json(hours)),
  http.get("/api/v1/accuracy/by-level", ({ request }) => {
    const basis = new URL(request.url).searchParams.get("basis");
    return HttpResponse.json(basis === "forecast" ? levelsForecast : levelsActual);
  }),
  http.get("/api/v1/accuracy/distribution", () => HttpResponse.json(distribution)),
  http.get("/api/v1/accuracy/worst", ({ request }) => {
    const metric = new URL(request.url).searchParams.get("metric");
    return HttpResponse.json(metric === "bias" ? worstBias : worstMae);
  }),
  http.get("/api/v1/accuracy/cutoff-sensitivity", () => HttpResponse.json(sensitivity)),
  http.get("/api/v1/risk/buffer", () => HttpResponse.json(buffer)),
  http.get("/api/v1/risk/backtest", () => HttpResponse.json(backtest)),
];

export const server = setupServer(...handlers);
