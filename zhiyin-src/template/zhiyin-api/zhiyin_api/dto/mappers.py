"""DTO Mapper（**骨架**，方法体未实现）：业务形状 → 前端视图。

落位：`api/dto/mappers.py` —— 接口/前端联调负责人。

为什么单独一层
--------------
《分层详细设计》§2.2 规定 BFF 的转换动作由 "DTO Mapper" 承担，而
`api/facade/application.py` 只负责"编排调用 + 交给 Mapper"。这样切开的收益是：

- **前端字段口径只有一个地方**：改字段改 Mapper，不散落在 Facade 的每个方法体里；
- **Facade 与 DTO 可以并行**：前端先拿 `dto/` 的 View 形状开工，
  Mapper 实现完再接通数据；
- **契约可测**：Mapper 是纯函数（无 IO、无状态），可以脱离服务直接单测。

规则
----
- 只做形状翻译：`business 读模型 / Port 返回值 → dto View`；
- **不做取数**（不调服务）、**不写业务规则**（不判断该不该展示、不拼结论）；
- 不解析文案：文案一律来自 `copy_bundle`（动态资源），不要在这里拼中文。

字段来源（照此实现，不要另找数据源）
------------------------------------
- `BootstrapView` ← `RegistryService`（菜单 / 路由 / 任务入口 / 文案 / 横幅 / 信任块 /
  FAQ / 功能开关）+ `IdentityService`（身份区）
- `SessionListView` / `TaskSessionView` ← `WorkspaceService.list_sessions_summary`
  与 `TaskSession`（左栏按"任务/环节"命名，不按 agent 名排布）
- `ConversationTurnView` ← `Orchestrator.handle_message` 的 `TurnResult`
  （最短结论 + 显式告知 + 行为引导 + 管线卡）
- `WorkspacePageView` ← `WorkspaceService.build_view` 的 `WorkspaceView`
- `AssetVersionView` / `ReportFullTextView` / `ExportResultView` ←
  `AssetService` / `FunctionService` 的返回值

注意 `TurnResult.disclosure` 是**可空**的：只有"换主理 / 换理论 / 结论变化"时才填。
Mapper 必须把 None 原样透传成 `None`（前端据此决定是否渲染告知行），
**不要**用空字符串或默认文案顶替——那会让"没有告知"和"告知了但是空的"无法区分。
"""

from __future__ import annotations

from typing import Optional, Sequence

from zhiyin_api.dto.asset import (
    AssetVersionView,
    ExportResultView,
    ReportFullTextView,
)
from zhiyin_api.dto.bootstrap import BootstrapView
from zhiyin_api.dto.conversation import (
    ConversationTurnView,
    PipelineCardView,
    SessionListView,
    TaskSessionView,
)
from zhiyin_api.dto.workspace import WorkspacePageView
from zhiyin_business.ports.function import ExportResult
from zhiyin_business.ports.loop import LoopResult
from zhiyin_business.ports.orchestrator import TurnResult
from zhiyin_business.ports.workspace import WorkspaceView
from zhiyin_kernel.assets import Report
from zhiyin_kernel.blackboard import AssetVersion, TaskSession
from zhiyin_kernel.dynamic_content import (
    BannerSpec,
    FaqSpec,
    MenuSpec,
    RouteSpec,
    TrustBlockSpec,
)
from zhiyin_kernel.identity import UserAccount
from zhiyin_kernel.registry import AgentDescriptor, TaskEntrySpec

_TODO = "TODO(骨架): Mapper 未实现"


# ---------------------------------------------------------------------------
# 启动装配（app_controller → /app/bootstrap）
# ---------------------------------------------------------------------------


