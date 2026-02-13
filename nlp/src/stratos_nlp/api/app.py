"""NLP API — FastAPI app factory."""

from fastapi import FastAPI

from stratos_nlp.api.routes import router
from stratos_nlp.config import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    app = FastAPI(title="STRATOS NLP Service", version="0.1.0")
    app.include_router(router, prefix="/api/v1")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "nlp"}

    return app
