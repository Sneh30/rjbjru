"""Request-scoped dependencies for the API."""

from __future__ import annotations

from typing import cast

from fastapi import Request

from app.config import Settings
from app.data.repository import Repository
from app.domain.errors import DataUnavailableError
from app.services.analysis_service import AnalysisService


def get_repository(request: Request) -> Repository:
    """Return the loaded snapshot repository or a 503-mapped error."""
    repository = getattr(request.app.state, "repository", None)
    if repository is None:
        raise DataUnavailableError("data snapshot is unavailable; see startup logs")
    return cast(Repository, repository)


def get_service(request: Request) -> AnalysisService:
    """Return the warmed analysis service or a 503-mapped error."""
    service = getattr(request.app.state, "analysis", None)
    if service is None:
        raise DataUnavailableError("data snapshot is unavailable; see startup logs")
    return cast(AnalysisService, service)


def get_app_settings(request: Request) -> Settings:
    """Return the settings used to construct this app instance."""
    settings = getattr(request.app.state, "settings", None)
    if settings is None:
        raise DataUnavailableError("application settings are unavailable")
    return cast(Settings, settings)
