"""资产与导出 DTO（FR-BLOCK-001）。

写操作 DTO 说明（FR-DIAG-004 / FR-DECIDE-003 / FR-ACT-004 / FR-BLOCK-002）
------------------------------------------------------------------------
这四个请求体是"报告之后产品就空转"的解药：此前用户只能在对话里读产出，
没有任何端点能把「我认领这条差距 / 我选这套方案 / 我做完这件事 / 把它放进日历」
落成真实数据，于是成就、跟踪时间线、方案选择状态永远为空。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from zhiyin_kernel.enums import AssetType, PlanRole


class AssetVersionView(BaseModel):
    """资产版本视图（R-API-005）。前端据此展示"v1→v2 的差异"。"""

    model_config = ConfigDict(extra="forbid")

    asset_type: AssetType
    asset_id: str
    version: int
    created_at: datetime
    depends_on_profile_keys: list[str] = Field(default_factory=list)
    diff_from_previous: Optional[str] = None


class ReportFullTextView(BaseModel):
    """完整报告页正文（只读资产视图，不承载实时对话）。"""

    model_config = ConfigDict(extra="forbid")

    report_id: str
    version: int
    generated_at: datetime
    toc: list[dict[str, str]] = Field(default_factory=list, description="左侧目录导航")
    sections: list[dict[str, Any]] = Field(
        default_factory=list, description="15 维全景 / 方案 / 行动计划 / 个人画像"
    )


class ExportRequest(BaseModel):
    """导出请求。"""

    model_config = ConfigDict(extra="forbid")

    asset_type: AssetType
    format: Literal["pdf", "docx"] = "pdf"


class ExportResultView(BaseModel):
    """导出结果。第一期 available 恒 False，仅预留入口。"""

    model_config = ConfigDict(extra="forbid")

    available: bool = False
    message: str = "第一期仅预留导出入口"
    object_key: Optional[str] = None


# ---------------------------------------------------------------------------
# 闭环写操作（FR-DIAG-004 / FR-DECIDE-003 / FR-ACT-004 / FR-BLOCK-002）
# ---------------------------------------------------------------------------


class GapClaimRequest(BaseModel):
    """认领一条差距。gap_id 取自报告全文的差距区块。"""

    model_config = ConfigDict(extra="forbid")

    gap_id: str


class GapClaimView(BaseModel):
    """认领结果。带全量已认领 id，前端可直接刷新认领清单，无需再拉一次报告。"""

    model_config = ConfigDict(extra="forbid")

    gap_id: str
    claimed_at: datetime
    claimed_gap_ids: list[str] = Field(default_factory=list)


class DecisionSelectionRequest(BaseModel):
    """选择一套方向方案（可撤回，重选同样走本接口）。"""

    model_config = ConfigDict(extra="forbid")

    plan_id: str


class DecisionSelectionView(BaseModel):
    """选择结果：选中的方案及其角色，前端据此高亮并允许撤回。"""

    model_config = ConfigDict(extra="forbid")

    plan_id: str
    role: PlanRole
    name: str
    match_score: float
    selected_at: Optional[datetime] = None


class TaskDoneRequest(BaseModel):
    """勾掉一条行动任务。task_id 取自行动计划的 `阶段名:任务文本`（或任务文本）。"""

    model_config = ConfigDict(extra="forbid")

    task_id: str


class TaskDoneView(BaseModel):
    """勾选结果：命中的那条任务及其所属阶段。"""

    model_config = ConfigDict(extra="forbid")

    plan_id: str
    task_id: str
    phase: str
    text: str
    done: bool
    done_at: Optional[datetime] = None
    done_total: int = Field(default=0, description="当前已完成任务数")
    task_total: int = Field(default=0, description="当前任务总数")


class CalendarNodeRequest(BaseModel):
    """把一个关键节点写进日历。"""

    model_config = ConfigDict(extra="forbid")

    title: str
    due_at: Optional[datetime] = None
    source: Literal["planner", "coach", "manual"] = "manual"
    related_task_text: str = ""


class CalendarNodeView(BaseModel):
    """日历节点视图。"""

    model_config = ConfigDict(extra="forbid")

    node_id: str
    title: str
    due_at: Optional[datetime] = None
    source: str
    related_task_text: str = ""

