"""Gateway 装配表：外部能力用哪套实现。

第二期的八个替换点（MySQL / Kafka / pgvector / SSE / MinIO / Redis / pami IAM /
真实模型）全部落在这里。每个 `if` 都是一个替换点，业务代码不受影响。

骨架状态由实现类自己声明（`IMPLEMENTATION_STATUS`），不再靠模块路径猜：
- `wired`    ：真实可用的实现；
- `skeleton` ：形状对、能力占位（如哈希伪嵌入），必须让使用者看见。
"""

from __future__ import annotations

from typing import Any

from zhiyin_boot.settings import Settings


def build_gateways(settings: Settings) -> dict[str, Any]:
    """按配置装配 Gateway。默认全走 local（第一期可独立跑通）。"""
    from zhiyin_infrastructure.local.auth import DefaultPassAuth
    from zhiyin_infrastructure.local.cache import InMemoryCache
    from zhiyin_infrastructure.local.embedding import LocalHashEmbedder
    from zhiyin_infrastructure.local.knowledge import LocalSearchGateway
    from zhiyin_infrastructure.local.llm import LocalOrMockLLM
    from zhiyin_infrastructure.local.messaging import (
        InMemoryEventBus,
        LocalNotify,
        LocalScheduler,
    )
    from zhiyin_infrastructure.local.object_store import LocalFileStore
    from zhiyin_infrastructure.local.security import NoopRateLimit, NoopSecurity
    from zhiyin_infrastructure.local.vector_store import LocalVectorStore

    event_bus = InMemoryEventBus()

    gateways: dict[str, Any] = {
        "llm": LocalOrMockLLM(),
        "embedding": LocalHashEmbedder(),
        "search": LocalSearchGateway(settings.local_knowledge_dir),
        "vector": LocalVectorStore(),
        "cache": InMemoryCache(),
        "object_store": LocalFileStore(settings.local_object_dir),
        "event_bus": event_bus,
        # 调度器必须能投递事件，否则主动事件（停滞检测）永远不触发。显式注入。
        "scheduler": LocalScheduler(event_bus),
        "notifier": LocalNotify(),
        "auth": DefaultPassAuth(),
        "security": NoopSecurity(),
        "rate_limit": NoopRateLimit(),
        # raw_query 是"受限裸查询逃生口"，只给基础设施层的 Repository 实现用。
        # 第一期没有 MySQL 实现，因此显式保持未装配（不做假实现）。
        "raw_query": None,
    }

    if settings.redis_url:
        from zhiyin_infrastructure.redis import RedisCacheGateway, RedisClientFactory

        redis_factory = RedisClientFactory(
            settings.redis_url,
            password=settings.redis_password,
            ssl=settings.redis_ssl,
            pool_size=settings.redis_pool_size,
            socket_timeout_s=settings.redis_socket_timeout_s,
        )
        gateways["cache"] = RedisCacheGateway(
            redis_factory,
            env=settings.env,
            fallback=InMemoryCache(),
        )
        # DB 1–6 是分库策略，不是六个必须常驻的业务对象。保留统一工厂，等真实
        # Adapter / Worker 出现调用方时再用 domain_store(env, domain) 惰性创建；
        # 避免把无人消费且无降级兜底的连接误报成“已接线”。
        gateways["redis_factory"] = redis_factory

    # ---------- pami 替换点（§十） ----------
    if settings.use_pami_llm:
        from zhiyin_infrastructure.pami.adapters import PamiLLMGateway

        gateways["llm"] = PamiLLMGateway(
            settings.pami_base_url,
            settings.pami_agent_api_key or settings.pami_api_key,
            timeout_s=settings.pami_timeout_s,
        )
    if settings.use_pami_embedding:
        from zhiyin_infrastructure.pami.adapters import PamiEmbedGateway

        gateways["embedding"] = PamiEmbedGateway(
            settings.pami_base_url,
            settings.pami_embedding_model_id,
            timeout_s=settings.pami_timeout_s,
        )
    if settings.use_pami_search:
        from zhiyin_infrastructure.pami.adapters import PamiSearchGateway

        gateways["search"] = PamiSearchGateway(
            settings.pami_base_url,
            settings.pami_rag_api_key or settings.pami_api_key,
            timeout_s=settings.pami_timeout_s,
        )
    if settings.use_pami_auth:
        from zhiyin_infrastructure.pami.adapters import PamiAuthGateway

        gateways["auth"] = PamiAuthGateway(
            settings.pami_base_url,
            settings.pami_jwt_secret,
            org_id=settings.pami_org_id,
            timeout_s=settings.pami_timeout_s,
        )

    if settings.use_pgvector:
        from zhiyin_infrastructure.pgvector import PgVectorGateway

        gateways["vector"] = PgVectorGateway(settings.vector_database_url)

    if settings.use_pgvector and settings.use_pami_embedding:
        from zhiyin_infrastructure.search import RrfHybridSearchGateway

        gateways["search"] = RrfHybridSearchGateway(
            gateways["search"],
            gateways["embedding"],
            gateways["vector"],
            rrf_k=settings.search_rrf_k,
        )

    if settings.use_mysql and settings.database_url:
        from zhiyin_infrastructure.mysql import SqlAlchemyRawQueryGateway

        gateways["raw_query"] = SqlAlchemyRawQueryGateway(settings.database_url)
        search = gateways.get("search")
        if hasattr(search, "configure_authority"):
            from zhiyin_infrastructure.persistence.retrieval_documents import (
                RetrievalDocumentStore,
            )

            authority = RetrievalDocumentStore(settings.database_url)
            search.configure_authority(authority)
            gateways["retrieval_authority"] = authority

    if settings.use_minio:
        from zhiyin_infrastructure.minio import MinioObjectStore

        gateways["object_store"] = MinioObjectStore(
            settings.minio_endpoint,
            settings.minio_access_key,
            settings.minio_secret_key,
            bucket=settings.minio_bucket,
            secure=settings.minio_secure,
        )

    return gateways


__all__ = ["build_gateways"]
