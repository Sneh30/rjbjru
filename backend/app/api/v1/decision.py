"""Decision desk and revision explorer routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_app_settings, get_service
from app.api.schemas import DecisionQuery, DecisionViewOut, RevisionsOut, RevisionsQuery
from app.api.v1.common import resolve_cutoff
from app.config import Settings
from app.services.analysis_service import AnalysisService
from app.services.decision_service import decision_view
from app.services.revision_service import revisions

router = APIRouter(tags=["decision"])


@router.get(
    "/decision-view",
    response_model=DecisionViewOut,
    response_model_exclude_none=True,
    summary="Decision-time forecast for one delivery day",
    responses={404: {"description": "Delivery date out of scope"}},
)
def get_decision_view(
    query: Annotated[DecisionQuery, Query()],
    service: Annotated[AnalysisService, Depends(get_service)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> dict[str, object]:
    """Return the latest eligible forecast per hour, optionally with hindsight."""
    return decision_view(
        service,
        query.delivery_date,
        resolve_cutoff(query.cutoff, settings),
        include_actuals=query.include_actuals,
    )


@router.get(
    "/revisions",
    response_model=RevisionsOut,
    summary="Every forecast vintage for one target, with the cutoff marked",
    responses={404: {"description": "Target out of scope or no data"}},
)
def get_revisions(
    query: Annotated[RevisionsQuery, Query()],
    service: Annotated[AnalysisService, Depends(get_service)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> dict[str, object]:
    """Return eligible and leakage-illustrating vintages around a decision cutoff."""
    return revisions(
        service,
        target_time=query.target_time,
        delivery_date=query.delivery_date,
        period=query.period,
        cutoff=resolve_cutoff(query.cutoff, settings),
    )
