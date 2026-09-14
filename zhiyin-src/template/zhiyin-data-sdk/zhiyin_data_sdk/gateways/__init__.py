"""Gateway 接口集合（传输 / 外部能力契约）。

Gateway = 对外部能力（模型 / 嵌入 / 向量 / 缓存 / 裸查询 / 知识库 / 检索 /
对象存储 / 事件 / 调度 / 通知 / 鉴权 / 安全 / 限流）的抽象。第一期全部提供
Local / Mock / Noop 默认实现，由 zhiyin-boot 装配；后续替换为 pami / MySQL /
pgvector / Redis / Kafka 真实适配器时，上层代码不变。

分工口径：
- 本包只定义**抽象与数据形状**，实现一律在 `zhiyin-infrastructure`；
- 业务层与编排层只面向抽象编程，装配处在 `zhiyin-boot/container`；
- 语义契约（信封 / 幂等 / 冷却策略）在 `zhiyin_orchestration`，本包只管传输。
"""

from zhiyin_data_sdk.gateways.ai import (
    EmbedGateway,
    KnowledgeGateway,
    KnowledgeHit,
    LLMGateway,
    LLMMessage,
    LLMResult,
    SearchGateway,
    SearchHit,
)
from zhiyin_data_sdk.gateways.cache import CacheGateway
from zhiyin_data_sdk.gateways.db import Params, RawQueryGateway
from zhiyin_data_sdk.gateways.storage import ObjectStoreGateway, StoredObject
from zhiyin_data_sdk.gateways.messaging import (
    EventBusGateway,
    NotifyGateway,
    NotifyResult,
    ScheduledTask,
    SchedulerGateway,
)
from zhiyin_data_sdk.gateways.security import (
    AuthGateway,
    AuthPrincipal,
    RateLimitGateway,
    SecurityGateway,
)
from zhiyin_data_sdk.gateways.vector import VectorGateway, VectorHit, VectorRecord

__all__ = [
    "CacheGateway",
    "EmbedGateway",
    "KnowledgeGateway",
    "KnowledgeHit",
    "LLMGateway",
    "LLMMessage",
    "LLMResult",
    "Params",
    "RawQueryGateway",
    "SearchGateway",
    "SearchHit",
    "ObjectStoreGateway",
    "StoredObject",
    "EventBusGateway",
    "NotifyGateway",
    "NotifyResult",
    "ScheduledTask",
    "SchedulerGateway",
    "AuthGateway",
    "AuthPrincipal",
    "RateLimitGateway",
    "SecurityGateway",
    "VectorGateway",
    "VectorHit",
    "VectorRecord",
]
