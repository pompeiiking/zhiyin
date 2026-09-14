"""Application Facade 契约。

职责（R-API-004）：
- 编排业务层服务调用，组装 View DTO；
- 通过 Mapper 完成 business 模型 → api DTO 的转换，业务模型变更不外溢到前端；
- 不写业务规则，不直接访问数据库 / 模型 / 知识库。

装配方式：zhiyin-boot 在启动时调用 configure_facade(实现)，Controller 通过
get_facade() 获取。这样 Controller 不依赖任何具体实现，替换实现无需改接口层。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from fastapi import Request

from zhiyin_business.published import AssetType
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


class ApplicationFacade(ABC):
    """BFF 应用门面。"""

    # ---------- 身份 ----------

    @abstractmethod
    async def resolve_user_id(self, request: Request) -> str:
        """解析当前用户。第一期由 AuthGateway 返回本地演示用户。"""

    # ---------- 启动 ----------

    @abstractmethod
    def bootstrap(self, user_id: str) -> BootstrapView:
        """启动装配视图。"""

    # ---------- 对话 ----------

    @abstractmethod
    def list_sessions(self, user_id: str) -> SessionListView:
        """左栏会话列表。"""

    @abstractmethod
    async def enter_task(self, user_id: str, body: TaskEnterRequest) -> TaskSessionView:
        """进入任务：判定环节 → 选主理 → 建会话或续接。"""

    @abstractmethod
    async def send_message(
        self, user_id: str, body: MessageRequest
    ) -> ConversationTurnView:
        """处理一轮消息，返回最短结论 + 告知 + 引导 + 管线卡。"""

    # ---------- 工作台 ----------

    @abstractmethod
    def get_workspace(self, user_id: str) -> WorkspacePageView:
        """工作台聚合视图。"""

    # ---------- 资产 ----------

    @abstractmethod
    def list_asset_versions(
        self, user_id: str, asset_type: AssetType
    ) -> list[AssetVersionView]:
        """资产版本列表（含 diff 与依赖字段）。"""

    @abstractmethod
    def get_report_full_text(
        self, user_id: str, version: Optional[int] = None
    ) -> ReportFullTextView:
        """完整报告页正文。"""

    @abstractmethod
    async def export_asset(self, user_id: str, body: ExportRequest) -> ExportResultView:
        """导出资产（第一期占位）。"""


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
