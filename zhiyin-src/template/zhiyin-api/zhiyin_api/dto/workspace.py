"""智能工作台 DTO（FR-WB，按 ①-⑤ 分层聚合）。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from zhiyin_kernel.enums import LoopStage


class ProfilePanelView(BaseModel):
    """① 画像状态：字段覆盖度 / 置信度 / 缺口 / 更新时间。"""

    model_config = ConfigDict(extra="forbid")

    coverage: float = Field(default=0.0, ge=0.0, le=1.0, description="字段覆盖度")
    overall_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    fields: list[dict[str, Any]] = Field(default_factory=list)
    gaps: list[dict[str, Any]] = Field(default_factory=list)
    updated_at: Optional[datetime] = None


class StagePanelView(BaseModel):
    """②-⑤ 的节点卡。三态：当前评价 / 理论模型 / 历史 diff。"""

    model_config = ConfigDict(extra="forbid")

    stage: LoopStage
    title: str
    evaluation: str = ""
    theory_models: list[dict[str, Any]] = Field(default_factory=list)
    version: Optional[int] = None
    diff: Optional[str] = Field(default=None, description="差异说明，如「因更新了 X，v1→v2 的变化」")
    updated_at: Optional[datetime] = None


class DependencyEdgeView(BaseModel):
    """依赖可视化（FR-WB-005 简版）。"""

    model_config = ConfigDict(extra="forbid")

    from_asset: str
    to_asset: str
    via_profile_keys: list[str] = Field(default_factory=list)


class WorkspacePageView(BaseModel):
    """工作台聚合视图。"""

    model_config = ConfigDict(extra="forbid")

    profile_panel: ProfilePanelView = Field(default_factory=ProfilePanelView)
    report_panel: Optional[StagePanelView] = Field(default=None, description="② 诊断与报告")
    plan_panel: Optional[StagePanelView] = Field(default=None, description="③ 方案")
    action_panel: Optional[StagePanelView] = Field(default=None, description="④ 计划与日历")
    calendar_nodes: list[dict[str, Any]] = Field(
        default_factory=list,
        description=(
            "④ 关键节点日历（FR-BLOCK-002）：节点 id / 标题 / 截止时间 / 来源 / 关联任务。"
            "此前工作台只有写端点、没有读路径，报告页写入后工作台永远空态。"
        ),
    )
    review_panel: Optional[StagePanelView] = Field(default=None, description="⑤ 跟踪与预警")
    coach_messages: list[dict[str, Any]] = Field(
        default_factory=list, description="教练消息汇总（FR-WB-006）"
    )
    dependencies: list[DependencyEdgeView] = Field(default_factory=list)
    blocks: dict[str, Any] = Field(
        default_factory=dict, description="功能块入口与静态数据（FR-WB-007）"
    )
    axis_a_stage: Optional[str] = Field(
        default=None, description="轴 A 阶段过滤依据（FR-WB-004）"
    )
