"""NLP service application factory."""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

import structlog
from fastapi import FastAPI

from stratos_nlp.api.routes import router
from stratos_nlp.config import Settings

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = Settings()
    logger.info("nlp_service.startup", port=settings.port)
    yield
    logger.info("nlp_service.shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title="STRATOS NLP Service",
        description="Financial sentiment, entity extraction, and RAG pipeline",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.include_router(router)
    return app


app = create_app()
