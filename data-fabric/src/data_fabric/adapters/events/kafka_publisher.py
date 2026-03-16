"""Kafka event publisher adapter — implements EventPublisher outbound port."""

from __future__ import annotations

import json
import logging

from aiokafka import AIOKafkaProducer

logger = logging.getLogger(__name__)


class KafkaEventPublisher:
    """Kafka-backed event publisher implementing EventPublisher protocol.

    Manages its own producer lifecycle. Call start() before publish()
    and stop() on shutdown.
    """

    def __init__(self, brokers: str) -> None:
        self._brokers = brokers
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        """Start the Kafka producer."""
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self._brokers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
        )
        await self._producer.start()
        logger.info("Kafka producer started on %s", self._brokers)

    async def publish(self, topic: str, key: str, payload: dict) -> None:
        """Publish a domain event to Kafka."""
        if self._producer is None:
            logger.warning("Kafka producer not started — dropping event on %s", topic)
            return
        await self._producer.send_and_wait(topic, value=payload, key=key)
        logger.debug("Published event to %s: key=%s", topic, key)

    async def stop(self) -> None:
        """Flush and stop the producer."""
        if self._producer is not None:
            await self._producer.stop()
            logger.info("Kafka producer stopped")
