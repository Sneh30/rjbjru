"""CSV export routes for the desk and lab."""

from __future__ import annotations

import csv
import io
from datetime import date, time
from typing import Annotated, Any, cast

from fastapi import APIRouter, Depends, Query, Response

from app.api.deps import get_app_settings, get_service
from app.api.schemas import DecisionQuery, ExportQuery
from app.api.v1.common import resolve_cutoff
from app.config import Settings
from app.services import accuracy_service
from app.services.analysis_service import AnalysisService
from app.services.decision_service import decision_view

router = APIRouter(prefix="/export", tags=["export"])

DECISION_COLUMNS = (
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
)


def _csv_response(rows: list[dict[str, Any]], columns: tuple[str, ...], filename: str) -> Response:
    """Build a UTF-8 CSV response with a stable column order."""
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(columns), extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {column: "" if row.get(column) is None else row.get(column) for column in columns}
        )
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/decision-view.csv",
    summary="CSV of the decision view",
    response_class=Response,
)
def export_decision_view(
    query: Annotated[DecisionQuery, Query()],
    service: Annotated[AnalysisService, Depends(get_service)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> Response:
    """Export exactly the displayed decision-time rows, optionally with hindsight."""
    cutoff = resolve_cutoff(query.cutoff, settings)
    payload = decision_view(
        service,
        query.delivery_date,
        cutoff,
        include_actuals=query.include_actuals,
    )
    cutoff_info = payload["cutoff"]
    rows = [
        {
            "delivery_date": payload["delivery_date"],
            "cutoff_utc": cutoff_info.get("utc") if isinstance(cutoff_info, dict) else None,
            "start_time_utc": point.get("start_time"),
            "start_time_local": point.get("local_time"),
            "forecast_mw": point.get("forecast_mw"),
            "publish_time_utc": point.get("publish_time"),
            "horizon_h": point.get("horizon_h"),
            "actual_mw": point.get("actual_mw"),
            "error_mw": point.get("error_mw"),
            "shortfall_mw": point.get("shortfall_mw"),
        }
        for point in cast(list[dict[str, Any]], payload["points"])
    ]
    filename = f"windlens-decision-{query.delivery_date.isoformat()}-{cutoff.strftime('%H%M')}.csv"
    return _csv_response(rows, DECISION_COLUMNS, filename)


def _accuracy_rows(
    service: AnalysisService,
    query: ExportQuery,
    start: date,
    end: date,
    cutoff: time,
) -> tuple[list[dict[str, Any]], tuple[str, ...]]:
    """Return rows and columns for the requested accuracy table."""
    rows: list[dict[str, Any]]
    columns: tuple[str, ...]
    if query.table == "daily":
        payload = accuracy_service.daily(service, start, end, cutoff)
        rows = cast(list[dict[str, Any]], payload["days"])
        columns = (
            "delivery_date",
            "n",
            "mae_mw",
            "bias_mw",
            "rmse_mw",
            "nmae_pct",
            "max_abs_mw",
            "max_abs_time",
            "shortfall_p90_mw",
            "mean_actual_mw",
        )
    elif query.table == "by-horizon":
        payload = accuracy_service.by_horizon(service, start, end, cutoff)
        rows = cast(list[dict[str, Any]], payload["buckets"])
        columns = ("from_h", "to_h", "label", "n", "nmae_pct", "mae_mw", "bias_mw", "rmse_mw")
    elif query.table == "by-hour":
        payload = accuracy_service.by_hour_breakdown(service, start, end, cutoff)
        rows = cast(list[dict[str, Any]], payload["hours"])
        columns = (
            "hour",
            "label",
            "n",
            "mae_mw",
            "bias_mw",
            "rmse_mw",
            "shortfall_p90_mw",
            "mean_actual_mw",
        )
    elif query.table == "by-level":
        payload = accuracy_service.by_level_breakdown(
            service, start, end, cutoff, basis=query.basis, bins=query.bins
        )
        rows = cast(list[dict[str, Any]], payload["bins"])
        columns = ("label", "from_mw", "to_mw", "n", "mae_mw", "bias_mw", "nmae_pct")
    else:
        payload = accuracy_service.cutoff_sensitivity(service, start, end)
        rows = cast(list[dict[str, Any]], payload["rows"])
        columns = (
            "cutoff",
            "n",
            "mae_mw",
            "bias_mw",
            "shortfall_p90_mw",
            "mean_horizon_h",
            "coverage_pct",
        )
    return rows, columns


@router.get(
    "/accuracy.csv",
    summary="CSV of an Accuracy Lab table",
    response_class=Response,
)
def export_accuracy(
    query: Annotated[ExportQuery, Query()],
    service: Annotated[AnalysisService, Depends(get_service)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> Response:
    """Export the selected accuracy table as CSV."""
    scope_start, scope_end = service.scope_bounds()
    start, end = service.ensure_window(
        query.start or scope_start,
        query.end or scope_end,
    )
    cutoff = resolve_cutoff(query.cutoff, settings)
    rows, columns = _accuracy_rows(service, query, start, end, cutoff)
    filename = f"windlens-{query.table}-{start.isoformat()}-{end.isoformat()}.csv"
    return _csv_response(rows, columns, filename)
