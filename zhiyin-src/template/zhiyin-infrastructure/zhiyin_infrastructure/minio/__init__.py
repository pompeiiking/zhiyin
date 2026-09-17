"""MinIO 对象存储实现。"""

from __future__ import annotations

import asyncio
import io
from datetime import timezone
from pathlib import PurePosixPath
from typing import Any, Optional

from zhiyin_data_sdk.errors import UnavailableError
from zhiyin_data_sdk.gateways.storage import ObjectStoreGateway, StoredObject


class MinioObjectStore(ObjectStoreGateway):
    IMPLEMENTATION_STATUS = "wired"

    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        *,
        bucket: str = "zhiyin-assets",
        secure: bool = True,
        client: Any | None = None,
    ) -> None:
        if not endpoint or not bucket:
            raise ValueError("MinIO endpoint 和 bucket 不能为空")
        if client is None:
            from minio import Minio

            client = Minio(
                endpoint,
                access_key=access_key,
                secret_key=secret_key,
                secure=secure,
            )
        self._client = client
        self._bucket = bucket
        self._locks: dict[str, asyncio.Lock] = {}
        self._ready = False

    async def _ensure_bucket(self) -> None:
        if self._ready:
            return
        exists = await asyncio.to_thread(self._client.bucket_exists, self._bucket)
        if not exists:
            await asyncio.to_thread(self._client.make_bucket, self._bucket)
        self._ready = True

    async def put(
        self, key: str, data: bytes, *, content_type: str = "application/octet-stream"
    ) -> StoredObject:
        self._validate_key(key)
        await self._ensure_bucket()
        try:
            result = await asyncio.to_thread(
                self._client.put_object,
                self._bucket,
                key,
                io.BytesIO(data),
                len(data),
                content_type=content_type,
            )
        except Exception as exc:
            raise UnavailableError("MinIO 写入失败", cause=exc) from exc
        return StoredObject(key=key, size=len(data), content_type=content_type, etag=result.etag)

    async def compare_and_swap(
        self,
        key: str,
        data: bytes,
        *,
        expected_etag: Optional[str],
        content_type: str = "application/octet-stream",
    ) -> Optional[StoredObject]:
        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            current = await self.stat(key)
            if (current.etag if current else None) != expected_etag:
                return None
            return await self.put(key, data, content_type=content_type)

    async def get(self, key: str) -> bytes:
        self._validate_key(key)
        await self._ensure_bucket()
        try:
            response = await asyncio.to_thread(self._client.get_object, self._bucket, key)
            try:
                return await asyncio.to_thread(response.read)
            finally:
                response.close()
                response.release_conn()
        except Exception as exc:
            if self._is_missing(exc):
                raise FileNotFoundError(f"对象不存在：{key}") from exc
            raise UnavailableError("MinIO 读取失败", cause=exc) from exc

    async def stat(self, key: str) -> Optional[StoredObject]:
        self._validate_key(key)
        await self._ensure_bucket()
        try:
            item = await asyncio.to_thread(self._client.stat_object, self._bucket, key)
        except Exception as exc:
            if self._is_missing(exc):
                return None
            raise UnavailableError("MinIO 元数据读取失败", cause=exc) from exc
        updated_at = item.last_modified
        if updated_at is not None and updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)
        return StoredObject(
            key=key,
            size=int(item.size),
            content_type=item.content_type or "application/octet-stream",
            updated_at=updated_at,
            etag=item.etag,
        )

    async def delete(self, key: str) -> None:
        self._validate_key(key)
        await self._ensure_bucket()
        try:
            await asyncio.to_thread(self._client.remove_object, self._bucket, key)
        except Exception as exc:
            if not self._is_missing(exc):
                raise UnavailableError("MinIO 删除失败", cause=exc) from exc

    def build_key(self, user_id: str, asset_type: str, version: int, ext: str) -> str:
        key = f"{user_id}/{asset_type}/v{version}.{ext.lstrip('.')}"
        self._validate_key(key)
        return key

    @staticmethod
    def _validate_key(key: str) -> None:
        path = PurePosixPath(key)
        if not key or key.startswith(("/", "\\")) or ".." in path.parts or "\\" in key:
            raise ValueError(f"非法对象键：{key}")

    @staticmethod
    def _is_missing(exc: Exception) -> bool:
        return str(getattr(exc, "code", "")) in {"NoSuchKey", "NoSuchObject", "NoSuchBucket"}


__all__ = ["MinioObjectStore"]
