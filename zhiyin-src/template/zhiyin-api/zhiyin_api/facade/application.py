"""Application Facade 实现（**骨架**，方法体未实现）。

落位：`api/facade/application.py` —— 接口/前端联调负责人。
依赖：业务层的 8 个服务 Port（只调不实现）+ DTO Mapper。

为什么它决定前端能否并行开工
----------------------------
前端只需要这一个实现：它把业务模型翻成 `dto/` 的 View，前端就拿到稳定的 JSON 形状。
本文件未实现时，所有 `/app/*` 接口按约定返回 503（code 1007），前端连不上——
这也是当前 `--check` 里 `services.facade=not_wired` 的含义。

三条不越界的要求：
- 不写业务规则（规则在 `business/policies/`，调用在 `business/services/`）；
- 不直接访问 Repository / Gateway（只经业务服务）；
- 只做"编排调用 + 模型 → DTO 转换"，转换逻辑集中在各 `dto/*.py` 的 Mapper。

装配：`zhiyin_boot.wire_application()` 在启动时调用
`configure_facade(DefaultApplicationFacade(...))`；未装配时 `get_facade()` 抛
`FacadeNotConfiguredError`，由 `create_app` 统一映射为 DEPENDENCY_UNAVAILABLE。
"""

from __future__ import annotations

from typing import Any, Optional

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
from zhiyin_api.dto.workspace import WorkspacePageView
from zhiyin_api.facade.facade import ApplicationFacade
from zhiyin_kernel.enums import AssetType

_TODO = "TODO(骨架): ApplicationFacade 未实现"


class DefaultApplicationFacade(ApplicationFacade):
    """BFF 门面默认实现（骨架）。"""

    IMPLEMENTATION_STATUS = "skeleton"

    def __init__(self, *, auth: Any) -> None:
        """构造依赖由 boot 注入。

        `auth` 这里**故意不做类型标注**：身份解析的契约是
        `zhiyin_data_sdk.gateways.security.AuthGateway`，而 api 层被
        `tests/test_architecture.py::test_api_does_not_touch_data_sdk` 禁止
        import data_sdk。在没有业务侧身份 Port 之前，只能由 boot 注入未类型化的对象。

        **待拍板**（这是外壳阶段就该定的事，不是实现细节）：
        要么为它新增业务侧 Port（如 `business/ports/identity.py::IdentityService`，
        由 business 包装 AuthGateway），api 只面对业务 Port；要么明确允许 api
        直连 `AuthGateway` 契约并同步修改依赖矩阵。二选一之前不要在这里写实现。
        """
        self._auth = auth

    # ---------- 身份 ----------

    async def resolve_user_id(self, request: Request) -> str:
        raise NotImplementedError(f"{_TODO}：经 AuthGateway 解析当前用户")

    # ---------- 启动 ----------

    def bootstrap(self, user_id: str) -> BootstrapView:
        raise NotImplementedError(f"{_TODO}：菜单 / 路由 / 任务入口 / 文案 / 功能开关")

    # ---------- 对话 ----------

    def list_sessions(self, user_id: str) -> SessionListView:
        raise NotImplementedError(f"{_TODO}：左栏会话列表")

    async def enter_task(self, user_id: str, body: TaskEnterRequest) -> TaskSessionView:
        raise NotImplementedError(f"{_TODO}：判环节 → 选主理 → 建会话或续接")

    async def send_message(
        self, user_id: str, body: MessageRequest
    ) -> ConversationTurnView:
        raise NotImplementedError(f"{_TODO}：一轮消息 → 结论 + 告知 + 引导 + 管线卡")

    # ---------- 工作台 ----------

    def get_workspace(self, user_id: str) -> WorkspacePageView:
        raise NotImplementedError(f"{_TODO}：工作台聚合视图")

    # ---------- 资产 ----------

    def list_asset_versions(
        self, user_id: str, asset_type: AssetType
    ) -> list[AssetVersionView]:
        raise NotImplementedError(f"{_TODO}：资产版本列表（含 diff 与依赖字段）")

    def get_report_full_text(
        self, user_id: str, version: Optional[int] = None
    ) -> ReportFullTextView:
        raise NotImplementedError(f"{_TODO}：完整报告页正文（只读，不重新生成）")

    async def export_asset(self, user_id: str, body: ExportRequest) -> ExportResultView:
        raise NotImplementedError(f"{_TODO}：导出（第一期占位）")


__all__ = ["DefaultApplicationFacade"]
