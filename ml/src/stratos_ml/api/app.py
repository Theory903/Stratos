"""ML service FastAPI application."""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

import structlog
from fastapi import FastAPI

from stratos_ml.api.routes import router
from stratos_ml.config import Settings

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = Settings()
    logger.info("ml_service.startup", port=settings.port)
    yield
    logger.info("ml_service.shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title="STRATOS ML Service",
        description="Statistical, classical ML, and deep learning models for financial analysis",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.include_router(router)
    return app


app = create_app()
