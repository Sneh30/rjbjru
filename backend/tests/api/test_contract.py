"""HTTP contract tests against the committed real snapshot.

These tests assert externally visible behaviour: status codes, RFC 7807 bodies,
response fields, caching, CORS and CSV shape. They are the API contract, not a
duplicate of the domain tests.
"""

from __future__ import annotations

import csv
import io
from typing import Any

import pytest
from fastapi.testclient import TestClient

BASE = "/api/v1"


def _json(response: Any) -> dict[str, Any]:
    assert response.headers["content-type"].startswith("application/json")
    payload = response.json()
    assert isinstance(payload, dict)
    return payload


def _assert_problem(response: Any, status: int, slug: str) -> dict[str, Any]:
    assert response.status_code == status
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["type"].endswith(slug)
    assert body["status"] == status
    assert body["detail"]
    assert body["instance"].startswith(BASE)
    return body


def test_health_reports_the_snapshot_identity_and_is_not_cached(client: TestClient) -> None:
    response = client.get(f"{BASE}/health")
    body = _json(response)
    assert response.status_code == 200
    assert body["status"] == "ok"
    assert body["version"] == "1.0.0"
    assert body["data_fingerprint"] == "331dc8acb133704a"
    assert body["actual_rows"] == 1536
    assert body["forecast_rows"] == 19856
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-request-id"]


def test_security_headers_are_present_on_every_api_response(client: TestClient) -> None:
    response = client.get(f"{BASE}/meta")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["cross-origin-resource-policy"] == "same-origin"
    assert "camera=()" in response.headers["permissions-policy"]


def test_request_id_is_echoed_and_bounded(client: TestClient) -> None:
    response = client.get(f"{BASE}/meta", headers={"X-Request-ID": "abc123"})
    assert response.headers["x-request-id"] == "abc123"
    generated = client.get(f"{BASE}/meta")
    assert len(generated.headers["x-request-id"]) == 32
    too_long = client.get(f"{BASE}/meta", headers={"X-Request-ID": "x" * 300})
    assert len(too_long.headers["x-request-id"]) == 128


def test_meta_describes_scope_defaults_and_provenance(client: TestClient) -> None:
    body = _json(client.get(f"{BASE}/meta"))
    assert body["product"] == "WindLens"
    assert body["timezone"] == "Europe/London"
    assert body["default_cutoff"] == "09:00"
    assert body["cutoff_grid"] == ["06:00", "08:00", "09:00", "09:20", "09:50", "10:00", "12:00"]
    assert body["scope"]["mode"] == "decision_date"
    assert body["scope"]["decision_dates"] == {"start": "2026-01-01", "end": "2026-01-31"}
    assert body["scope"]["delivery_dates"] == {"start": "2026-01-02", "end": "2026-02-01"}
    assert len(body["available_delivery_dates"]) == 31
    assert body["available_delivery_dates"][0] == "2026-01-02"
    assert body["available_delivery_dates"][-1] == "2026-02-01"
    assert body["horizon_buckets_h"] == [0.0, 6.0, 12.0, 18.0, 24.0, 36.0, 48.0, 72.0]
    assert body["constants"]["period_minutes"] == 30
    assert body["constants"]["forecast_period_minutes"] == 60
    assert body["data"]["fingerprint"] == "331dc8acb133704a"
    assert body["data"]["generated_at"].endswith("Z")
    assert body["data"]["coverage"]["actual_rows"] == 1536
    assert body["data"]["quality"]["actual_missing_rows"] == 0
    assert "FUELHH" in body["methodology"]["resolution_note"]
    assert "AI" in body["ai_disclosure"]


def test_decision_view_defaults_to_decision_time_only(client: TestClient) -> None:
    response = client.get(
        f"{BASE}/decision-view", params={"delivery_date": "2026-01-15", "cutoff": "09:00"}
    )
    body = _json(response)
    assert response.status_code == 200
    assert body["delivery_date"] == "2026-01-15"
    assert body["resolution_minutes"] == 60
    assert body["cutoff"] == {
        "local": "2026-01-14T09:00:00+00:00",
        "utc": "2026-01-14T09:00:00Z",
        "time": "09:00",
        "timezone": "Europe/London",
    }
    assert len(body["points"]) == 24
    assert all("actual_mw" not in point for point in body["points"])
    assert all(point["horizon_h"] >= 16.5 for point in body["points"])
    assert body["coverage"]["expected_periods"] == 24
    assert body["coverage"]["with_forecast"] == 24
    assert body["coverage"]["with_actual"] == 24
    assert body["coverage"]["missing_forecast_periods"] == []
    assert body["summary"]["horizon_h"]["min"] == 16.5
    assert body["summary"]["horizon_h"]["max"] == 39.5
    assert body["summary"]["mean_mw"] > 0
    assert body["summary"]["energy_mwh"] > 0
    assert body["summary"]["latest_publish_time"] <= body["cutoff"]["utc"]
    assert "day_metrics" not in body


