"""Elexon client request shapes, payload guards and retry policy."""

from __future__ import annotations

import json
from concurrent.futures import Future
from datetime import date

import httpx
import pytest
from tenacity import RetryCallState

from app.ingestion.elexon_client import (
    ElexonClient,
    ElexonError,
    RetryableStatusError,
    _wait,
    parse_payload,
)


def test_fetch_actuals_sends_the_verified_day_query() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=[{"fuelType": "WIND"}])

    with ElexonClient(transport=httpx.MockTransport(handler), pause_seconds=0) as client:
        content, url, params = client.fetch_actuals_day(date(2026, 1, 15))

    assert json.loads(content) == [{"fuelType": "WIND"}]
    assert seen[0].url.path == "/bmrs/api/v1/datasets/FUELHH/stream"
    assert seen[0].url.params["settlementDateFrom"] == "2026-01-15"
    assert seen[0].url.params["settlementDateTo"] == "2026-01-15"
    assert seen[0].url.params["fuelType"] == "WIND"
    assert params == {
        "settlementDateFrom": "2026-01-15",
        "settlementDateTo": "2026-01-15",
        "fuelType": "WIND",
    }
    assert url.startswith("https://data.elexon.co.uk/bmrs/api/v1/datasets/FUELHH/stream?")


def test_fetch_forecasts_sends_the_verified_publish_window() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=[])

    with ElexonClient(transport=httpx.MockTransport(handler), pause_seconds=0) as client:
        client.fetch_forecasts_publish_day(date(2026, 1, 15))

    assert seen[0].url.path == "/bmrs/api/v1/datasets/WINDFOR/stream"
    assert seen[0].url.params["publishDateTimeFrom"] == "2026-01-15T00:00:00Z"
    assert seen[0].url.params["publishDateTimeTo"] == "2026-01-15T23:59:59Z"


def test_non_retryable_http_error_is_reported_with_status() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, text="bad request")

    with (
        ElexonClient(transport=httpx.MockTransport(handler), pause_seconds=0) as client,
        pytest.raises(ElexonError, match="400"),
    ):
        client.fetch_actuals_day(date(2026, 1, 15))


def test_retryable_status_is_retried_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] < 3:
            return httpx.Response(429, text="slow down")
        return httpx.Response(200, json=[])

    client = ElexonClient(transport=httpx.MockTransport(handler), pause_seconds=0)
    monkeypatch.setattr(ElexonClient._get.retry, "wait", lambda _: 0.0)
    try:
        content, _, _ = client.fetch_actuals_day(date(2026, 1, 15))
    finally:
        client.close()
    assert content == b"[]"
    assert calls["count"] == 3


def test_retry_after_wait_honours_429_and_uses_backoff_otherwise() -> None:
    state = RetryCallState(None, None, (), {})  # type: ignore[arg-type]
    state.attempt_number = 2
    outcome: Future[object] = Future()
    outcome.set_exception(RetryableStatusError(429))
    state.outcome = outcome  # type: ignore[assignment]
    assert _wait(state) == pytest.approx(4.0)

    outcome_503: Future[object] = Future()
    outcome_503.set_exception(RetryableStatusError(503))
    state.outcome = outcome_503  # type: ignore[assignment]
    assert 0.0 < _wait(state) <= 30.0


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (b"not json", "valid JSON"),
        (b'{"rows": []}', "JSON array"),
        (b"[1, 2]", "array of objects"),
    ],
)
def test_parse_payload_rejects_malformed_responses(content: bytes, message: str) -> None:
    with pytest.raises(ElexonError, match=message):
        parse_payload(content, dataset="FUELHH")


def test_parse_payload_accepts_an_array_of_objects() -> None:
    assert parse_payload(b'[{"a": 1}]', dataset="WINDFOR") == [{"a": 1}]
