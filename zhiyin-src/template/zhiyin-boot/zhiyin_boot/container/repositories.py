"""Repository 与动态资源装配表。

第一期的 Repository 全部是内存实现（进程重启即丢）；MySQL 实现在
`zhiyin_infrastructure/persistence/` 下待补。动态资源（功能开关 / 智能体 /
理论卡 / 产出契约 / 任务入口）读 `data/registry/*.json`。
"""

from __future__ import annotations

from typing import Any

from zhiyin_boot.settings import Settings


def build_repositories(settings: Settings) -> dict[str, Any]:
    """按配置装配 Repository；启用 MySQL 时七类能力必须整体切换。"""
    if settings.use_mysql:
        if not settings.database_url:
            raise ValueError("启用 MySQL Repository 时必须配置 ZHIYIN_DATABASE_URL")
        from zhiyin_infrastructure.mysql import DatabaseContext, build_repository_set

        context = DatabaseContext(settings.database_url, echo=settings.db_echo)
        return {
            **build_repository_set(
                context, registry_seed_dir=settings.local_registry_dir
            ),
            "_database_context": context,
        }

    from zhiyin_infrastructure.local.repository import (
        InMemoryAssetRepository,
        InMemoryBehaviorRepository,
        InMemoryConversationMemoryRepository,
        InMemoryProfileRepository,
        InMemoryTaskSessionRepository,
        InMemoryUserRepository,
        LocalJsonRegistryRepository,
    )

    return {
        "profiles": InMemoryProfileRepository(),
        "behaviors": InMemoryBehaviorRepository(),
        "memories": InMemoryConversationMemoryRepository(),
        "assets": InMemoryAssetRepository(),
        "sessions": InMemoryTaskSessionRepository(),
        "registry": LocalJsonRegistryRepository(settings.local_registry_dir),
        "users": InMemoryUserRepository(),
    }


def build_transactions(settings: Settings) -> Any:
    """事务管理器。未启用 MySQL 时返回 None（第一期按设计走内存实现）。"""
    if not (settings.use_mysql and settings.database_url):
        return None
    from zhiyin_infrastructure.persistence.database import (
        SqlAlchemyTransactionManager,
    )

    return SqlAlchemyTransactionManager(settings.database_url, echo=settings.db_echo)


def build_feature_flags(settings: Settings) -> Any:
    """功能开关。属于动态资源，读本地 JSON 而不是写死在 Settings 里。"""
    from zhiyin_infrastructure.local.feature_flag import LocalFeatureFlagStore

    return LocalFeatureFlagStore(settings.local_registry_dir)


__all__ = ["build_feature_flags", "build_repositories", "build_transactions"]
