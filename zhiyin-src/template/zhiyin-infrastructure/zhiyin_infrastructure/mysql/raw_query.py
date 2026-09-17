"""仅供 Infrastructure 内部使用的受限 SQL 查询实现。"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import time
from collections.abc import Mapping, Sequence
from typing import Any

from zhiyin_data_sdk.errors import UnavailableError, ValidationError
from zhiyin_data_sdk.gateways.db import Params, RawQueryGateway

_FETCH_VERBS = frozenset({"SELECT", "SHOW", "DESCRIBE", "EXPLAIN"})
_WRITE_VERBS = frozenset({"INSERT", "UPDATE", "DELETE"})
_LOGGER = logging.getLogger("zhiyin.raw_query.audit")


def _async_url(database_url: str) -> str:
    value = database_url.strip()
    if value.startswith("mysql+pymysql://"):
        return "mysql+asyncmy://" + value.removeprefix("mysql+pymysql://")
    if value.startswith("mysql://"):
        return "mysql+asyncmy://" + value.removeprefix("mysql://")
    return value


def _verb(sql: str) -> str:
    statement = sql.strip()
    if not statement:
        raise ValidationError("SQL 不能为空")
    without_trailing = statement[:-1] if statement.endswith(";") else statement
    if ";" in without_trailing:
        raise ValidationError("禁止执行多条 SQL")
    match = re.match(r"([A-Za-z]+)", statement)
    if match is None:
        raise ValidationError("无法识别 SQL 类型")
    return match.group(1).upper()


class SqlAlchemyRawQueryGateway(RawQueryGateway):
    """限制语句类型、行数与超时的 MySQL 查询逃生口。"""

    IMPLEMENTATION_STATUS = "wired"

    def __init__(
        self,
        database_url: str,
        *,
        max_rows: int = 1000,
        timeout_s: float = 5.0,
        pool_size: int = 5,
        engine: Any | None = None,
    ) -> None:
        if max_rows <= 0:
            raise ValueError("max_rows 必须大于 0")
        if timeout_s <= 0:
            raise ValueError("timeout_s 必须大于 0")
        self._max_rows = max_rows
        self._timeout_s = timeout_s
        if engine is None:
            from sqlalchemy.ext.asyncio import create_async_engine

            engine = create_async_engine(
                _async_url(database_url),
                pool_pre_ping=True,
                pool_size=pool_size,
            )
        self._engine = engine

    @staticmethod
    async def _execute(connection: Any, sql: str, params: Params) -> Any:
        if params is None:
            return await connection.exec_driver_sql(sql)
        if isinstance(params, Mapping):
            from sqlalchemy import text

            return await connection.execute(text(sql), dict(params))
        return await connection.exec_driver_sql(sql, tuple(params))

    async def fetch_all(self, sql: str, params: Params = None) -> list[dict[str, Any]]:
        verb = _verb(sql)
        if verb not in _FETCH_VERBS:
            raise ValidationError("fetch_all 只允许只读 SQL")
        started = time.perf_counter()
        try:
            async def query() -> list[dict[str, Any]]:
                async with self._engine.connect() as connection:
                    result = await self._execute(connection, sql, params)
                    return [dict(row) for row in result.mappings().fetchmany(self._max_rows)]

            rows = await asyncio.wait_for(query(), timeout=self._timeout_s)
            self._audit(sql, verb, "ok", started, len(rows))
            return rows
        except ValidationError:
            raise
        except Exception as exc:
            self._audit(sql, verb, "error", started, 0)
            raise UnavailableError("MySQL 查询失败", cause=exc) from exc

    async def fetch_one(self, sql: str, params: Params = None) -> dict[str, Any] | None:
        rows = await self.fetch_all(sql, params)
        return rows[0] if rows else None

    async def execute(self, sql: str, params: Params = None) -> int:
        verb = _verb(sql)
        if verb not in _WRITE_VERBS:
            raise ValidationError("execute 只允许 INSERT / UPDATE / DELETE")
        started = time.perf_counter()
        try:
            async def query() -> int:
                async with self._engine.begin() as connection:
                    result = await self._execute(connection, sql, params)
                    return max(int(result.rowcount or 0), 0)

            affected = await asyncio.wait_for(query(), timeout=self._timeout_s)
            self._audit(sql, verb, "ok", started, affected)
            return affected
        except ValidationError:
            raise
        except Exception as exc:
            self._audit(sql, verb, "error", started, 0)
            raise UnavailableError("MySQL 写入失败", cause=exc) from exc

    async def execute_many(self, sql: str, rows: Sequence[Sequence[Any]]) -> int:
        verb = _verb(sql)
        if verb not in _WRITE_VERBS:
            raise ValidationError("execute_many 只允许 INSERT / UPDATE / DELETE")
        if not rows:
            return 0
        started = time.perf_counter()
        try:
            async def query() -> int:
                async with self._engine.begin() as connection:
                    result = await connection.exec_driver_sql(
                        sql, [tuple(row) for row in rows]
                    )
                    return max(int(result.rowcount or 0), 0)

            affected = await asyncio.wait_for(query(), timeout=self._timeout_s)
            self._audit(sql, verb, "ok", started, affected)
            return affected
        except ValidationError:
            raise
        except Exception as exc:
            self._audit(sql, verb, "error", started, 0)
            raise UnavailableError("MySQL 批量写入失败", cause=exc) from exc

    @staticmethod
    def _audit(sql: str, verb: str, status: str, started: float, rows: int) -> None:
        # 不记录 SQL 原文或参数，避免检索条件中的个人信息进入日志。
        _LOGGER.info(
            "raw_query verb=%s statement_hash=%s status=%s rows=%d latency_ms=%d",
            verb,
            hashlib.sha256(sql.encode("utf-8")).hexdigest()[:16],
            status,
            rows,
            int((time.perf_counter() - started) * 1000),
        )

    async def close(self) -> None:
        await self._engine.dispose()


__all__ = ["SqlAlchemyRawQueryGateway"]