def test_decision_view_hindsight_is_opt_in_and_reconciles(client: TestClient) -> None:
    body = _json(
        client.get(
            f"{BASE}/decision-view",
            params={
                "delivery_date": "2026-01-15",
                "cutoff": "09:00",
                "include_actuals": "true",
            },
        )
    )
    points = body["points"]
    assert all("actual_mw" in point for point in points)
    for point in points:
        assert point["error_mw"] == pytest.approx(
            point["forecast_mw"] - point["actual_mw"], abs=0.11
        )
        assert point["shortfall_mw"] == pytest.approx(max(0.0, point["error_mw"]), abs=0.11)
    metrics = body["day_metrics"]
    assert metrics["n"] == 24
    assert metrics["n_missing_actual"] == 0
    assert metrics["n_missing_forecast"] == 0
    assert metrics["mae_mw"] == pytest.approx(
        sum(abs(point["error_mw"]) for point in points) / 24, abs=0.2
    )


def test_decision_view_is_available_at_scope_edges(client: TestClient) -> None:
    first = client.get(f"{BASE}/decision-view", params={"delivery_date": "2026-01-02"})
    last = client.get(f"{BASE}/decision-view", params={"delivery_date": "2026-02-01"})
    assert first.status_code == 200
    assert last.status_code == 200
    assert len(first.json()["points"]) == 24
    assert len(last.json()["points"]) == 24


@pytest.mark.parametrize("day", ["2026-01-01", "2026-02-02", "2025-12-31"])
def test_out_of_scope_delivery_dates_return_404_problem_json(client: TestClient, day: str) -> None:
    response = client.get(f"{BASE}/decision-view", params={"delivery_date": day})
    body = _assert_problem(response, 404, "out-of-scope")
    assert body["valid_range"] == {"start": "2026-01-02", "end": "2026-02-01"}


@pytest.mark.parametrize(
    "params",
    [
        {"delivery_date": "not-a-date"},
        {"delivery_date": "2026-01-15", "cutoff": "9:00"},
        {"delivery_date": "2026-01-15", "cutoff": "24:00"},
        {"delivery_date": "2026-01-15", "include_actuals": "maybe"},
        {"delivery_date": "2026-01-15", "unknown": "1"},
        {},
    ],
)
def test_invalid_decision_queries_return_422(client: TestClient, params: dict[str, str]) -> None:
    body = _assert_problem(client.get(f"{BASE}/decision-view", params=params), 422, "validation")
    assert body["errors"]


def test_revisions_mark_the_cutoff_and_never_select_a_post_cutoff_vintage(
    client: TestClient,
) -> None:
    body = _json(
        client.get(
            f"{BASE}/revisions",
            params={"target_time": "2026-01-15T12:00:00Z", "cutoff": "09:00"},
        )
    )
    assert body["target_time"] == "2026-01-15T12:00:00Z"
    assert body["delivery_date"] == "2026-01-15"
    assert body["selected_publish_time"] <= body["cutoff"]["utc"]
    assert body["selected_forecast_mw"] is not None
    assert body["actual_mw"] is not None
    assert body["error_mw"] == pytest.approx(
        body["selected_forecast_mw"] - body["actual_mw"], abs=0.11
    )
    assert len(body["vintages"]) >= 2
    for vintage in body["vintages"]:
        if vintage["selected"]:
            assert vintage["eligible"] is True
            assert vintage["publish_time"] == body["selected_publish_time"]
    assert any(vintage["eligible"] is False for vintage in body["vintages"])
    assert body["eligibility_note"].startswith("eligible means")
    assert body["lookahead_hours"] == 6


