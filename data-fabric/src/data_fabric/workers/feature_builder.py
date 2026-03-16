"""Feature-builder worker entrypoint."""

from __future__ import annotations

import asyncio

from data_fabric.adapters.queue_consumers import KafkaEventConsumer
from data_fabric.application import FeatureBuilderUseCase
from data_fabric.workers.runtime import build_runtime, close_runtime


async def main() -> None:
    runtime = await build_runtime()
    consumer = KafkaEventConsumer(
        brokers=runtime.settings.kafka_brokers,
        topic="ingest.completed",
        group_id="data-fabric-feature-builder",
    )
    use_case = FeatureBuilderUseCase(
        store=runtime.store,
        documents=runtime.documents,
        events=runtime.events,
    )
    await consumer.start()
    try:
        async for message in consumer.messages():
            await use_case.execute(message)
    finally:
        await consumer.stop()
        await close_runtime(runtime)


if __name__ == "__main__":
    asyncio.run(main())
