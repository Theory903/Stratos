"""Kafka consumer wrapper for worker processes."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

from aiokafka import AIOKafkaConsumer


class KafkaEventConsumer:
    """Async generator over Kafka events."""

    def __init__(self, *, brokers: str, topic: str, group_id: str) -> None:
        self._consumer = AIOKafkaConsumer(
            topic,
            bootstrap_servers=brokers,
            group_id=group_id,
            value_deserializer=lambda value: json.loads(value.decode("utf-8")),
            key_deserializer=lambda value: value.decode("utf-8") if value else None,
            auto_offset_reset="earliest",
        )

    async def start(self) -> None:
        await self._consumer.start()

    async def stop(self) -> None:
        await self._consumer.stop()

    async def messages(self) -> AsyncIterator[dict]:
        async for message in self._consumer:
            yield message.value
