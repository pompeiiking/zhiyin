"""第一期 Redis 基础能力。

单实例使用逻辑 DB 隔离数据域，同时始终保留环境与业务域 Key 前缀。业务层只依赖
Data SDK 的 Port；Redis Client、DB 编号、序列化和降级全部留在 Infrastructure。
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from enum import IntEnum
from typing import Any, Mapping, Optional, Sequence

from zhiyin_data_sdk.gateways.cache import CacheGateway

logger = logging.getLogger(__name__)


class RedisLogicalDatabase(IntEnum):
    CACHE = 0
    SESSION = 1
    SCHEDULE = 2
    GUARD = 3
    CRAWL = 4
    KNOWLEDGE = 5
    VECTOR_SYNC = 6
    TEST = 15


DOMAIN_DATABASES: dict[str, RedisLogicalDatabase] = {
    "cache": RedisLogicalDatabase.CACHE,
    "session": RedisLogicalDatabase.SESSION,
    "schedule": RedisLogicalDatabase.SCHEDULE,
    "guard": RedisLogicalDatabase.GUARD,
    "crawl": RedisLogicalDatabase.CRAWL,
    "knowledge": RedisLogicalDatabase.KNOWLEDGE,
    "vector-sync": RedisLogicalDatabase.VECTOR_SYNC,
    "test": RedisLogicalDatabase.TEST,
}

_CACHE_NAMESPACES = {"cache", "profile", "workspace", "registry", "bootstrap"}
_NAMESPACE_DOMAINS = {
    **{namespace: "cache" for namespace in _CACHE_NAMESPACES},
    "session": "session",
    "schedule": "schedule",
    "rate-limit": "guard",
    "idempotency": "guard",
    "dedup": "guard",
    "guard": "guard",
    "crawl": "crawl",
    "knowledge": "knowledge",
    "retrieval": "knowledge",
    "vector-sync": "vector-sync",
    "test": "test",
}


def build_redis_key(env: str, domain: str, entity: str, identifier: str) -> str:
    """构造 ``zhiyin:{env}:{domain}:{entity}:{identifier}``，拒绝空段。"""
    parts = (env, domain, entity, identifier)
    if any(not str(part).strip() for part in parts):
        raise ValueError("Redis Key 的 env/domain/entity/identifier 均不能为空")
    if any(":" in str(part) for part in (env, domain, entity)):
        raise ValueError("Redis Key 的 env/domain/entity 不得包含冒号")
    if domain not in DOMAIN_DATABASES:
        raise ValueError(f"未登记的 Redis 数据域：{domain}")
    return ":".join(("zhiyin", *(str(part).strip() for part in parts)))


class RedisClientFactory:
    """为每个逻辑 DB 创建并复用固定客户端，运行中不执行 ``SELECT``。"""

    def __init__(
        self,
        url: str,
        *,
        password: str = "",
        ssl: bool = False,
        pool_size: int = 20,
        socket_timeout_s: float = 2.0,
        clients: Optional[Mapping[int, Any]] = None,
    ) -> None:
        self._url = url
        self._password = password
        self._ssl = ssl
        self._pool_size = pool_size
        if socket_timeout_s <= 0:
            raise ValueError("Redis socket_timeout_s 必须为正数")
        self._socket_timeout_s = socket_timeout_s
        self._clients: dict[int, Any] = dict(clients or {})

    def client(self, database: int | RedisLogicalDatabase) -> Any:
        db = int(database)
        if db not in {int(item) for item in RedisLogicalDatabase}:
            raise ValueError(f"未登记的 Redis 逻辑库：DB {db}")
        if db not in self._clients:
            self._clients[db] = self._create(db)
        return self._clients[db]

    def domain_store(self, env: str, domain: str) -> "RedisDomainStore":
        try:
            database = DOMAIN_DATABASES[domain]
        except KeyError as exc:
            raise ValueError(f"未登记的 Redis 数据域：{domain}") from exc
        return RedisDomainStore(self.client(database), env=env, domain=domain)

    def _create(self, database: int) -> Any:
        try:
            import redis.asyncio as redis
        except ImportError as exc:  # pragma: no cover - 取决于部署环境
            raise RuntimeError("Redis 已启用，但未安装 redis 依赖；请重新安装项目依赖") from exc

        url = self._url
        if self._ssl and url.startswith("redis://"):
            url = "rediss://" + url[len("redis://") :]
        return redis.from_url(
            url,
            db=database,
            password=self._password or None,
            decode_responses=True,
            max_connections=self._pool_size,
            socket_connect_timeout=self._socket_timeout_s,
            socket_timeout=self._socket_timeout_s,
            health_check_interval=30,
        )

    async def close(self) -> None:
        for client in self._clients.values():
            closer = getattr(client, "aclose", None) or getattr(client, "close", None)
            if closer is not None:
                result = closer()
                if hasattr(result, "__await__"):
                    await result


class RedisCacheGateway(CacheGateway):
    """Redis 缓存实现；不可用时可回退到进程内的可重建缓存。"""

    IMPLEMENTATION_STATUS = "wired"

    def __init__(
        self,
        factory: RedisClientFactory,
        *,
        env: str,
        default_ttl_s: int = 300,
        fallback: Optional[CacheGateway] = None,
    ) -> None:
        self._factory = factory
        self._env = env
        self._default_ttl_s = default_ttl_s
        self._fallback = fallback

    async def get(self, namespace: str, key: str) -> Optional[str]:
        client, redis_key = self._resolve(namespace, key)
        try:
            return await client.get(redis_key)
        except Exception as exc:
            return await self._fallback_get(namespace, key, exc)

    async def set(
        self, namespace: str, key: str, value: str, *, ttl_s: Optional[int] = None
    ) -> None:
        client, redis_key = self._resolve(namespace, key)
        effective = self._default_ttl_s if ttl_s is None else ttl_s
        try:
            if effective > 0:
                await client.set(redis_key, value, ex=effective)
            else:
                raise ValueError("Redis 缓存必须设置正数 TTL")
        except ValueError:
            raise
        except Exception as exc:
            await self._fallback_set(namespace, key, value, effective, exc)

    async def delete(self, namespace: str, key: str) -> None:
        client, redis_key = self._resolve(namespace, key)
        try:
            await client.delete(redis_key)
        except Exception as exc:
            await self._fallback_delete(namespace, key, exc)

    async def delete_many(self, namespace: str, keys: Sequence[str]) -> int:
        if not keys:
            return 0
        resolved = [self._resolve(namespace, key) for key in keys]
        client = resolved[0][0]
        try:
            return int(await client.delete(*(redis_key for _, redis_key in resolved)))
        except Exception as exc:
            if self._fallback is None:
                raise
            logger.warning("Redis 批量删除失败，使用本地缓存降级：namespace=%s error=%s", namespace, type(exc).__name__)
            return await self._fallback.delete_many(namespace, keys)

    async def clear_namespace(self, namespace: str) -> None:
        client, prefix = self._resolve(namespace, "namespace-clear")
        pattern = prefix.rsplit(":", 1)[0] + ":*"
        try:
            batch: list[str] = []
            async for redis_key in client.scan_iter(match=pattern, count=200):
                batch.append(redis_key)
                if len(batch) == 200:
                    await client.delete(*batch)
                    batch.clear()
            if batch:
                await client.delete(*batch)
        except Exception as exc:
            if self._fallback is None:
                raise
            logger.warning("Redis 命名空间清理失败，使用本地缓存降级：namespace=%s error=%s", namespace, type(exc).__name__)
            await self._fallback.clear_namespace(namespace)

    def _resolve(self, namespace: str, key: str) -> tuple[Any, str]:
        try:
            domain = _NAMESPACE_DOMAINS[namespace]
        except KeyError as exc:
            raise ValueError(f"未登记的 Redis namespace：{namespace}") from exc
        database = DOMAIN_DATABASES[domain]
        redis_key = build_redis_key(self._env, domain, namespace, key)
        return self._factory.client(database), redis_key

    async def _fallback_get(self, namespace: str, key: str, exc: Exception) -> Optional[str]:
        if self._fallback is None:
            raise exc
        logger.warning("Redis 读取失败，使用本地缓存降级：namespace=%s error=%s", namespace, type(exc).__name__)
        return await self._fallback.get(namespace, key)

    async def _fallback_set(
        self, namespace: str, key: str, value: str, ttl_s: int, exc: Exception
    ) -> None:
        if self._fallback is None:
            raise exc
        logger.warning("Redis 写入失败，使用本地缓存降级：namespace=%s error=%s", namespace, type(exc).__name__)
        await self._fallback.set(namespace, key, value, ttl_s=ttl_s)

    async def _fallback_delete(self, namespace: str, key: str, exc: Exception) -> None:
        if self._fallback is None:
            raise exc
        logger.warning("Redis 删除失败，使用本地缓存降级：namespace=%s error=%s", namespace, type(exc).__name__)
        await self._fallback.delete(namespace, key)


class RedisDomainStore:
    """绑定单一数据域/逻辑 DB 的通用临时状态适配器。"""

    IMPLEMENTATION_STATUS = "wired"

    def __init__(
        self,
        client: Any,
        *,
        env: str,
        domain: str,
        max_value_bytes: int = 1_048_576,
    ) -> None:
        if domain not in DOMAIN_DATABASES:
            raise ValueError(f"未登记的 Redis 数据域：{domain}")
        self._client = client
        self._env = env
        self._domain = domain
        if max_value_bytes <= 0:
            raise ValueError("Redis 单值容量上限必须为正数")
        self._max_value_bytes = max_value_bytes

    def key(self, entity: str, identifier: str) -> str:
        return build_redis_key(self._env, self._domain, entity, identifier)

    async def get_text(self, entity: str, identifier: str) -> Optional[str]:
        return await self._client.get(self.key(entity, identifier))

    async def set_text(
        self, entity: str, identifier: str, value: str, *, ttl_s: int
    ) -> None:
        if ttl_s <= 0:
            raise ValueError("临时状态必须设置正数 TTL")
        if len(value.encode("utf-8")) > self._max_value_bytes:
            raise ValueError("Redis 临时状态超过单值容量上限")
        await self._client.set(self.key(entity, identifier), value, ex=ttl_s)

    async def get_json(self, entity: str, identifier: str) -> Optional[Any]:
        value = await self.get_text(entity, identifier)
        if value is None:
            return None
        try:
            envelope = json.loads(value)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValueError("Redis JSON 数据格式无效") from exc
        if not isinstance(envelope, dict) or envelope.get("schema_version") != 1:
            raise ValueError("Redis JSON 缺少受支持的 schema_version")
        if "value" not in envelope:
            raise ValueError("Redis JSON 缺少 value 字段")
        return envelope["value"]

    async def set_json(
        self, entity: str, identifier: str, value: Any, *, ttl_s: int
    ) -> None:
        payload = json.dumps(
            {"schema_version": 1, "value": value},
            ensure_ascii=False,
            separators=(",", ":"),
            default=_json_default,
        )
        await self.set_text(entity, identifier, payload, ttl_s=ttl_s)

    async def delete(self, entity: str, identifier: str) -> bool:
        return bool(await self._client.delete(self.key(entity, identifier)))

    async def set_once(
        self, entity: str, identifier: str, value: str, *, ttl_s: int
    ) -> bool:
        if ttl_s <= 0:
            raise ValueError("幂等/去重键必须设置正数 TTL")
        return bool(
            await self._client.set(
                self.key(entity, identifier), value, nx=True, ex=ttl_s
            )
        )

    async def increment(
        self, entity: str, identifier: str, *, ttl_s: int, amount: int = 1
    ) -> int:
        if ttl_s <= 0:
            raise ValueError("计数键必须设置正数 TTL")
        key = self.key(entity, identifier)
        value = int(await self._client.incrby(key, amount))
        if value == amount:
            await self._client.expire(key, ttl_s)
        return value

    async def acquire_lock(
        self, entity: str, identifier: str, owner_token: str, *, ttl_s: int
    ) -> bool:
        return await self.set_once(entity, identifier, owner_token, ttl_s=ttl_s)

    async def release_lock(self, entity: str, identifier: str, owner_token: str) -> bool:
        script = (
            "if redis.call('get', KEYS[1]) == ARGV[1] then "
            "return redis.call('del', KEYS[1]) else return 0 end"
        )
        return bool(await self._client.eval(script, 1, self.key(entity, identifier), owner_token))


def _json_default(value: Any) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise ValueError("Redis JSON 时间必须带时区")
        return value.astimezone(timezone.utc).isoformat()
    raise TypeError(f"不支持的 Redis JSON 类型：{type(value).__name__}")


__all__ = [
    "DOMAIN_DATABASES",
    "RedisCacheGateway",
    "RedisClientFactory",
    "RedisDomainStore",
    "RedisLogicalDatabase",
    "build_redis_key",
]
