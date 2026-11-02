"""Risk buffer and walk-forward routes."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_app_settings, get_service
from app.api.schemas import BacktestOut, BacktestQuery, BufferOut, BufferQuery
from app.api.v1.common import resolve_cutoff
from app.config import Settings
from app.services import risk_service
from app.services.analysis_service import AnalysisService

router = APIRouter(prefix="/risk", tags=["risk"])


def _window(
    service: AnalysisService,
    start: date | None,
    end: date | None,
) -> tuple[date, date]:
    scope_start, scope_end = service.scope_bounds()
    return service.ensure_window(start or scope_start, end or scope_end)


@router.get(
    "/buffer",
    response_model=BufferOut,
    summary="In-sample empirical signed-error buffers",
)
def get_buffer(
    query: Annotated[BufferQuery, Query()],
    service: Annotated[AnalysisService, Depends(get_service)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> dict[str, object]:
    """Return overall and hour-of-day buffers at the requested probabilities."""
    start, end = _window(service, query.start, query.end)
    return risk_service.buffer(
        service,
        start,
        end,
        resolve_cutoff(query.cutoff, settings),
        query.parsed_levels,
    )


@router.get(
    "/backtest",
    response_model=BacktestOut,
    summary="Leakage-safe walk-forward buffer coverage",
)
def get_backtest(
    query: Annotated[BacktestQuery, Query()],
    service: Annotated[AnalysisService, Depends(get_service)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> dict[str, object]:
    """Back-test a buffer using only outcomes observable before each day."""
    start, end = _window(service, query.start, query.end)
    return risk_service.backtest(
        service,
        start,
        end,
        resolve_cutoff(query.cutoff, settings),
        level=query.level,
        min_history_days=query.min_history_days,
    )
