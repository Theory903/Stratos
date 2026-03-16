"""Redis cache adapter — implements CacheStore outbound port."""

from __future__ import annotations

import redis.asyncio as redis


class RedisCacheStore:
    """Redis-backed cache implementing the CacheStore protocol.

    Thread-safe: redis.asyncio handles connection pooling internally.
    """

    def __init__(self, url: str) -> None:
        self._client = redis.from_url(url, decode_responses=True)

    async def get(self, key: str) -> str | None:
        return await self._client.get(key)

    async def set(self, key: str, value: str, ttl_seconds: int = 300) -> None:
        await self._client.set(key, value, ex=ttl_seconds)

    async def delete(self, key: str) -> None:
        await self._client.delete(key)

    async def close(self) -> None:
        await self._client.aclose()