def bootstrap_view(
    *,
    copy_bundle: dict[str, str],
    menus: Sequence[MenuSpec],
    routes: Sequence[RouteSpec],
    task_entries: Sequence[TaskEntrySpec],
    agents: dict[str, AgentDescriptor],
    trust_blocks: Sequence[TrustBlockSpec],
    banners: Sequence[BannerSpec],
    faqs: Sequence[FaqSpec],
    feature_flags: dict[str, bool],
    identity: Optional[UserAccount] = None,
) -> BootstrapView:
    """拼首页启动视图。

    口径：
    - `app_name` 取 `copy_bundle["app.name"]`，取不到就留空字符串——**不要回落硬编码**，
      空值会让"文案包缺了"在联调时立刻可见；
    - 任务入口的 `lead_agent_name` 由 `agents[lead_agent].name` 解析，取不到时为 None
      （前端回落显示 agent_id，不静默编名字）；
    - 身份区为 `None`（游客）时 identity 留空 dict。
    """
    raise NotImplementedError(f"{_TODO}：组装 BootstrapView")


# ---------------------------------------------------------------------------
# 对话页（conversation_controller）
# ---------------------------------------------------------------------------


def task_session_view(
    session: TaskSession,
    *,
    task_name: str,
    lead_agent_name: str = "",
    progress: float = 0.0,
) -> TaskSessionView:
    """左栏会话项。`task_name` 取自动态任务入口文案，不按 agent 名排布。"""
    raise NotImplementedError(f"{_TODO}：TaskSession → TaskSessionView")


def session_list_view(
    sessions: Sequence[TaskSessionView], *, current_task_id: Optional[str] = None
) -> SessionListView:
    """左栏会话列表。"""
    raise NotImplementedError(f"{_TODO}：组装 SessionListView")


def conversation_turn_view(turn: TurnResult) -> ConversationTurnView:
    """一轮回复：最短结论 + 显式告知 + 行为引导 + 管线卡。"""
    raise NotImplementedError(f"{_TODO}：TurnResult → ConversationTurnView")


def pipeline_cards(
    session: TaskSession, asset_versions: Sequence[AssetVersion]
) -> list[PipelineCardView]:
    """右栏 ①-⑤ 管线卡（三态：当前产出 / 理论模型 / 评价状态）。"""
    raise NotImplementedError(f"{_TODO}：组装 PipelineCardView 列表")


def loop_stage_view(result: LoopResult) -> dict:
    """单个环节的产出摘要（供管线卡与工作台共用，避免两处各写一遍摘要口径）。"""
    raise NotImplementedError(f"{_TODO}：LoopResult → 产出摘要")


# ---------------------------------------------------------------------------
# 工作台（workspace_controller）
# ---------------------------------------------------------------------------


def workspace_page_view(view: WorkspaceView) -> WorkspacePageView:
    """工作台 ①-⑤ 聚合视图。"""
    raise NotImplementedError(f"{_TODO}：WorkspaceView → WorkspacePageView")


# ---------------------------------------------------------------------------
# 资产（asset_controller）
# ---------------------------------------------------------------------------


def asset_version_view(
    version: AssetVersion, *, previous: Optional[AssetVersion] = None
) -> AssetVersionView:
    """资产版本视图。`diff_from_previous` 由两版内容差异生成，不整篇重排。"""
    raise NotImplementedError(f"{_TODO}：AssetVersion → AssetVersionView")


def report_full_text_view(report: Report) -> ReportFullTextView:
    """完整报告页正文（只读资产版本，不重新生成）。"""
    raise NotImplementedError(f"{_TODO}：Report → ReportFullTextView")


def export_result_view(result: ExportResult) -> ExportResultView:
    """导出结果。第一期 `available` 恒 False（占位）。"""
    raise NotImplementedError(f"{_TODO}：ExportResult → ExportResultView")


__all__ = [
    "asset_version_view",
    "bootstrap_view",
    "conversation_turn_view",
    "export_result_view",
    "loop_stage_view",
    "pipeline_cards",
    "report_full_text_view",
    "session_list_view",
    "task_session_view",
    "workspace_page_view",
]
