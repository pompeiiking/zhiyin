"""Application Facade 实现（**骨架**，方法体未实现）。

落位：`api/facade/application.py` —— 接口/前端联调负责人。
依赖：业务层的服务 Port（只调不实现）+ `api/dto/mappers.py`。

为什么它决定前端能否并行开工
----------------------------
前端只需要这一个实现：它把业务模型翻成 `dto/` 的 View，前端就拿到稳定的 JSON 形状。
本文件未实现时，所有 `/app/*` 接口按约定返回 503（code 1007），前端连不上——
这也是当前 `--check` 里 `services.facade=not_wired` 的含义。

三条不越界的要求：
- 不写业务规则（规则在 `business/policies/`，调用在 `business/services/`）；
- 不直接访问 Repository / Gateway（只经业务服务）；
- 只做"编排调用 + 交给 Mapper"，字段映射全部在 `api/dto/mappers.py`；
  本文件里不应出现 `XxxView(...)` 的直接构造。

两个硬前置（构造时必须注入，否则 `/app/bootstrap` 无数据可返回）
---------------------------------------------------------------
- `IdentityService`：解析当前用户（api 拿不到 `AuthGateway`）；
- `RegistryService`：菜单 / 路由 / 任务入口 / 文案 / 开关（api 拿不到 `RegistryRepository`）。

两者都是"api 需要、契约却在 data_sdk"逼出来的业务侧出口，
判据与决策见 `business/ports/identity.py` 与 `business/ports/registry.py` 的模块 docstring。

装配：`zhiyin_boot.wire_application()` 在启动时调用
`configure_facade(DefaultApplicationFacade(...))`；未装配时 `get_facade()` 抛
`FacadeNotConfiguredError`，由 `create_app` 统一映射为 DEPENDENCY_UNAVAILABLE。
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
from zhiyin_api.dto.workspace import WorkspacePageView
from zhiyin_api.dto.track import TrackEventAck, TrackEventRequest
from zhiyin_api.facade.facade import ApplicationFacade
from zhiyin_business.ports.identity import IdentityService
from zhiyin_business.ports.registry import RegistryService
from zhiyin_kernel.enums import AssetType

_TODO = "TODO(骨架): ApplicationFacade 未实现"


class DefaultApplicationFacade(ApplicationFacade):
    """BFF 门面默认实现（骨架）。"""

    IMPLEMENTATION_STATUS = "skeleton"

    def __init__(self, *, identity: IdentityService, registry: RegistryService) -> None:
        """构造依赖由 boot 注入。

        身份解析走业务 Port：api 被禁止 import `zhiyin_data_sdk`，拿不到
        `AuthGateway`；由 `DefaultIdentityService` 把它包成业务抽象
        （决策见 `business/ports/identity.py` 的模块 docstring）。

        动态资源同理：菜单 / 路由 / 任务入口 / 文案 / 开关经
        `DefaultRegistryService` 取（`business/ports/registry.py`）。

        `resolve_user_id` 的职责边界：**只做 HTTP → 业务形状的翻译**
        （从请求里取 token），用户记录的补齐、游客会话、登录合并都在业务侧。
        """
        self._identity = identity
        self._registry = registry

    # ---------- 身份 ----------

    async def resolve_user_id(self, request: Request) -> str:
        raise NotImplementedError(
            f"{_TODO}：从 Request 取 token → IdentityService.current_user() → 返回 user_id"
        )

    # ---------- 启动 ----------

    def bootstrap(self, user_id: str) -> BootstrapView:
        raise NotImplementedError(
            f"{_TODO}：RegistryService 取数（菜单 / 路由 / 任务入口 / 文案 / "
            "横幅 / 信任块 / FAQ / 开关）→ mappers.bootstrap_view"
        )

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

    # ---------- 埋点 ----------

    async def track_event(
        self, user_id: str, body: TrackEventRequest
    ) -> TrackEventAck:
        raise NotImplementedError(
            f"{_TODO}：RegistryService 校验 frontend 事件 → 落库（口径待定）"
        )


__all__ = ["DefaultApplicationFacade"]
