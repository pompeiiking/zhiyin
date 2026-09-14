"""Mock Facade 外壳（**骨架**，方法体未实现）。

落位：`api/facade/mock.py` —— 接口/前端联调负责人。
用途：决策 15 = A——Facade 未实现时，前端用 `ZHIYIN_MOCK=1` 走真实路由联调，
数据全部来自动态资源（任务入口 / 菜单 / 文案 / 开关等），并可作为
FR-BLOCK-005 自动演示的数据源。

三条与真实 Facade 相同的边界：
- 不写业务规则，不做字段映射（字段口径只在 `dto/mappers.py`）；
- 不直接访问 Repository / Gateway，只面对业务 Port；
- 自报 `IMPLEMENTATION_STATUS = "skeleton"`，装配报告会如实标注。

装配：`zhiyin_boot/container/__init__.py` 在 `settings.mock_facade=True` 时
构造本类并注入。真实 Facade 完成前，本类是"让前端能跑起来"的最小替身。
"""

from __future__ import annotations

from typing import Optional

from fastapi import Request

from zhiyin_api.dto.asset import (
    AssetVersionView,
    ExportRequest,
    ExportResultView,
    ReportFullTextView,
)
from zhiyin_api.dto.bootstrap import BootstrapView
from zhiyin_api.dto.conversation import (
    ConversationTurnView,
    MessageRequest,
    SessionListView,
    TaskEnterRequest,
    TaskSessionView,
)
from zhiyin_api.dto.track import TrackEventAck, TrackEventRequest
from zhiyin_api.dto.workspace import WorkspacePageView
from zhiyin_api.facade.facade import ApplicationFacade
from zhiyin_business.ports.identity import IdentityService
from zhiyin_business.ports.registry import RegistryService
from zhiyin_kernel.enums import AssetType

_TODO = "TODO(骨架): MockApplicationFacade 未实现"


class MockApplicationFacade(ApplicationFacade):
    """BFF 门面的 Mock 替身（骨架）。"""

    IMPLEMENTATION_STATUS = "skeleton"

    def __init__(self, *, identity: IdentityService, registry: RegistryService) -> None:
        self._identity = identity
        self._registry = registry

    async def resolve_user_id(self, request: Request) -> str:
        raise NotImplementedError(f"{_TODO}：返回固定演示用户")

    def bootstrap(self, user_id: str) -> BootstrapView:
        raise NotImplementedError(f"{_TODO}：读 RegistryService → mappers.bootstrap_view")

    def list_sessions(self, user_id: str) -> SessionListView:
        raise NotImplementedError(f"{_TODO}：返回静态演示会话")

    async def enter_task(self, user_id: str, body: TaskEnterRequest) -> TaskSessionView:
        raise NotImplementedError(f"{_TODO}：返回演示会话")

    async def send_message(
        self, user_id: str, body: MessageRequest
    ) -> ConversationTurnView:
        raise NotImplementedError(f"{_TODO}：按产出契约合成一轮回复")

    def get_workspace(self, user_id: str) -> WorkspacePageView:
        raise NotImplementedError(f"{_TODO}：返回静态工作台")

    def list_asset_versions(
        self, user_id: str, asset_type: AssetType
    ) -> list[AssetVersionView]:
        raise NotImplementedError(f"{_TODO}：返回静态版本列表")

    def get_report_full_text(
        self, user_id: str, version: Optional[int] = None
    ) -> ReportFullTextView:
        raise NotImplementedError(f"{_TODO}：返回演示报告全文")

    async def export_asset(self, user_id: str, body: ExportRequest) -> ExportResultView:
        raise NotImplementedError(f"{_TODO}：返回占位导出结果")

    async def track_event(
        self, user_id: str, body: TrackEventRequest
    ) -> TrackEventAck:
        raise NotImplementedError(f"{_TODO}：确认接收，演示数据不落库")


__all__ = ["MockApplicationFacade"]
