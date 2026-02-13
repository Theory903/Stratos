"""API layer — FastAPI app factory and dependency injection wiring."""

from __future__ import annotations

from fastapi import FastAPI

from data_fabric.api.routes import router
from data_fabric.config import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Application factory pattern — testable, configurable."""
    settings = settings or Settings()

    app = FastAPI(
        title="STRATOS Data Fabric",
        version="0.1.0",
        description="Ingestion, storage, and feature pipeline for STRATOS",
    )

    app.include_router(router, prefix="/api/v1")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "data-fabric"}

    return app