def test_revisions_accept_a_delivery_date_and_one_based_hour(client: TestClient) -> None:
    by_period = _json(
        client.get(
            f"{BASE}/revisions",
            params={"delivery_date": "2026-01-15", "period": 13, "cutoff": "09:00"},
        )
    )
    by_time = _json(
        client.get(
            f"{BASE}/revisions",
            params={"target_time": "2026-01-15T12:00:00Z", "cutoff": "09:00"},
        )
    )
    assert by_period["target_time"] == by_time["target_time"] == "2026-01-15T12:00:00Z"
    assert by_period["selected_forecast_mw"] == by_time["selected_forecast_mw"]


@pytest.mark.parametrize(
    "params",
    [
        {"target_time": "2026-01-15T12:00:00Z", "delivery_date": "2026-01-15", "period": 13},
        {"delivery_date": "2026-01-15"},
        {"period": 13},
        {"delivery_date": "2026-01-15", "period": 0},
        {"delivery_date": "2026-01-15", "period": 25},
        {"target_time": "2026-01-15", "period": 13},
    ],
)
def test_invalid_revision_queries_return_422(client: TestClient, params: dict[str, object]) -> None:
    _assert_problem(client.get(f"{BASE}/revisions", params=params), 422, "validation")


def test_revisions_reject_non_hourly_and_out_of_scope_targets(client: TestClient) -> None:
    non_hourly = client.get(f"{BASE}/revisions", params={"target_time": "2026-01-15T12:30:00Z"})
    body = _assert_problem(non_hourly, 404, "out-of-scope")
    assert body["resolution_minutes"] == 60

    out_of_scope = client.get(f"{BASE}/revisions", params={"target_time": "2026-03-01T12:00:00Z"})
    _assert_problem(out_of_scope, 404, "out-of-scope")


def test_accuracy_summary_locks_the_headline_numbers(client: TestClient) -> None:
    body = _json(client.get(f"{BASE}/accuracy/summary"))
    assert body["window"] == {
        "start": "2026-01-02",
        "end": "2026-02-01",
        "delivery_days": 31,
        "expected_periods": 744,
    }
    assert body["cutoff"] == "09:00"
    metrics = body["metrics"]
    assert metrics["n"] == 744
    assert metrics["n_missing_actual"] == 0
    assert metrics["n_missing_forecast"] == 0
    assert metrics["mae_mw"] == 2038.9
    assert metrics["rmse_mw"] == 2504.8
    assert metrics["bias_mw"] == 1747.9
    assert metrics["nmae_pct"] == 18.07
    assert metrics["over_forecast_share"] == 0.85
    assert metrics["shortfall_p90_mw"] == 4097.9
    assert metrics["p95_abs_mw"] == 5283.4
    assert metrics["correlation"] == 0.93
    assert body["baseline"]["mae_mw"] == 4125.9
    assert body["baseline"]["skill"] == 0.51
    assert body["baseline"]["n"] == 744
    assert body["horizon_h"] == {"min": 16.5, "mean": 28.0, "max": 39.5}
    assert body["coverage"] == {
        "expected_periods": 744,
        "with_forecast": 744,
        "with_actual": 744,
        "missing_forecast_periods": [],
        "missing_actual_periods": [],
        "coverage_pct": 100.0,
    }


def test_accuracy_summary_respects_an_explicit_window(client: TestClient) -> None:
    body = _json(
        client.get(f"{BASE}/accuracy/summary", params={"start": "2026-01-15", "end": "2026-01-15"})
    )
    assert body["window"]["delivery_days"] == 1
    assert body["window"]["expected_periods"] == 24
    assert body["metrics"]["n"] == 24


def test_daily_series_covers_every_delivery_day(client: TestClient) -> None:
    body = _json(client.get(f"{BASE}/accuracy/daily"))
    assert body["start"] == "2026-01-02"
    assert body["end"] == "2026-02-01"
    assert len(body["days"]) == 31
    assert [row["delivery_date"] for row in body["days"]] == [
        *(f"2026-01-{day:02d}" for day in range(2, 32)),
        "2026-02-01",
    ]
    assert all(row["n"] == 24 for row in body["days"])
    assert all(row["mae_mw"] is not None for row in body["days"])


