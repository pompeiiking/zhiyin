"""第一期 Redis 分库、Key/TTL、幂等、锁与故障降级验收。"""

from __future__ import annotations

import fnmatch
import os
from uuid import uuid4

import pytest

from zhiyin_infrastructure.local.cache import InMemoryCache
from zhiyin_infrastructure.redis import (
    DOMAIN_DATABASES,
    RedisCacheGateway,
    RedisClientFactory,
    RedisLogicalDatabase,
    build_redis_key,
)


class FakeRedis:
    def __init__(self, database: int, *, broken: bool = False) -> None:
        self.database = database
        self.broken = broken
        self.values: dict[str, str] = {}
        self.ttls: dict[str, int] = {}

    def _check(self) -> None:
        if self.broken:
            raise ConnectionError("redis unavailable")

    async def get(self, key: str):
        self._check()
        return self.values.get(key)

    async def set(self, key: str, value: str, *, ex=None, nx=False):
        self._check()
        if nx and key in self.values:
            return False
        self.values[key] = value
        if ex is not None:
            self.ttls[key] = ex
        return True

    async def delete(self, *keys: str):
        self._check()
        removed = 0
        for key in keys:
            if key in self.values:
                removed += 1
                self.values.pop(key)
                self.ttls.pop(key, None)
        return removed

    async def incrby(self, key: str, amount: int):
        self._check()
        value = int(self.values.get(key, "0")) + amount
        self.values[key] = str(value)
        return value

    async def expire(self, key: str, ttl_s: int):
        self._check()
        self.ttls[key] = ttl_s
        return True

    async def eval(self, script: str, number_of_keys: int, key: str, token: str):
        self._check()
        if self.values.get(key) != token:
            return 0
        return await self.delete(key)

    async def scan_iter(self, *, match: str, count: int):
        self._check()
        for key in list(self.values):
            if fnmatch.fnmatch(key, match):
                yield key


def _factory(*, broken: bool = False):
    clients = {db.value: FakeRedis(db.value, broken=broken) for db in RedisLogicalDatabase}
    return RedisClientFactory("redis://unused", clients=clients), clients


def test_logical_database_allocation_is_frozen() -> None:
    assert {name: int(db) for name, db in DOMAIN_DATABASES.items()} == {
        "cache": 0,
        "session": 1,
        "schedule": 2,
        "guard": 3,
        "crawl": 4,
        "knowledge": 5,
        "vector-sync": 6,
        "test": 15,
    }


def test_key_requires_environment_domain_entity_and_identifier() -> None:
    assert build_redis_key("dev", "crawl", "snapshot", "batch-1") == (
        "zhiyin:dev:crawl:snapshot:batch-1"
    )
    with pytest.raises(ValueError):
        build_redis_key("", "crawl", "snapshot", "batch-1")
    with pytest.raises(ValueError):
        build_redis_key("dev", "unknown", "snapshot", "batch-1")


async def test_cache_uses_db_zero_prefix_ttl_and_namespace_isolation() -> None:
    factory, clients = _factory()
    cache = RedisCacheGateway(factory, env="dev")

    await cache.set("workspace", "u1", "workspace", ttl_s=60)
    await cache.set("profile", "u1", "profile", ttl_s=120)

    redis = clients[0]
    assert redis.values["zhiyin:dev:cache:workspace:u1"] == "workspace"
    assert redis.values["zhiyin:dev:cache:profile:u1"] == "profile"
    assert redis.ttls["zhiyin:dev:cache:workspace:u1"] == 60
    assert await cache.get("workspace", "u1") == "workspace"
    await cache.clear_namespace("workspace")
    assert await cache.get("workspace", "u1") is None
    assert await cache.get("profile", "u1") == "profile"


async def test_domain_stores_bind_db_and_support_guard_primitives() -> None:
    factory, clients = _factory()
    schedule = factory.domain_store("dev", "schedule")
    guard = factory.domain_store("dev", "guard")
    crawl = factory.domain_store("dev", "crawl")
    knowledge = factory.domain_store("dev", "knowledge")
    vector = factory.domain_store("dev", "vector-sync")

    await schedule.set_json("task", "s1", {"due": "soon"}, ttl_s=600)
    await crawl.set_text("snapshot", "c1", "raw", ttl_s=3600)
    await knowledge.set_text("query", "q1", "hits", ttl_s=300)
    await vector.set_text("checkpoint", "v1", "42", ttl_s=1800)
    assert "zhiyin:dev:schedule:task:s1" in clients[2].values
    assert "zhiyin:dev:crawl:snapshot:c1" in clients[4].values
    assert "zhiyin:dev:knowledge:query:q1" in clients[5].values
    assert "zhiyin:dev:vector-sync:checkpoint:v1" in clients[6].values

    assert await guard.set_once("idempotency", "evt-1", "1", ttl_s=3600)
    assert not await guard.set_once("idempotency", "evt-1", "1", ttl_s=3600)
    assert await guard.increment("rate", "u1", ttl_s=60) == 1
    assert await guard.increment("rate", "u1", ttl_s=60) == 2
    assert await guard.acquire_lock("lock", "asset-u1", "owner-a", ttl_s=30)
    assert not await guard.release_lock("lock", "asset-u1", "owner-b")
    assert await guard.release_lock("lock", "asset-u1", "owner-a")


async def test_temporary_domain_store_rejects_missing_ttl() -> None:
    factory, _ = _factory()
    store = factory.domain_store("test", "test")
    with pytest.raises(ValueError):
        await store.set_text("case", "one", "value", ttl_s=0)

    cache = RedisCacheGateway(factory, env="test")
    with pytest.raises(ValueError):
        await cache.set("workspace", "u1", "value", ttl_s=0)


async def test_cache_connection_failure_falls_back_to_rebuildable_memory() -> None:
    factory, _ = _factory(broken=True)
    fallback = InMemoryCache()
    cache = RedisCacheGateway(factory, env="dev", fallback=fallback)

    await cache.set("workspace", "u1", "payload", ttl_s=60)
    assert await cache.get("workspace", "u1") == "payload"
    await cache.delete("workspace", "u1")
    assert await cache.get("workspace", "u1") is None


def test_unknown_namespace_and_database_fail_closed() -> None:
    factory, _ = _factory()
    cache = RedisCacheGateway(factory, env="dev")
    with pytest.raises(ValueError):
        cache._resolve("unknown", "u1")
    with pytest.raises(ValueError):
        factory.client(14)


@pytest.mark.integration
async def test_real_redis_logical_databases_ttl_and_cleanup() -> None:
    """显式设置 ZHIYIN_TEST_REDIS_URL 时验证真实实例；只删本用例唯一键。"""
    url = os.getenv("ZHIYIN_TEST_REDIS_URL", "").strip()
    if not url:
        pytest.skip("未设置 ZHIYIN_TEST_REDIS_URL")
    factory = RedisClientFactory(url)
    probe = uuid4().hex
    touched: list[tuple[object, str]] = []
    try:
        for domain, database in DOMAIN_DATABASES.items():
            store = factory.domain_store("test", domain)
            key = store.key("integration", probe)
            client = factory.client(database)
            touched.append((client, key))
            await store.set_text("integration", probe, domain, ttl_s=60)
            assert await client.get(key) == domain
            ttl = int(await client.ttl(key))
            assert 0 < ttl <= 60
    finally:
        for client, key in touched:
            await client.delete(key)
        await factory.close()
