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
    from zhiyin_infrastructure.local.knowledge import (
        LocalKeywordSearch,
        LocalKnowledgeRepo,
    )
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
        "knowledge": LocalKnowledgeRepo(settings.local_knowledge_dir),
        "search": LocalKeywordSearch(settings.local_knowledge_dir),
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

    # ---------- pami 替换点（§十） ----------
    # 未实现的分支在首次调用时抛 NotImplementedError，而不是静默回落本地 ——
    # 静默回落会让"已经切到 pami"变成假象，问题推迟到线上才暴露。
    if settings.use_pami_llm:
        from zhiyin_infrastructure.pami.adapters import PamiLLMGateway

        gateways["llm"] = PamiLLMGateway(settings.pami_base_url, settings.pami_api_key)
    if settings.use_pami_knowledge:
        from zhiyin_infrastructure.pami.adapters import PamiKnowledgeGateway

        gateways["knowledge"] = PamiKnowledgeGateway(
            settings.pami_base_url, settings.pami_api_key
        )
    if settings.use_pami_auth:
        from zhiyin_infrastructure.pami.adapters import PamiAuthGateway

        gateways["auth"] = PamiAuthGateway(
            settings.pami_base_url, settings.pami_jwt_secret
        )

    return gateways


__all__ = ["build_gateways"]
