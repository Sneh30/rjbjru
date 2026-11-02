"""Health and metadata routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_app_settings, get_repository
from app.api.schemas import HealthOut, MetaOut
from app.config import Settings
from app.data.repository import Repository
from app.services import meta_service

router = APIRouter(tags=["system"])


@router.head(
    "/health",
    response_model=HealthOut,
    include_in_schema=False,
    responses={503: {"description": "Snapshot unavailable"}},
)
@router.get(
    "/health",
    response_model=HealthOut,
    summary="Liveness plus dataset fingerprint",
    responses={503: {"description": "Snapshot unavailable"}},
)
def health(
    repository: Annotated[Repository, Depends(get_repository)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> dict[str, object]:
    """Return liveness, row counts and the immutable dataset hash."""
    return meta_service.health(repository, settings)


@router.get(
    "/meta",
    response_model=MetaOut,
    summary="Scope, defaults, provenance and methodology metadata",
)
def meta(
    repository: Annotated[Repository, Depends(get_repository)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> dict[str, object]:
    """Return the UI's provenance and configuration source of truth."""
    return meta_service.meta(repository, settings)