def test_horizon_breakdown_has_a_stable_open_ended_bucket(client: TestClient) -> None:
    body = _json(client.get(f"{BASE}/accuracy/by-horizon"))
    assert len(body["buckets"]) == 8
    assert [bucket["label"] for bucket in body["buckets"]] == [
        "0-6 h",
        "6-12 h",
        "12-18 h",
        "18-24 h",
        "24-36 h",
        "36-48 h",
        "48-72 h",
        "72+ h",
    ]
    assert body["buckets"][-1]["to_h"] is None
    assert body["decision_band_h"] == {"min": 16.5, "max": 39.5}
    assert body["dropped_negative_horizon"] > 0
    assert body["n_vintage_rows"] > 0


def test_hour_and_level_breakdowns_cover_all_rows(client: TestClient) -> None:
    hours = _json(client.get(f"{BASE}/accuracy/by-hour"))["hours"]
    assert [row["hour"] for row in hours] == list(range(24))
    assert sum(row["n"] for row in hours) == 744
    assert all(row["label"].endswith(":00") for row in hours)

    levels = _json(client.get(f"{BASE}/accuracy/by-level"))
    assert levels["basis"] == "actual"
    assert len(levels["bins"]) == 5
    assert sum(row["n"] for row in levels["bins"]) == 744
    assert levels["bins"][0]["label"].startswith("Q1")


def test_distribution_summarises_every_valid_error(client: TestClient) -> None:
    body = _json(client.get(f"{BASE}/accuracy/distribution"))
    assert len(body["histogram"]) == 20
    assert sum(bin_["count"] for bin_ in body["histogram"]) == 744
    assert body["scatter_total"] == 744
    assert len(body["scatter"]) == 744
    assert body["scatter_limit"] == 1500
    assert body["quantiles"]["p50"] == 1592.0
    assert body["quantiles"]["shortfall_p90"] == 4097.9


def test_worst_ranking_and_cutoff_sensitivity(client: TestClient) -> None:
    worst = _json(client.get(f"{BASE}/accuracy/worst", params={"n": 3}))
    assert len(worst["days"]) == 3
    assert len(worst["periods"]) == 3
    assert worst["metric"] == "mae"
    assert worst["days"][0]["mae_mw"] >= worst["days"][1]["mae_mw"]

    by_bias = _json(client.get(f"{BASE}/accuracy/worst", params={"n": 2, "metric": "bias"}))
    assert by_bias["metric"] == "bias"

    sensitivity = _json(client.get(f"{BASE}/accuracy/cutoff-sensitivity"))
    assert [row["cutoff"] for row in sensitivity["rows"]] == [
        "06:00",
        "08:00",
        "09:00",
        "09:20",
        "09:50",
        "10:00",
        "12:00",
    ]
    assert all(row["n"] <= 744 for row in sensitivity["rows"])
    assert sensitivity["rows"][2]["n"] == 744


def test_risk_buffer_and_walk_forward_are_explicit_about_causality(client: TestClient) -> None:
    buffer = _json(client.get(f"{BASE}/risk/buffer"))
    assert buffer["basis"] == "in_sample"
    assert [point["level"] for point in buffer["overall"]] == [0.5, 0.75, 0.9, 0.95]
    assert buffer["overall"][2]["buffer_mw"] == pytest.approx(4097.9)
    assert len(buffer["by_hour"]) == 24
    assert buffer["n"] == 744
    assert "walk-forward" in buffer["caveat"]

    backtest = _json(client.get(f"{BASE}/risk/backtest", params={"level": 0.9}))
    assert backtest["basis"] == "walk_forward"
    assert backtest["outcome_lag_days"] == 2
    assert backtest["min_history_days"] == 7
    assert backtest["evaluated_days"] == 23
    assert len(backtest["skipped_days"]) == 8
    assert 0.85 <= backtest["coverage"] <= 0.87
    assert backtest["mean_buffer_mw"] == pytest.approx(4051.8)
    assert backtest["target"] == 0.9
    assert len(backtest["daily"]) == 23


def test_cutoff_sensitivity_is_deterministic_across_repeated_requests(client: TestClient) -> None:
    first = client.get(f"{BASE}/accuracy/cutoff-sensitivity")
    second = client.get(f"{BASE}/accuracy/cutoff-sensitivity")
    assert first.content == second.content


def test_etag_supports_conditional_requests(client: TestClient) -> None:
    url = f"{BASE}/accuracy/summary"
    first = client.get(url)
    etag = first.headers["etag"]
    assert etag.startswith('"')
    assert etag.endswith('"')
    cached = client.get(url, headers={"If-None-Match": etag})
    assert cached.status_code == 304
    assert cached.content == b""
    other = client.get(url, params={"cutoff": "06:00"})
    assert other.headers["etag"] != etag
    assert other.headers["cache-control"].startswith("public, max-age=300")


