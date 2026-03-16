"""S3-compatible object storage adapter."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any

import boto3
from botocore.exceptions import ClientError


class MinioObjectStore:
    """Persist immutable raw payloads in MinIO/S3."""

    def __init__(
        self,
        *,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        bucket: str,
    ) -> None:
        self._bucket = bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )

    async def ensure_bucket(self) -> None:
        await asyncio.to_thread(self._ensure_bucket_sync)

    def _ensure_bucket_sync(self) -> None:
        try:
            self._client.head_bucket(Bucket=self._bucket)
        except ClientError:
            self._client.create_bucket(Bucket=self._bucket)

    async def put_raw_payload(
        self,
        *,
        provider: str,
        entity_type: str,
        entity_id: str,
        payload: dict[str, Any],
        request_hash: str,
    ) -> str:
        now = datetime.now(timezone.utc)
        day = now.strftime("%Y%m%d")
        stamp = now.strftime("%Y%m%dT%H%M%SZ")
        key = (
            f"raw/{provider}/{entity_type}/{entity_id}/{day}/"
            f"{stamp}_{stamp}/{request_hash}.json"
        )
        body = json.dumps(payload, default=str).encode("utf-8")
        await asyncio.to_thread(
            self._client.put_object,
            Bucket=self._bucket,
            Key=key,
            Body=body,
            ContentType="application/json",
        )
        return key
