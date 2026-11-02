"""Version 1 API router composition."""

from __future__ import annotations

from fastapi import APIRouter

from . import accuracy, decision, exports, meta, risk

api_router = APIRouter()
api_router.include_router(meta.router)
api_router.include_router(decision.router)
api_router.include_router(accuracy.router)
api_router.include_router(risk.router)
api_router.include_router(exports.router)
