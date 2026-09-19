"""资产与跟踪类契约。

对应《职引-PRD-v2.0》§7.3 15 维报告 / §7.4 方向方案 / §7.5 行动计划 / §7.6 跟踪与成就。
字段结构对齐 PRD，第一期不追求索引与分区优化。
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from zhiyin_kernel.blackboard import ProfileField
from zhiyin_kernel.enums import DimensionEvidenceLevel, PlanRole


class Verdict(BaseModel):
    """报告综合结论。"""

    model_config = ConfigDict(extra="forbid")

    title: str
    summary: str


class Swot(BaseModel):
    """SWOT。每项不少于 2 条（FR-DIAG-002）。"""

    model_config = ConfigDict(extra="forbid")

    strength: list[str] = Field(default_factory=list)
    weakness: list[str] = Field(default_factory=list)
    opportunity: list[str] = Field(default_factory=list)
    risk: list[str] = Field(default_factory=list)


class ReportDimensionItem(BaseModel):
    """15 维中的单维。

    `tag` 原为自由字符串，实测模型产出 11 种措辞（已确认/待验证/未定义/缺失/
    待确认/部分匹配/无依据/严重不足/未知/低/未建立），既无法上色，也把
    "证据够不够"和"这一维好不好"两件事混在一句里。现收紧为**证据充分度**闭合枚举，
    让热力图有稳定的等级轴，并约束模型只能在这四档里选。
    """

    model_config = ConfigDict(extra="forbid")

    index: int
    name: str
    tag: DimensionEvidenceLevel = Field(
        description="证据充分度等级，只能取 confirmed/partial/pending/missing"
    )
    conclusion: str
    evidence: str = Field(description="证据引用，必须可溯源")


class ReportDimensionGroup(BaseModel):
    """15 维分组：自我画像 6 / 职业环境 5 / 决策与风险 4。"""

    model_config = ConfigDict(extra="forbid")

    group: Literal["SELF-PORTRAIT", "JOB-MARKET", "DECISION-RISK"]
    group_method: str = Field(description="该分组支撑的方法论")
    items: list[ReportDimensionItem] = Field(default_factory=list)


class GapClaim(BaseModel):
    """差距认领记录。诊断 → 决策的衔接点（FR-DIAG-004）。"""

    model_config = ConfigDict(extra="forbid")

    gap_id: str
    claimed_at: datetime


class Report(BaseModel):
    """15 维诊断报告。

    `profile_snapshot` 是**生成这一版报告时的画像快照**，不是活状态。
    为什么必须有它：报告是**版本化只读资产**（《前端页面设计》§4.4 第 245 行：
    "报告全文页读取资产版本"），而画像会继续变化。若报告页实时读当前画像，
    用户会看到"v1 报告里显示的是今天的画像"，两份东西对不上。
    旧报告该字段为空列表 → 报告页不生成画像章节，向后兼容、无需数据迁移。
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    user_id: str
    version: int
    generated_at: datetime
    verdict: Verdict
    swot: Swot
    dimensions: list[ReportDimensionGroup] = Field(default_factory=list)
    gap_claims: list[GapClaim] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list, description="事实来源，如学职平台/JD")
    methodologies: list[str] = Field(default_factory=list, description="本次使用的理论模型")
    profile_snapshot: list[ProfileField] = Field(
        default_factory=list,
        description="本版本生成时的画像快照（冻结，不随画像继续变化）",
    )


class PlanGap(BaseModel):
    """方案内的差距条目：要求 − 现状 = 差距 + 补齐建议。"""

    model_config = ConfigDict(extra="forbid")

    requirement: str
    current_state: str
    suggestion: str


class DirectionPlan(BaseModel):
    """方向方案。主攻/平行/保底三套，选择可撤回。"""

    model_config = ConfigDict(extra="forbid")

    id: str
    report_id: Optional[str] = Field(default=None, description="关联的诊断报告 id")
    role: PlanRole
    name: str
    target_desc: str = Field(description="目标描述")
    match_score: float = Field(description="匹配度，解释性分值，非严谨算法")
    gaps: list[PlanGap] = Field(default_factory=list)
    fit_reason: str = Field(description="契合依据")
    main_risk: str = Field(description="主要风险")
    selected: bool = False
    selected_at: Optional[datetime] = None
    revocable: bool = Field(default=True, description="可撤回，恒为 True")


class ActionTask(BaseModel):
    """行动任务。颗粒度要求"今天/本周勾得掉"。"""

    model_config = ConfigDict(extra="forbid")

    text: str
    due_date: Optional[datetime] = None
    done: bool = False
    done_at: Optional[datetime] = None


class ActionPhase(BaseModel):
    """行动阶段。"""

    model_config = ConfigDict(extra="forbid")

    name: str
    date_range: str
    tag: str = Field(default="", description="阶段标签，如秋招投递/笔试冲刺")
    tasks: list[ActionTask] = Field(default_factory=list)


class ActionPlan(BaseModel):
    """行动计划。"""

    model_config = ConfigDict(extra="forbid")

    id: str
    plan_id: Optional[str] = Field(default=None, description="关联的方向方案 id")
    phases: list[ActionPhase] = Field(default_factory=list)
    reminders_synced: bool = False
    exported_at: Optional[datetime] = None


class TrackEvent(BaseModel):
    """跟踪时间线事件。复盘产出的载体。"""

    model_config = ConfigDict(extra="forbid")

    id: str
    user_id: str
    type: Literal[
        "milestone_done", "reminder", "warning", "semester_review", "coach_message"
    ]
    title: str
    detail: str = ""
    occurred_at: Optional[datetime] = None
    due_at: Optional[datetime] = None
    related_task_id: Optional[str] = None
    related_stage: Optional[str] = None


class Achievement(BaseModel):
    """成就。只由行为日志驱动，防自嗨（FR-BLOCK-003）。"""

    model_config = ConfigDict(extra="forbid")

    id: str
    user_id: str
    badge_key: str
    unlocked: bool = False
    unlocked_at: Optional[datetime] = None
    driven_by_behavior_log_only: bool = Field(default=True)


class CalendarNode(BaseModel):
    """关键节点日历条目（FR-BLOCK-002）。

    放在 contracts 而不是业务层：它是**需要落库的数据形状**（key_calendar_node 表），
    基础设施层的表清单必须能指向契约。若留在业务层，persistence 就会反向引用业务
    模型，破坏单向依赖（§九 验收项 1）。规划师写入、教练读取的业务规则仍在业务层。
    """

    model_config = ConfigDict(extra="forbid")

    node_id: str
    user_id: str = ""
    title: str
    due_at: Optional[datetime] = None
    source: Literal["planner", "coach", "manual"] = "planner"
    related_task_text: str = ""
