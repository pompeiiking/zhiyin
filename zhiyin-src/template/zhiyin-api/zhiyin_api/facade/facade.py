"""Application Facade 契约。

职责（R-API-004）：
- 编排业务层服务调用，组装 View DTO；
- 转换一律交给 `zhiyin_api/dto/mappers.py`（业务模型 → api DTO），
  本层不内联字段映射，业务模型变更不外溢到前端；
- 不写业务规则，不直接访问数据库 / 模型 / 知识库。

取数通道（api 被禁止 import `zhiyin_data_sdk`，所以只有这两条业务侧出口）
------------------------------------------------------------------------
| 需要的东西 | 出口 |
| --- | --- |
| 我是谁（认证主体 → 本地用户记录） | `business/ports/identity.py::IdentityService` |
| 页面长什么样（菜单 / 路由 / 任务入口 / 文案 / 横幅 / 信任块 / FAQ / 开关） | `business/ports/registry.py::RegistryService` |

因此 Facade 的构造依赖至少包含这两个服务；`bootstrap()` 没有它们就无法返回任何内容。
其余能力（对话 / 工作台 / 资产）分别走 `Orchestrator` 与 `WorkspaceService` / `AssetService`。

装配方式：zhiyin-boot 在启动时调用 configure_facade(实现)，Controller 通过
get_facade() 获取。这样 Controller 不依赖任何具体实现，替换实现无需改接口层。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from fastapi import Request

from zhiyin_kernel.enums import AssetType
from zhiyin_api.dto.asset import (
    AssetVersionView,
    ExportRequest,
    ExportResultView,
    ReportFullTextView,
)
from zhiyin_api.dto.bootstrap import BootstrapView
from zhiyin_api.dto.conversation import (
    ConversationHistoryView,
    ConversationTurnView,
    MessageRequest,
    SessionListView,
    TaskEnterRequest,
    TaskSessionView,
)
from zhiyin_api.dto.workspace import WorkspacePageView
from zhiyin_api.dto.track import TrackEventAck, TrackEventRequest


class ApplicationFacade(ABC):
    """BFF 应用门面。"""

    # ---------- 身份 ----------

    @abstractmethod
    async def resolve_user_id(self, request: Request) -> str:
        """解析当前用户。

        实现只做 HTTP → 业务形状的翻译：从请求里取 token，交给业务侧的
        `IdentityService.current_user()`，返回其 `user_id`。**不要**在这里访问
        用户表或鉴权网关（api 层被禁止 import data_sdk）。
        """

    # ---------- 启动 ----------

    @abstractmethod
    async def bootstrap(self, user_id: str) -> BootstrapView:
        """启动装配视图。"""

    # ---------- 对话 ----------

    @abstractmethod
    async def list_sessions(self, user_id: str) -> SessionListView:
        """左栏会话列表。"""

    @abstractmethod
    async def enter_task(self, user_id: str, body: TaskEnterRequest) -> TaskSessionView:
        """进入任务：判定环节 → 选主理 → 建会话或续接。"""

    @abstractmethod
    async def send_message(
        self, user_id: str, body: MessageRequest
    ) -> ConversationTurnView:
        """处理一轮消息，返回最短结论 + 告知 + 引导 + 管线卡。"""

    @abstractmethod
    async def read_conversation_history(
        self, user_id: str, task_id: str
    ) -> ConversationHistoryView:
        """读取某任务会话的既成事实：全部消息 + 所处环节 + 管线卡。

        前端刷新页面或切换会话时用它恢复对话流与环节进度。未知会话或不属于
        该用户的会话必须显式失败（由 Orchestrator 抛 LookupError/PermissionError
        统一映射），**不得返回空历史冒充成功**。
        """

    # ---------- 工作台 ----------

    @abstractmethod
    async def get_workspace(self, user_id: str) -> WorkspacePageView:
        """工作台聚合视图。"""

    # ---------- 资产 ----------

    @abstractmethod
    async def list_asset_versions(
        self, user_id: str, asset_type: AssetType
    ) -> list[AssetVersionView]:
        """资产版本列表（含 diff 与依赖字段）。"""

    @abstractmethod
    async def get_report_full_text(
        self, user_id: str, version: Optional[int] = None
    ) -> ReportFullTextView:
        """完整报告页正文。"""

    @abstractmethod
    async def export_asset(self, user_id: str, body: ExportRequest) -> ExportResultView:
        """导出资产（第一期占位）。"""

    # ---------- 埋点 ----------

    @abstractmethod
    async def track_event(
        self, user_id: str, body: TrackEventRequest
    ) -> TrackEventAck:
        """接收前端埋点上报。

        实现要求：先经 `RegistryService.list_track_events()` 校验事件属于
        `channel=frontend`，再决定落库口径（体验型事件存储是后续待办）。
        本层不写事件归属判断，只编排。
        """


# ---------- 装配与获取 ----------

_facade: Optional[ApplicationFacade] = None


class FacadeNotConfiguredError(RuntimeError):
    """Facade 未装配。

    第一期业务服务尚未实现，接口层会得到本异常；`create_app` 会把它统一映射为
    ErrorCode.DEPENDENCY_UNAVAILABLE（§6.2：不中断核心调用链，也不静默吞掉）。
    """


def configure_facade(facade: ApplicationFacade) -> None:
    """由 zhiyin-boot 在启动时调用。"""
    global _facade
    _facade = facade


def get_facade() -> ApplicationFacade:
    """获取已装配的 Facade。未装配时抛出可识别的异常，避免静默返回空实现。"""
    if _facade is None:
        raise FacadeNotConfiguredError(
            "ApplicationFacade 尚未装配：请在 zhiyin-boot 启动时调用 configure_facade()"
        )
    return _facade


def reset_facade() -> None:
    """清空已装配的 Facade。供测试隔离使用，业务代码不应调用。

    与 `zhiyin_api.runtime.reset_runtime()` 同源：装配是全局注入，测试之间必须
    显式还原，否则"某个用例 wire 过一次"会让后面的用例看到别人的装配状态。
    `tests/conftest.py` 的自动夹具对两者统一还原。
    """
    global _facade
    _facade = None
