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
from data_fabric.adapters.providers import (
    CoinAPIMarketSource,
    GDELTEventSource,
    RedditSocialSource,
    RssFeedSource,
    SecEdgarSource,
    UpstoxMarketSource,
    XSocialSource,
)
from data_fabric.adapters.sources import FREDMacroSource, PolygonMarketSource, WorldBankCountrySource
from data_fabric.adapters.sources.oanda import OandaFXSource
from data_fabric.api.routes import router as v1_router
from data_fabric.api.v2_routes import router as v2_router
from data_fabric.api.research_routes import router as research_router
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
    app.state.provider_sources = {
        "massive": app.state.market_source,
        "fred": app.state.fred_source,
        "world_bank": app.state.country_source,
        "oanda": app.state.fx_source,
        "sec": app.state.sec_source,
        "upstox": UpstoxMarketSource(
            api_key=settings.upstox_api_key,
            base_url=settings.upstox_base_url,
        ),
        "coinapi": CoinAPIMarketSource(
            api_key=settings.coinapi_api_key,
            base_url=settings.coinapi_base_url,
        ),
        "gdelt": GDELTEventSource(base_url=settings.gdelt_base_url),
        "reddit": RedditSocialSource(
            client_id=settings.reddit_client_id,
            client_secret=settings.reddit_client_secret,
            user_agent=settings.reddit_user_agent,
        ),
        "x": XSocialSource(
            bearer_token=settings.x_bearer_token,
            base_url=settings.x_base_url,
        ),
        "rbi_rss": RssFeedSource(
            name="rbi_rss",
            feed_url=settings.rbi_rss_url,
            source_type="policy",
        ),
        "sebi_rss": RssFeedSource(
            name="sebi_rss",
            feed_url=settings.sebi_rss_url,
            source_type="policy",
        ),
        "nse_rss": RssFeedSource(
            name="nse_rss",
            feed_url=settings.nse_rss_url,
            source_type="exchange_announcement",
        ),
        "bse_rss": RssFeedSource(
            name="bse_rss",
            feed_url=settings.bse_rss_url,
            source_type="exchange_announcement",
        ),
    }

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
        for name, provider in app.state.provider_sources.items():
            if provider in {
                app.state.market_source,
                app.state.fred_source,
                app.state.country_source,
                app.state.fx_source,
                app.state.sec_source,
            }:
                continue
            close = getattr(provider, "close", None)
            if close is not None:
                await close()
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
    app.include_router(research_router, prefix="/api/v2/research")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "data-fabric"}

    return app
