"""第一期默认实现（Local / Mock / Noop）。

目的：让"链贯通"这一步不依赖任何外部服务。zhiyin-boot 默认装配本包实现，
后续逐个替换为 pami / MySQL 版本，上层代码零改动。
"""

__all__ = [
    "auth",
    "cache",
    "embedding",
    "feature_flag",
    "knowledge",
    "llm",
    "messaging",
    "object_store",
    "repository",
    "security",
    "vector_store",
]
