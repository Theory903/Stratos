"""Orchestrator API — the unified STRATOS gateway."""

from fastapi import FastAPI

from stratos_orchestrator.api.routes import router
from stratos_orchestrator.config import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    app = FastAPI(
        title="STRATOS Orchestrator",
        version="0.1.0",
        description="Unified financial intelligence gateway",
    )
    app.include_router(router, prefix="/api/v1")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "orchestrator"}

    return app
