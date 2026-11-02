"""Accuracy Lab routes."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_app_settings, get_service
from app.api.schemas import (
    AccuracySummaryOut,
    ByLevelQuery,
    DailyOut,
    DateWindowQuery,
    DistributionOut,
    DistributionQuery,
    HorizonOut,
    HoursOut,
    LevelOut,
    SensitivityOut,
    WindowQuery,
    WorstOut,
    WorstQuery,
)
from app.api.v1.common import resolve_cutoff
from app.config import Settings
from app.services import accuracy_service
from app.services.analysis_service import AnalysisService

router = APIRouter(prefix="/accuracy", tags=["accuracy"])


def _window(
    service: AnalysisService,
    start: date | None,
    end: date | None,
) -> tuple[date, date]:
    scope_start, scope_end = service.scope_bounds()
    return service.ensure_window(start or scope_start, end or scope_end)


@router.get(
    "/summary",
    response_model=AccuracySummaryOut,
    summary="Pooled decision-time scorecard",
)
def get_summary(
    query: Annotated[DateWindowQuery, Query()],
    service: Annotated[AnalysisService, Depends(get_service)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> dict[str, object]:
    """Return headline metrics, baseline skill and coverage for the window."""
    start, end = _window(service, query.start, query.end)
    return accuracy_service.summary(service, start, end, resolve_cutoff(query.cutoff, settings))


@router.get("/daily", response_model=DailyOut, summary="Daily accuracy series")
def get_daily(
    query: Annotated[DateWindowQuery, Query()],
    service: Annotated[AnalysisService, Depends(get_service)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> dict[str, object]:
    """Return MAE, bias and worst-period detail for each delivery day."""
    start, end = _window(service, query.start, query.end)
    return accuracy_service.daily(service, start, end, resolve_cutoff(query.cutoff, settings))


@router.get(
    "/by-horizon",
    response_model=HorizonOut,
    summary="Error growth across forecast horizons",
)
def get_by_horizon(
    query: Annotated[DateWindowQuery, Query()],
    service: Annotated[AnalysisService, Depends(get_service)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> dict[str, object]:
    """Return metrics for every vintage, bucketed by horizon."""
    start, end = _window(service, query.start, query.end)
    return accuracy_service.by_horizon(service, start, end, resolve_cutoff(query.cutoff, settings))


@router.get("/by-hour", response_model=HoursOut, summary="Metrics by London hour of day")
def get_by_hour(
    query: Annotated[DateWindowQuery, Query()],
    service: Annotated[AnalysisService, Depends(get_service)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> dict[str, object]:
    """Return decision-time accuracy for each of the 24 London hours."""
    start, end = _window(service, query.start, query.end)
    return accuracy_service.by_hour_breakdown(
        service, start, end, resolve_cutoff(query.cutoff, settings)
    )


@router.get("/by-level", response_model=LevelOut, summary="Metrics by wind-output level")
def get_by_level(
    query: Annotated[ByLevelQuery, Query()],
    service: Annotated[AnalysisService, Depends(get_service)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> dict[str, object]:
    """Return equal-count wind-level bins using actual or forecast output."""
    start, end = _window(service, query.start, query.end)
    return accuracy_service.by_level_breakdown(
        service,
        start,
        end,
        resolve_cutoff(query.cutoff, settings),
        basis=query.basis,
        bins=query.bins,
    )


@router.get(
    "/distribution",
    response_model=DistributionOut,
    summary="Signed-error histogram and scatter sample",
)
def get_distribution(
    query: Annotated[DistributionQuery, Query()],
    service: Annotated[AnalysisService, Depends(get_service)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> dict[str, object]:
    """Return a histogram, quantiles and a deterministic scatter sample."""
    start, end = _window(service, query.start, query.end)
    return accuracy_service.distribution(
        service,
        start,
        end,
        resolve_cutoff(query.cutoff, settings),
        bins=query.bins,
    )


@router.get("/worst", response_model=WorstOut, summary="Worst days and periods")
def get_worst(
    query: Annotated[WorstQuery, Query()],
    service: Annotated[AnalysisService, Depends(get_service)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> dict[str, object]:
    """Return the largest daily misses and individual forecast errors."""
    start, end = _window(service, query.start, query.end)
    return accuracy_service.worst(
        service,
        start,
        end,
        resolve_cutoff(query.cutoff, settings),
        n=query.n,
        metric=query.metric,
    )


@router.get(
    "/cutoff-sensitivity",
    response_model=SensitivityOut,
    summary="Accuracy across the configured cutoff grid",
)
def get_cutoff_sensitivity(
    query: Annotated[WindowQuery, Query()],
    service: Annotated[AnalysisService, Depends(get_service)],
) -> dict[str, object]:
    """Return metrics and coverage for every configured cutoff."""
    start, end = _window(service, query.start, query.end)
    return accuracy_service.cutoff_sensitivity(service, start, end)
