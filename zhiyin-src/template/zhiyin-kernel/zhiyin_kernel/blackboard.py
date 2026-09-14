"""黑板四件套契约。

黑板书 = 画像（活状态）+ 行为日志 + 会话记忆 + 资产版本影响面。
对应数据库表：profile_field / profile_gap / behavior_log / conversation_memory
/ asset_version / task_session。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from zhiyin_kernel.enums import (
    AssetType,
    BehaviorEventType,
    LoopStage,
    ProfileSource,
    TaskStatus,
)


class ProfileField(BaseModel):
    """画像字段 · 活状态的最小单位。"""

    model_config = ConfigDict(extra="forbid")

    key: str = Field(description="字段键，如 major / skills / interest")
    value: Any = Field(description="字段值，结构由画像 schema 决定")
    confidence: float = Field(ge=0.0, le=1.0, description="置信度 0-1")
    source: ProfileSource = Field(description="来源")
    updated_at: datetime = Field(description="更新时间")
    evidence: list[str] = Field(default_factory=list, description="证据来源引用")


class ProfileGap(BaseModel):
    """画像缺口。用于采集追问与工作台展示。"""

    model_config = ConfigDict(extra="forbid")

    key: str = Field(description="缺口字段键")
    reason: str = Field(description="为什么算缺口")
    suggested_next_action: str = Field(description="建议的下一步采集动作")


class Profile(BaseModel):
    """个人画像（活状态）。不因首次建档结束而冻结。"""

    model_config = ConfigDict(extra="forbid")

    id: str
    user_id: str
    version: int = Field(default=1, description="画像整体版本")
    updated_at: datetime
    fields: list[ProfileField] = Field(default_factory=list)
    gaps: list[ProfileGap] = Field(default_factory=list)


class BehaviorLog(BaseModel):
    """行为日志。北极星指标的唯一事实来源。"""

    model_config = ConfigDict(extra="forbid")

    id: str
    user_id: str
    event_type: BehaviorEventType
    occurred_at: datetime
    payload: dict[str, Any] = Field(default_factory=dict)
    related_asset_ids: list[str] = Field(default_factory=list)


class ConversationMemory(BaseModel):
    """会话记忆 · 按任务会话维护摘要，用于跨会话续接。"""

    model_config = ConfigDict(extra="forbid")

    id: str
    user_id: str
    task_id: Optional[str] = Field(default=None, description="为空表示无归属任务的自由会话")
    loop_stage: LoopStage
    lead_agent: str = Field(description="该会话当前主理智能体的 agent_id")
    summary: str = Field(default="", description="会话摘要")
    last_active_at: datetime


class AssetVersion(BaseModel):
    """资产版本与影响面。

    depends_on_profile_keys 是影响面传播的唯一依据（FR-ORCH-004）：
    画像字段更新后，只重算命中的资产，版本 +1。
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    user_id: str
    asset_type: AssetType
    version: int = Field(description="从 1 开始递增")
    created_at: datetime
    depends_on_profile_keys: list[str] = Field(default_factory=list)
    diff_from_previous: Optional[str] = Field(
        default=None, description="v(n-1) → v(n) 的差异说明，首版为空"
    )


class TaskSession(BaseModel):
    """任务会话。可拆可续的载体：记录当前环节，而非"报告是否生成"。"""

    model_config = ConfigDict(extra="forbid")

    id: str
    user_id: str
    task_code: str = Field(description="首页任务入口 code，如 confused / verify_direction")
    task_name: str = Field(description="用户可见的任务名")
    loop_stage: LoopStage
    lead_agent: str
    status: TaskStatus = TaskStatus.ACTIVE
    created_at: datetime
    updated_at: datetime
