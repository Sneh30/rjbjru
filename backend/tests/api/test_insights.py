"""Contract tests for the committed insight artefacts.

These tests close the drift gap that a prose-only INSIGHTS.md leaves open: the
JSON payloads are compared with real API responses from the committed snapshot,
and the earliest-vintage comparison is recomputed with the same domain code.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.data.repository import Repository
from app.domain.baseline import baseline_summary, persistence_for_selected
from app.domain.join import join_selected_actuals
from app.domain.metrics import compute_metrics
from app.domain.selection import select_earliest_forecasts
from app.services.formatting import horizon_stats, metrics_payload

BASE = "/api/v1"
WINDOW = {"start": "2026-01-02", "end": "2026-02-01"}
DEFAULT_CUTOFF = "09:00"
DOCS = Path(__file__).resolve().parents[3] / "docs"


@pytest.fixture(scope="module")
def insights() -> dict[str, Any]:
    """Load the committed insight payload once."""
    path = DOCS / "insights.json"
    assert path.exists(), "docs/insights.json is missing; run 'make insights'"
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    assert isinstance(payload, dict)
    return payload


def _get(client: TestClient, path: str, **params: Any) -> dict[str, Any]:
    """GET an API path and return the JSON object."""
    response = client.get(path, params=params)
    assert response.status_code == 200, response.text
    body = response.json()
    assert isinstance(body, dict)
    return body


def test_summary_payload_matches_live_api(client: TestClient, insights: dict[str, Any]) -> None:
    body = _get(
        client,
        f"{BASE}/accuracy/summary",
        **WINDOW,
        cutoff=DEFAULT_CUTOFF,
    )
    assert body == insights["summary"]


def test_horizon_payload_matches_live_api(client: TestClient, insights: dict[str, Any]) -> None:
    body = _get(
        client,
        f"{BASE}/accuracy/by-horizon",
        **WINDOW,
        cutoff=DEFAULT_CUTOFF,
    )
    assert body == insights["horizon"]


def test_hours_payload_matches_live_api(client: TestClient, insights: dict[str, Any]) -> None:
    body = _get(
        client,
        f"{BASE}/accuracy/by-hour",
        **WINDOW,
        cutoff=DEFAULT_CUTOFF,
    )
    assert body == insights["hours"]


def test_levels_payload_matches_live_api(client: TestClient, insights: dict[str, Any]) -> None:
    body = _get(
        client,
        f"{BASE}/accuracy/by-level",
        **WINDOW,
        cutoff=DEFAULT_CUTOFF,
        basis="actual",
        bins=5,
    )
    assert body == insights["levels"]


def test_daily_payload_matches_live_api(client: TestClient, insights: dict[str, Any]) -> None:
    body = _get(
        client,
        f"{BASE}/accuracy/daily",
        **WINDOW,
        cutoff=DEFAULT_CUTOFF,
    )
    assert body == insights["daily"]


def test_worst_payload_matches_live_api(client: TestClient, insights: dict[str, Any]) -> None:
    body = _get(
        client,
        f"{BASE}/accuracy/worst",
        **WINDOW,
        cutoff=DEFAULT_CUTOFF,
        metric="mae",
        n=5,
    )
    assert body == insights["worst"]


def test_cutoff_sensitivity_matches_live_api(client: TestClient, insights: dict[str, Any]) -> None:
    body = _get(client, f"{BASE}/accuracy/cutoff-sensitivity", **WINDOW)
    assert body == insights["cutoff_sensitivity"]


def test_risk_buffer_matches_live_api(client: TestClient, insights: dict[str, Any]) -> None:
    body = _get(
        client,
        f"{BASE}/risk/buffer",
        **WINDOW,
        cutoff=DEFAULT_CUTOFF,
        levels="0.5,0.75,0.9,0.95",
    )
    assert body == insights["risk"]["buffer"]


@pytest.mark.parametrize("level", ["0.5", "0.75", "0.9", "0.95"])
def test_risk_backtests_match_live_api(
    client: TestClient,
    insights: dict[str, Any],
    level: str,
) -> None:
    body = _get(
        client,
        f"{BASE}/risk/backtest",
        **WINDOW,
        cutoff=DEFAULT_CUTOFF,
        level=level,
        min_history_days=7,
    )
    assert body == insights["risk"]["backtests"][level]


def test_earliest_vintage_payload_matches_domain_recomputation(
    repository: Repository,
    settings: Settings,
    insights: dict[str, Any],
) -> None:
    earliest = select_earliest_forecasts(repository.forecasts(), settings.default_cutoff)
    joined = join_selected_actuals(earliest, repository.hourly_actuals())
    joined = persistence_for_selected(joined, repository.hourly_actuals(), settings.default_cutoff)
    start = pd.Timestamp(WINDOW["start"]).date()
    end = pd.Timestamp(WINDOW["end"]).date()
    window = joined.loc[(joined["delivery_date"] >= start) & (joined["delivery_date"] <= end)]
    metrics = compute_metrics(window, mape_min_actual_mw=settings.mape_min_actual_mw)
    payload = metrics_payload(metrics)
    payload["n_missing_forecast"] = 0
    committed = insights["derived"]["vintage_value"]["earliest"]
    assert payload == committed["metrics"]
    assert horizon_stats(window["horizon_h"]) == committed["horizon_h"]
    baseline = baseline_summary(window)
    assert baseline.n == committed["baseline"]["n"]
    assert round(baseline.mae_mw or 0.0, 1) == committed["baseline"]["mae_mw"]


def test_insight_snapshot_matches_health_and_meta(
    client: TestClient, insights: dict[str, Any]
) -> None:
    health = _get(client, f"{BASE}/health")
    meta = _get(client, f"{BASE}/meta")
    data = insights["derived"]["data"]
    assert data["snapshot"]["fingerprint"] == health["data_fingerprint"]
    assert data["snapshot"]["fingerprint"] == meta["data"]["fingerprint"]
    assert data["snapshot"]["manifest_generated_at"] == meta["data"]["generated_at"]
    assert data["actuals"]["rows"] == meta["data"]["coverage"]["actual_rows"]
    assert data["actuals"]["hourly_rows"] == meta["data"]["coverage"]["hourly_actual_periods"]
    assert data["forecasts"]["rows"] == meta["data"]["coverage"]["forecast_rows"]
    assert data["forecasts"]["vintages"] == meta["data"]["coverage"]["forecast_vintages"]
    assert data["forecasts"]["target_start"] == meta["data"]["coverage"]["forecast_target_start"]
    assert data["forecasts"]["target_end"] == meta["data"]["coverage"]["forecast_target_end"]


def test_markdown_contains_generated_headline_numbers(insights: dict[str, Any]) -> None:
    markdown = (DOCS / "INSIGHTS.md").read_text(encoding="utf-8")
    metrics = insights["summary"]["metrics"]
    assert f"{metrics['mae_mw']:,.1f} MW" in markdown
    assert f"{metrics['nmae_pct']:,.2f}%" in markdown
    assert f"{metrics['bias_mw']:+,.1f} MW" in markdown
    assert "85.0%" in markdown
    assert "4,097.9 MW" in markdown
    default_risk = insights["derived"]["risk_summary"]["default"]
    assert f"{default_risk['walk_forward_coverage'] * 100:,.1f}%" in markdown
    for heading in (
        "## 1. Headline metrics at the default cutoff",
        "## 2. Error direction and shortfall",
        "## 3. Horizon and lead time",
        "## 4. Best and worst hours of the day",
        "## 5. Wind-level analysis",
        "## 6. Worst delivery days and demo-day picks",
        "## 7. Cutoff sensitivity",
        "## 8. Vintage value: latest, earliest and persistence",
        "## 9. Risk-buffer calibration",
        "## 10. Data coverage and provenance",
    ):
        assert heading in markdown
