"""Shared pytest fixtures.

The committed snapshot is read from the repository, never from a machine-specific
absolute path. API tests use a session-scoped app so startup validation is exercised
once, exactly as it is in production.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.data.repository import Repository, SnapshotRepository
from app.main import create_app

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"


@pytest.fixture(scope="session")
def settings() -> Settings:
    """Return deterministic test settings pointing at the committed snapshot."""
    return Settings(
        data_dir=DATA_DIR,
        scope_mode="decision_date",
        scope_start=pd.Timestamp("2026-01-01").date(),
        scope_end=pd.Timestamp("2026-01-31").date(),
        default_cutoff=pd.Timestamp("2026-01-01T09:00:00").time(),
        cors_origins=["http://localhost:5173"],
        log_level="CRITICAL",
    )


@pytest.fixture(scope="session")
def repository() -> Repository:
    """Load the real committed snapshot."""
    return SnapshotRepository(DATA_DIR)


@pytest.fixture(scope="session")
def client(settings: Settings, repository: Repository) -> Iterator[TestClient]:
    """Return a TestClient with the real snapshot attached."""
    app = create_app(settings=settings, repository=repository)
    with TestClient(app) as test_client:
        yield test_client
