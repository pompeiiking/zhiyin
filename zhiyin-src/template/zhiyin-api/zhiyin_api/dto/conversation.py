"""核心对话页 DTO（FR-CONV，三栏框架）。

- 左栏：会话管理（TaskSessionView / SessionListView）
- 中栏：对话 + 行为引导（ConversationMessageView / ConversationTurnView）
- 右栏：微循环管线卡三态（PipelineCardView）

长内容不进对话流：对话消息只说最短结论，全文走右栏卡与工作台资产。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from zhiyin_kernel.enums import LoopStage, TaskStatus


class TaskEnterRequest(BaseModel):
    """进入任务（FR-HOME-002）。task_code 取自 bootstrap 的任务入口。"""

    model_config = ConfigDict(extra="forbid")

    task_code: str


class MessageRequest(BaseModel):
    """一轮用户输入。支持会话续接（R-API-003）。"""

    model_config = ConfigDict(extra="forbid")

    task_id: str
    message: str
    client_msg_id: Optional[str] = Field(default=None, description="前端幂等键")


class ConversationMessageView(BaseModel):
    """对话气泡。"""

    model_config = ConfigDict(extra="forbid")

    role: Literal["agent", "user", "system"]
    text: str
    agent_id: Optional[str] = None
    agent_name: Optional[str] = None
    theory_refs: list[dict[str, Any]] = Field(
        default_factory=list, description="可点开的理论标签"
    )
    created_at: Optional[datetime] = None


class PipelineCardView(BaseModel):
    """右栏管线卡（①-⑤ 每环节一卡）。

    三态：当前产出 / 可展开理论模型 / 可展开评价状态。
    """

    model_config = ConfigDict(extra="forbid")

    stage: LoopStage
    title: str
    active: bool = Field(default=False, description="是否为当前环节，前端高亮")
    status: Literal["empty", "in_progress", "done"] = "empty"
    current_output: Optional[dict[str, Any]] = Field(
        default=None, description="态①：当前产出摘要"
    )
    theory_models: list[dict[str, Any]] = Field(
        default_factory=list, description="态②：可展开的理论模型"
    )
    evaluation: Optional[dict[str, Any]] = Field(
        default=None, description="态③：可展开的评价状态"
    )


class ConversationTurnView(BaseModel):
    """一轮回复的完整视图。

    对应架构文档 §5 的调用链返回：最短结论 + 显式告知 + 行为引导 + 管线卡。
    """

    model_config = ConfigDict(extra="forbid")

    task_id: str
    stage: LoopStage
    badge: dict[str, Any] = Field(
        default_factory=dict, description="顶栏主理徽章：agent_id/name/依据"
    )
    messages: list[ConversationMessageView] = Field(default_factory=list)
    disclosure: Optional[dict[str, Any]] = Field(
        default=None, description="换主理/换理论/结论变化的显式告知行"
    )
    guide: dict[str, Any] = Field(
        default_factory=dict, description="行为引导：question/options/task/reminder 四选一"
    )
    pipeline_cards: list[PipelineCardView] = Field(default_factory=list)
    changed_assets: list[dict[str, Any]] = Field(
        default_factory=list, description="本轮变化的资产版本，用于工作台刷新"
    )


class ConversationHistoryView(BaseModel):
    """某任务会话的既成事实：按时间正序的全部消息 + 所处环节 + 管线卡。

    与 `ConversationTurnView` 的分工：一轮回复回答"刚刚发生了什么"，
    历史回答"这个会话到现在为止是什么样"。前端刷新或切换会话时据此恢复
    对话流与环节进度，而不是把气泡清空后显示空态。
    """

    model_config = ConfigDict(extra="forbid")

    task_id: str
    stage: LoopStage
    stage_label: str = Field(description="环节中文名，左栏与右栏高亮共用同一口径")
    badge: dict[str, Any] = Field(
        default_factory=dict, description="当前主理徽章：agent_id/name/role_summary"
    )
    messages: list[ConversationMessageView] = Field(default_factory=list)
    pipeline_cards: list[PipelineCardView] = Field(default_factory=list)


class TaskSessionView(BaseModel):
    """左栏会话项。按"任务/环节"命名，不按 agent 名排布（FR-CONV-003）。"""

    model_config = ConfigDict(extra="forbid")

    task_id: str
    task_name: str
    stage: LoopStage
    stage_label: str = Field(description="环节中文名，用于左栏命名")
    lead_agent_name: str = ""
    status: TaskStatus = TaskStatus.ACTIVE
    progress: float = Field(default=0.0, ge=0.0, le=1.0, description="闭环进度")
    last_active_at: Optional[datetime] = None


class SessionListView(BaseModel):
    """左栏会话列表。"""

    model_config = ConfigDict(extra="forbid")

    sessions: list[TaskSessionView] = Field(default_factory=list)
    current_task_id: Optional[str] = None
