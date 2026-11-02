"""Small shared helpers for route handlers."""

from __future__ import annotations

from datetime import time

from app.config import Settings
from app.domain.timeutils import parse_cutoff


def resolve_cutoff(value: str | None, settings: Settings) -> time:
    """Resolve an optional query cutoff against the configured default."""
    return settings.default_cutoff if value is None else parse_cutoff(value)