def test_gzip_is_applied_to_large_responses(client: TestClient) -> None:
    response = client.get(f"{BASE}/accuracy/distribution", headers={"Accept-Encoding": "gzip"})
    assert response.status_code == 200
    assert response.headers.get("content-encoding") == "gzip"
    assert len(response.json()["scatter"]) == 744


def test_cors_allows_only_configured_origins(client: TestClient) -> None:
    allowed = client.get(f"{BASE}/meta", headers={"Origin": "http://localhost:5173"})
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
    blocked = client.get(f"{BASE}/meta", headers={"Origin": "https://example.com"})
    assert "access-control-allow-origin" not in blocked.headers


def test_csv_exports_have_stable_headers_and_rows(client: TestClient) -> None:
    response = client.get(
        f"{BASE}/export/decision-view.csv",
        params={"delivery_date": "2026-01-15", "cutoff": "09:00", "include_actuals": "true"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment" in response.headers["content-disposition"]
    rows = list(csv.DictReader(io.StringIO(response.text)))
    assert len(rows) == 24
    assert list(rows[0]) == [
        "delivery_date",
        "cutoff_utc",
        "start_time_utc",
        "start_time_local",
        "forecast_mw",
        "publish_time_utc",
        "horizon_h",
        "actual_mw",
        "error_mw",
        "shortfall_mw",
    ]
    assert all(row["delivery_date"] == "2026-01-15" for row in rows)
    assert all(row["actual_mw"] != "" for row in rows)


@pytest.mark.parametrize(
    ("table", "data_rows"),
    [
        ("daily", 31),
        ("by-horizon", 8),
        ("by-hour", 24),
        ("by-level", 5),
        ("cutoff-sensitivity", 7),
    ],
)
def test_accuracy_csv_exports(client: TestClient, table: str, data_rows: int) -> None:
    response = client.get(f"{BASE}/export/accuracy.csv", params={"table": table})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    lines = [line for line in response.text.splitlines() if line]
    assert len(lines) == data_rows + 1


def test_export_rejects_an_unknown_table(client: TestClient) -> None:
    _assert_problem(
        client.get(f"{BASE}/export/accuracy.csv", params={"table": "everything"}),
        422,
        "validation",
    )


def test_openapi_and_docs_are_served(client: TestClient) -> None:
    schema = client.get("/api/openapi.json")
    assert schema.status_code == 200
    document = schema.json()
    paths = document["paths"]
    for path in (
        "/api/v1/health",
        "/api/v1/meta",
        "/api/v1/decision-view",
        "/api/v1/revisions",
        "/api/v1/accuracy/summary",
        "/api/v1/accuracy/daily",
        "/api/v1/accuracy/by-horizon",
        "/api/v1/accuracy/by-hour",
        "/api/v1/accuracy/by-level",
        "/api/v1/accuracy/distribution",
        "/api/v1/accuracy/worst",
        "/api/v1/accuracy/cutoff-sensitivity",
        "/api/v1/risk/buffer",
        "/api/v1/risk/backtest",
        "/api/v1/export/decision-view.csv",
        "/api/v1/export/accuracy.csv",
    ):
        assert path in paths, path
    docs = client.get("/api/docs")
    assert docs.status_code == 200
    assert "text/html" in docs.headers["content-type"]
    assert client.head("/api/docs").status_code == 200
    assert "/api/static/swagger/swagger-ui-bundle.js" in docs.text
    assert "cdn.jsdelivr.net" not in docs.text
    for asset in (
        "swagger-ui.css",
        "swagger-ui-bundle.js",
        "swagger-ui-standalone-preset.js",
        "swagger-init.js",
        "favicon-32x32.png",
    ):
        response = client.get(f"/api/static/swagger/{asset}")
        assert response.status_code == 200, asset


def test_unknown_paths_return_problem_json(client: TestClient) -> None:
    body = _assert_problem(client.get(f"{BASE}/does-not-exist"), 404, "http")
    assert body["title"] == "Request failed"


def test_head_requests_are_supported_for_health(client: TestClient) -> None:
    response = client.head(f"{BASE}/health")
    assert response.status_code == 200
    assert response.content == b""
