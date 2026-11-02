"""Thin Elexon BMRS client for the two permitted datasets.

Only ``FUELHH`` filtered to WIND and ``WINDFOR`` are ever requested. The client is
used offline by the ingestion CLI; the serving path never calls Elexon.
"""

from __future__ import annotations

import time
from datetime import date
from typing import Any

import httpx
from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1"
USER_AGENT = "windlens-ingest/1.0"


class ElexonError(RuntimeError):
    """Raised when Elexon returns a non-retryable error or malformed payload."""


class RetryableStatusError(ElexonError):
    """Raised for 429/5xx responses so tenacity can retry."""

    def __init__(self, status: int) -> None:
        super().__init__(f"Elexon returned retryable status {status}")
        self.status = status


def _wait(retry_state: RetryCallState) -> float:
    """Honour Retry-After when present, otherwise use exponential backoff."""
    exception = retry_state.outcome.exception() if retry_state.outcome else None
    if isinstance(exception, RetryableStatusError) and exception.status == 429:
        return min(30.0, 2.0**retry_state.attempt_number)
    return wait_exponential(multiplier=1, max=30)(retry_state)


class ElexonClient:
    """Synchronous, polite client with retries and day-sized chunks."""

    def __init__(
        self,
        base_url: str = BASE_URL,
        *,
        timeout: float = 30.0,
        pause_seconds: float = 0.2,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.pause_seconds = pause_seconds
        self._client = httpx.Client(
            timeout=httpx.Timeout(timeout, connect=10.0),
            headers={"Accept": "application/json", "User-Agent": USER_AGENT},
            transport=transport,
            follow_redirects=True,
        )

    def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        self._client.close()

    def __enter__(self) -> ElexonClient:
        """Return the client for context-manager use."""
        return self

    def __exit__(self, *_: object) -> None:
        """Close the connection pool on context exit."""
        self.close()

    @retry(
        retry=retry_if_exception_type(
            (RetryableStatusError, httpx.TimeoutException, httpx.TransportError)
        ),
        stop=stop_after_attempt(6),
        wait=_wait,
        reraise=True,
    )
    def _get(self, path: str, params: dict[str, str]) -> tuple[bytes, str]:
        response = self._client.get(f"{self.base_url}{path}", params=params)
        if response.status_code == 429 or response.status_code >= 500:
            raise RetryableStatusError(response.status_code)
        if response.status_code >= 400:
            raise ElexonError(f"Elexon {response.status_code} for {path}: {response.text[:300]}")
        return response.content, str(response.request.url)

    def fetch_actuals_day(self, day: date) -> tuple[bytes, str, dict[str, str]]:
        """Fetch FUELHH WIND for one settlement date.

        Args:
            day: Settlement date in Europe/London (all of January 2026 is UTC).

        Returns:
            Raw response bytes, resolved URL and request parameters.
        """
        params = {
            "settlementDateFrom": day.isoformat(),
            "settlementDateTo": day.isoformat(),
            "fuelType": "WIND",
        }
        content, url = self._get("/datasets/FUELHH/stream", params)
        time.sleep(self.pause_seconds)
        return content, url, params

    def fetch_forecasts_publish_day(self, day: date) -> tuple[bytes, str, dict[str, str]]:
        """Fetch all WINDFOR vintages published on one UTC date.

        Args:
            day: Publication date in UTC.

        Returns:
            Raw response bytes, resolved URL and request parameters.
        """
        params = {
            "publishDateTimeFrom": f"{day.isoformat()}T00:00:00Z",
            "publishDateTimeTo": f"{day.isoformat()}T23:59:59Z",
        }
        content, url = self._get("/datasets/WINDFOR/stream", params)
        time.sleep(self.pause_seconds)
        return content, url, params


def parse_payload(content: bytes, *, dataset: str) -> list[dict[str, Any]]:
    """Parse a stream payload and enforce that it is a JSON array of objects.

    Raises:
        ElexonError: if the payload is malformed or empty for a non-retryable reason.
    """
    import json

    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ElexonError(f"{dataset}: response was not valid JSON") from exc
    if not isinstance(payload, list):
        raise ElexonError(f"{dataset}: expected a JSON array, got {type(payload).__name__}")
    if not all(isinstance(row, dict) for row in payload):
        raise ElexonError(f"{dataset}: expected an array of objects")
    return payload
