"""FastAPI app factory with V1 and V2 route trees."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from data_fabric.adapters.cache import RedisCacheStore
from data_fabric.adapters.database import (
    PostgresDataStore,
    create_tables,
    dispose_engine,
    get_session_factory,
    init_engine,
)
from data_fabric.adapters.document_store import MongoDocumentStore
from data_fabric.adapters.events import KafkaEventPublisher
from data_fabric.adapters.object_store import MinioObjectStore
from data_fabric.adapters.providers import SecEdgarSource
from data_fabric.adapters.sources import FREDMacroSource, PolygonMarketSource, WorldBankCountrySource
from data_fabric.adapters.sources.oanda import OandaFXSource
from data_fabric.api.routes import router as v1_router
from data_fabric.api.v2_routes import router as v2_router
from data_fabric.config import Settings

try:  # pragma: no cover
    import structlog

    logger = structlog.get_logger()
except ImportError:  # pragma: no cover
    logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.settings

    logger.info("starting_data_fabric", port=settings.port)
    init_engine(settings)
    await create_tables()
    app.state.data_store = PostgresDataStore(get_session_factory())
    app.state.cache = RedisCacheStore(settings.redis_url)
    app.state.document_store = MongoDocumentStore(settings.mongo_url, settings.mongo_database)
    app.state.object_store = MinioObjectStore(
        endpoint_url=settings.s3_endpoint,
        access_key=settings.s3_access_key,
        secret_key=settings.s3_secret_key,
        bucket=settings.s3_bucket,
    )
    await app.state.object_store.ensure_bucket()

    app.state.events = KafkaEventPublisher(settings.kafka_brokers)
    await app.state.events.start()

    app.state.market_source = PolygonMarketSource(
        api_key=settings.market_api_key,
        base_url=settings.market_base_url,
    )
    app.state.fred_source = FREDMacroSource(api_key=settings.fred_api_key)
    app.state.country_source = WorldBankCountrySource(base_url=settings.world_bank_base_url)
    app.state.fx_source = OandaFXSource(api_key=settings.oanda_api_key)
    app.state.sec_source = SecEdgarSource(
        base_url=settings.sec_base_url,
        ticker_map_url=settings.sec_ticker_map_url,
        user_agent=settings.sec_user_agent,
    )

    logger.info("data_fabric_ready", debug=settings.debug)
    try:
        yield
    finally:
        logger.info("shutting_down_data_fabric")
        await app.state.events.stop()
        await app.state.cache.close()
        await app.state.document_store.close()
        await app.state.market_source.close()
        await app.state.fred_source.close()
        await app.state.country_source.close()
        await app.state.fx_source.close()
        await app.state.sec_source.close()
        await dispose_engine()
        logger.info("data_fabric_stopped")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    app = FastAPI(
        title="STRATOS Data Fabric",
        version="0.2.0",
        description="Data ingestion, storage, and query service for STRATOS",
        lifespan=lifespan,
    )
    app.state.settings = settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(v1_router, prefix="/api/v1")
    app.include_router(v2_router, prefix="/api/v2")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "data-fabric"}

    return app
