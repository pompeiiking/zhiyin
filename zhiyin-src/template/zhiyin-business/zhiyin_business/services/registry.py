"""动态资源读侧服务实现（**骨架**，方法体未实现）。

落位：`business/services/registry.py` —— 业务编排负责人。
依赖：`RegistryRepository`（内容型动态资源）+ `FeatureFlagGateway`（配置型开关）。

它是 BFF 的**硬前置**之一：`/app/bootstrap` 拿不到菜单 / 路由 / 任务入口 / 文案 /
开关，前端连首页都渲染不出来。因此本服务与 `DefaultIdentityService` 一起，
构成"Facade 一装配就会被调用"的两个依赖。

三条不越界的要求：
- **不组装页面视图**：返回内核形状，拼 `BootstrapView` 是 `api/dto/mappers.py` 的事；
- **不写业务判断**：任务入口 → 环节的路由判定在 `policies/routing.py`，
  本服务只做"按 key 取出来"；
- **不缓存**：缓存是第二期的事（§5.5 读侧允许缓存），现在加等于引入一个
  没有失效策略的缓存。

实现方只要填方法体；方法体里通常是一行转发（`await self._registry.xxx()`），
上下线与排序口径由 Repository 统一负责（见 `RegistryRepository` 的 docstring），
**不要在这里再写一遍 status 过滤与 sort**。
"""

from __future__ import annotations

from typing import Optional

from zhiyin_business.ports.registry import RegistryService
from zhiyin_data_sdk.gateways.feature_flag import FeatureFlagGateway
from zhiyin_data_sdk.repositories import RegistryRepository
from zhiyin_kernel.dynamic_content import (
    BannerSpec,
    FaqSpec,
    MenuSpec,
    RouteSpec,
    TrustBlockSpec,
)
from zhiyin_kernel.registry import AgentDescriptor, TaskEntrySpec
from zhiyin_kernel.registry import TrackEventSpec

_TODO = "TODO(骨架): RegistryService 未实现"


class DefaultRegistryService(RegistryService):
    """动态资源读侧服务默认实现（骨架）。"""

    IMPLEMENTATION_STATUS = "skeleton"

    def __init__(
        self,
        registry: RegistryRepository,
        feature_flags: FeatureFlagGateway,
    ) -> None:
        self._registry = registry
        self._feature_flags = feature_flags

    async def list_task_entries(self) -> list[TaskEntrySpec]:
        raise NotImplementedError(f"{_TODO}：转发 RegistryRepository.list_task_entries")

    async def get_agent(self, agent_id: str) -> Optional[AgentDescriptor]:
        raise NotImplementedError(f"{_TODO}：转发 RegistryRepository.get_agent")

    async def list_menus(self) -> list[MenuSpec]:
        raise NotImplementedError(f"{_TODO}：转发 RegistryRepository.list_menus")

    async def list_routes(self) -> list[RouteSpec]:
        raise NotImplementedError(f"{_TODO}：转发 RegistryRepository.list_routes")

    async def get_copy_bundle(self, bundle: str = "zh-CN") -> dict[str, str]:
        raise NotImplementedError(f"{_TODO}：转发 RegistryRepository.get_copy_bundle")

    async def list_banners(self) -> list[BannerSpec]:
        raise NotImplementedError(f"{_TODO}：转发 RegistryRepository.list_banners")

    async def list_trust_blocks(self) -> list[TrustBlockSpec]:
        raise NotImplementedError(f"{_TODO}：转发 RegistryRepository.list_trust_blocks")

    async def list_faqs(self) -> list[FaqSpec]:
        raise NotImplementedError(f"{_TODO}：转发 RegistryRepository.list_faqs")

    async def list_track_events(self) -> list[TrackEventSpec]:
        raise NotImplementedError(f"{_TODO}：转发 RegistryRepository.list_track_events")

    async def feature_flags(self) -> dict[str, bool]:
        raise NotImplementedError(f"{_TODO}：转发 FeatureFlagGateway.all")


__all__ = ["DefaultRegistryService"]
