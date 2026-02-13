"""ML API — FastAPI app factory."""

from fastapi import FastAPI

from stratos_ml.api.routes import router
from stratos_ml.config import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    app = FastAPI(title="STRATOS ML Service", version="0.1.0")
    app.include_router(router, prefix="/api/v1")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "ml"}

    return app
