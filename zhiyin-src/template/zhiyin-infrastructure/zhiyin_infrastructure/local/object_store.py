"""本地文件对象存储（LocalFileStore）。

第一期：写本地目录。TODO(第二期)：替换为 MinIO（见 §十替换点）。

安全约束（《第一期技术架构文档》§7.1）：第一期禁止写入真实敏感信息，
因此本实现只负责落盘，不做加密；接生产安全时换 NoopSecurity 为真实实现，
本类不需要改动。
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional
from uuid import uuid4

from zhiyin_data_sdk.gateways.storage import ObjectStoreGateway, StoredObject


_PATH_LOCKS: dict[Path, threading.Lock] = {}
_PATH_LOCKS_GUARD = threading.Lock()


class LocalFileStore(ObjectStoreGateway):
    """本地目录实现。"""

    def __init__(self, root: str = "data/objects") -> None:
        self._root = Path(root).resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    async def put(
        self, key: str, data: bytes, *, content_type: str = "application/octet-stream"
    ) -> StoredObject:
        path = self._resolve(key)
        await asyncio.to_thread(self._write_locked, path, data)
        return self._stored_object(key, data, content_type)

    async def compare_and_swap(
        self,
        key: str,
        data: bytes,
        *,
        expected_etag: Optional[str],
        content_type: str = "application/octet-stream",
    ) -> Optional[StoredObject]:
        path = self._resolve(key)
        changed = await asyncio.to_thread(
            self._compare_and_swap, path, data, expected_etag
        )
        return self._stored_object(key, data, content_type) if changed else None

    async def get(self, key: str) -> bytes:
        path = self._resolve(key)
        data = await asyncio.to_thread(self._read_locked, path)
        if data is None:
            raise FileNotFoundError(f"对象不存在：{key}")
        return data

    async def stat(self, key: str) -> Optional[StoredObject]:
        path = self._resolve(key)
        result = await asyncio.to_thread(self._stat_locked, path)
        if result is None:
            return None
        size, modified_at, etag = result
        return StoredObject(
            key=key,
            size=size,
            content_type="application/octet-stream",
            updated_at=datetime.fromtimestamp(modified_at, tz=timezone.utc),
            etag=etag,
        )

    async def delete(self, key: str) -> None:
        path = self._resolve(key)
        await asyncio.to_thread(self._delete_locked, path)

    def build_key(self, user_id: str, asset_type: str, version: int, ext: str) -> str:
        """统一对象键：{user_id}/{asset_type}/v{version}.{ext}"""
        return f"{user_id}/{asset_type}/v{version}.{ext.lstrip('.')}"

    # ---------- 内部 ----------

    def _resolve(self, key: str) -> Path:
        """解析对象键并挡住路径穿越。

        对象键来自业务层，正常情况下不含 `..`；这里仍然显式校验，
        避免本地实现被当作任意文件读写入口。
        """
        root = self._root
        path = Path(os.path.abspath(root / key))
        normalized_root = os.path.normcase(os.path.abspath(root))
        normalized_path = os.path.normcase(os.path.abspath(path))
        if os.path.commonpath((normalized_root, normalized_path)) != normalized_root:
            raise ValueError(f"非法对象键（越出存储根目录）：{key}")
        return path

    @staticmethod
    def _write(path: Path, data: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
        try:
            temporary.write_bytes(data)
            for attempt in range(5):
                try:
                    os.replace(temporary, path)
                    break
                except PermissionError:
                    if attempt == 4:
                        raise
                    time.sleep(0.01 * (attempt + 1))
        finally:
            temporary.unlink(missing_ok=True)

    @classmethod
    def _path_lock(cls, path: Path) -> threading.Lock:
        with _PATH_LOCKS_GUARD:
            return _PATH_LOCKS.setdefault(path, threading.Lock())

    @classmethod
    def _write_locked(cls, path: Path, data: bytes) -> None:
        with cls._path_lock(path):
            with cls._file_lock(path):
                cls._write(path, data)

    @classmethod
    def _read_locked(cls, path: Path) -> Optional[bytes]:
        with cls._path_lock(path):
            with cls._file_lock(path):
                return path.read_bytes() if path.is_file() else None

    @classmethod
    def _stat_locked(cls, path: Path) -> Optional[tuple[int, float, str]]:
        with cls._path_lock(path):
            with cls._file_lock(path):
                if not path.is_file():
                    return None
                data = path.read_bytes()
                info = path.stat()
                return info.st_size, info.st_mtime, hashlib.sha256(data).hexdigest()

    @classmethod
    def _delete_locked(cls, path: Path) -> None:
        with cls._path_lock(path):
            with cls._file_lock(path):
                path.unlink(missing_ok=True)

    @classmethod
    def _compare_and_swap(
        cls, path: Path, data: bytes, expected_etag: Optional[str]
    ) -> bool:
        with cls._path_lock(path):
            with cls._file_lock(path):
                current_etag = (
                    hashlib.sha256(path.read_bytes()).hexdigest()
                    if path.is_file()
                    else None
                )
                if current_etag != expected_etag:
                    return False
                cls._write(path, data)
                return True

    @staticmethod
    @contextmanager
    def _file_lock(path: Path) -> Iterator[None]:
        """用独立锁文件串行化跨进程的读取、条件写和替换。"""
        path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = path.with_name(f".{path.name}.lock")
        with lock_path.open("a+b") as handle:
            if os.name == "nt":
                import msvcrt

                handle.seek(0, os.SEEK_END)
                if handle.tell() == 0:
                    handle.write(b"0")
                    handle.flush()
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
                try:
                    yield
                finally:
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:  # pragma: no cover - Windows 工作区之外的兼容路径
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    @staticmethod
    def _stored_object(key: str, data: bytes, content_type: str) -> StoredObject:
        return StoredObject(
            key=key,
            size=len(data),
            content_type=content_type,
            updated_at=datetime.now(timezone.utc),
            etag=hashlib.sha256(data).hexdigest(),
        )


__all__ = ["LocalFileStore"]
