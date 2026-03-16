"""Shared runtime bootstrapping for worker processes."""

from __future__ import annotations

from dataclasses import dataclass

from data_fabric.adapters.database import PostgresDataStore, create_tables, get_session_factory, init_engine
from data_fabric.adapters.document_store import MongoDocumentStore
from data_fabric.adapters.events import KafkaEventPublisher
from data_fabric.adapters.object_store import MinioObjectStore
from data_fabric.adapters.providers import (
    FREDMacroSource,
    PolygonMarketSource,
    SecEdgarSource,
    WorldBankCountrySource,
)
from data_fabric.config import Settings


@dataclass(slots=True)
class WorkerRuntime:
    settings: Settings
    store: PostgresDataStore
    documents: MongoDocumentStore
    object_store: MinioObjectStore
    events: KafkaEventPublisher
    providers: dict[str, object]


async def build_runtime() -> WorkerRuntime:
    settings = Settings()
    init_engine(settings)
    await create_tables()

    store = PostgresDataStore(get_session_factory())
    documents = MongoDocumentStore(settings.mongo_url, settings.mongo_database)
    object_store = MinioObjectStore(
        endpoint_url=settings.s3_endpoint,
        access_key=settings.s3_access_key,
        secret_key=settings.s3_secret_key,
        bucket=settings.s3_bucket,
    )
    await object_store.ensure_bucket()
    events = KafkaEventPublisher(settings.kafka_brokers)
    await events.start()

    providers: dict[str, object] = {
        "fred": FREDMacroSource(api_key=settings.fred_api_key),
        "world_bank": WorldBankCountrySource(base_url=settings.world_bank_base_url),
        "sec": SecEdgarSource(
            base_url=settings.sec_base_url,
            ticker_map_url=settings.sec_ticker_map_url,
            user_agent=settings.sec_user_agent,
        ),
        "massive": PolygonMarketSource(
            api_key=settings.market_api_key,
            base_url=settings.market_base_url,
        ),
    }
    return WorkerRuntime(
        settings=settings,
        store=store,
        documents=documents,
        object_store=object_store,
        events=events,
        providers=providers,
    )


async def close_runtime(runtime: WorkerRuntime) -> None:
    await runtime.events.stop()
    await runtime.documents.close()
    for provider in runtime.providers.values():
        close = getattr(provider, "close", None)
        if close is not None:
            await close()
