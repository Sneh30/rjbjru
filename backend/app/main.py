"""FastAPI application factory, middleware and RFC 7807 error handling."""

from __future__ import annotations

import hashlib
import json
import logging
import time as time_module
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import cast

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import api_router
from app.config import Settings, get_settings
from app.data.repository import Repository, SnapshotRepository
from app.domain.errors import (
    ConfigError,
    DataIntegrityError,
    DataUnavailableError,
    NoDataError,
    OutOfScopeError,
    WindLensError,
)
from app.services.analysis_service import AnalysisService

LOGGER = logging.getLogger("windlens.api")
PROBLEM_BASE = "https://windlens/errors"
STATIC_DIR = Path(__file__).resolve().parent / "static"
ERROR_STATUS: dict[type[WindLensError], int] = {
    OutOfScopeError: 404,
    NoDataError: 404,
    DataUnavailableError: 503,
    DataIntegrityError: 500,
    ConfigError: 500,
}
ERROR_TYPE: dict[type[WindLensError], str] = {
    OutOfScopeError: "out-of-scope",
    NoDataError: "no-data",
    DataUnavailableError: "data-unavailable",
    DataIntegrityError: "data-integrity",
    ConfigError: "configuration",
}


def _configure_logging(level: str) -> None:
    """Configure JSON-friendly console logging once."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(message)s",
    )
    for handler in logging.getLogger().handlers:
        if handler.formatter is not None:
            handler.formatter.converter = time_module.gmtime


def _problem(
    request: Request,
    *,
    status: int,
    slug: str,
    title: str,
    detail: str,
    errors: list[dict[str, object]] | None = None,
    extra: dict[str, object] | None = None,
) -> JSONResponse:
    """Build an RFC 7807 ``application/problem+json`` response."""
    body: dict[str, object] = {
        "type": f"{PROBLEM_BASE}/{slug}",
        "title": title,
        "status": status,
        "detail": detail,
        "instance": request.url.path,
    }
    if errors:
        body["errors"] = errors
    if extra:
        body.update(extra)
    return JSONResponse(
        status_code=status,
        content=body,
        media_type="application/problem+json",
        headers={"X-Request-ID": getattr(request.state, "request_id", "")},
    )


def _error_handler(request: Request, exc: WindLensError) -> JSONResponse:
    """Map a typed domain failure to a stable problem document."""
    status = 500
    matched: type[WindLensError] | None = None
    for error_type, code in ERROR_STATUS.items():
        if isinstance(exc, error_type):
            status = code
            matched = error_type
            break
    slug = ERROR_TYPE.get(matched, "internal") if matched else "internal"
    title = {
        404: "Requested data is not available",
        503: "Data snapshot unavailable",
        500: "Internal data error",
    }.get(status, "Request failed")
    if isinstance(exc, OutOfScopeError):
        title = "Date out of scope"
    return _problem(
        request,
        status=status,
        slug=slug,
        title=title,
        detail=str(exc),
        extra=exc.extra,
    )


def create_app(
    settings: Settings | None = None,
    repository: Repository | None = None,
) -> FastAPI:
    """Create the ASGI application.

    Args:
        settings: Optional settings override for tests.
        repository: Optional pre-loaded repository, used by contract tests.

    Returns:
        A configured FastAPI instance. The default snapshot is loaded on startup.
    """
    resolved = settings or get_settings()
    _configure_logging(resolved.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        try:
            loaded = cast(
                Repository,
                repository if repository is not None else SnapshotRepository(resolved.data_dir),
            )
            analysis = AnalysisService(loaded, resolved)
            analysis.verify_scope()
            scope_start, scope_end = analysis.scope_bounds()
            analysis.window(resolved.default_cutoff, scope_start, scope_end)
            app.state.repository = loaded
            app.state.analysis = analysis
            app.state.startup_error = None
            LOGGER.info(
                json.dumps(
                    {
                        "event": "startup",
                        "fingerprint": loaded.fingerprint,
                        "actual_rows": len(loaded.actuals()),
                        "forecast_rows": len(loaded.forecasts()),
                    }
                )
            )
        except Exception as exc:
            app.state.repository = None
            app.state.analysis = None
            app.state.startup_error = str(exc)
            LOGGER.exception("snapshot failed to load")
        yield

    app = FastAPI(
        title="WindLens API",
        version="1.0.0",
        description=(
            "Decision-time accuracy for GB wind. Data: Elexon BMRS FUELHH (WIND) "
            "and WINDFOR. Error sign: forecast minus actual; positive means "
            "over-forecast and shortfall risk."
        ),
        docs_url=None,
        redoc_url=None,
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
        openapi_tags=[
            {"name": "system", "description": "Liveness, fingerprint and scope metadata."},
            {"name": "decision", "description": "Decision-time forecasts and vintage history."},
            {"name": "accuracy", "description": "Scorecards and error breakdowns."},
            {"name": "risk", "description": "Empirical buffers and walk-forward validation."},
            {"name": "export", "description": "CSV exports of the desk and lab tables."},
        ],
    )
    app.state.settings = resolved

    app.mount("/api/static", StaticFiles(directory=STATIC_DIR), name="api-static")

    @app.api_route("/api/docs", methods=["GET", "HEAD"], include_in_schema=False)
    async def swagger_ui() -> FileResponse:
        """Serve the self-hosted Swagger UI bundled in the deployment."""
        return FileResponse(STATIC_DIR / "swagger" / "index.html")

    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "HEAD", "OPTIONS"],
        allow_headers=["Accept", "Content-Type", "If-None-Match", "X-Request-ID"],
        expose_headers=["ETag", "X-Request-ID"],
        max_age=600,
    )

    @app.middleware("http")
    async def request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        request.state.request_id = request_id[:128]
        started = time_module.perf_counter()
        response: Response
        try:
            response = await call_next(request)
        except Exception:
            elapsed = (time_module.perf_counter() - started) * 1000
            LOGGER.exception(
                json.dumps(
                    {
                        "ts": time_module.strftime("%Y-%m-%dT%H:%M:%SZ", time_module.gmtime()),
                        "level": "error",
                        "request_id": request.state.request_id,
                        "method": request.method,
                        "path": request.url.path,
                        "status": 500,
                        "duration_ms": round(elapsed, 2),
                    }
                )
            )
            raise
        elapsed = (time_module.perf_counter() - started) * 1000
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"

        if request.method in {"GET", "HEAD"} and request.url.path.startswith("/api/v1"):
            if request.url.path == "/api/v1/health":
                response.headers["Cache-Control"] = "no-store"
            else:
                response.headers["Cache-Control"] = (
                    "public, max-age=300, stale-while-revalidate=3600"
                )
                fingerprint = "unknown"
                loaded = getattr(request.app.state, "repository", None)
                if loaded is not None:
                    fingerprint = str(loaded.fingerprint)
                etag = (
                    '"'
                    + hashlib.sha256(
                        f"{fingerprint}:{request.url.path}?{request.url.query}".encode()
                    ).hexdigest()[:32]
                    + '"'
                )
                response.headers["ETag"] = etag
                if request.headers.get("if-none-match") == etag:
                    return Response(
                        status_code=304,
                        headers={
                            "ETag": etag,
                            "Cache-Control": response.headers["Cache-Control"],
                            "X-Request-ID": request.state.request_id,
                        },
                    )

        LOGGER.info(
            json.dumps(
                {
                    "ts": time_module.strftime("%Y-%m-%dT%H:%M:%SZ", time_module.gmtime()),
                    "level": "info",
                    "request_id": request.state.request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": round(elapsed, 2),
                }
            )
        )
        return response

    @app.exception_handler(WindLensError)
    async def windlens_error_handler(request: Request, exc: WindLensError) -> JSONResponse:
        return _error_handler(request, exc)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors: list[dict[str, object]] = [
            {
                "loc": list(error.get("loc", [])),
                "msg": str(error.get("msg", "invalid value")),
                "type": str(error.get("type", "value_error")),
            }
            for error in exc.errors()
        ]
        return _problem(
            request,
            status=422,
            slug="validation",
            title="Request validation failed",
            detail="One or more query parameters are invalid.",
            errors=errors,
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _problem(
            request,
            status=exc.status_code,
            slug="http",
            title="Request failed",
            detail=str(exc.detail),
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        LOGGER.exception("unhandled error", exc_info=exc)
        return _problem(
            request,
            status=500,
            slug="internal",
            title="Internal server error",
            detail="An unexpected error occurred. No stack trace is exposed.",
        )

    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
