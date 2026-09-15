"""业务领域事件契约。

规则（并行开发规则）：
- 跨模块通信只使用领域事件，不互相调用对方的私有 Service。
- 事件类型字符串在此集中定义，禁止在业务代码里散写魔法字符串。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict

from zhiyin_kernel.enums import BehaviorEventType

# ---------- 事件类型常量 ----------

PROFILE_FIELD_UPDATED = "profile_field_updated"
"""画像字段更新。订阅方：资产服务（影响面传播）。"""

ASSET_VERSION_CHANGED = "asset_version_changed"
"""资产版本变化。订阅方：工作台刷新、通知。"""

LOOP_STAGE_CHANGED = "loop_stage_changed"
"""环节切换。订阅方：会话记忆、工作台。"""

BEHAVIOR_LOGGED = "behavior_logged"
"""行为写入。订阅方：成就体系、复盘停滞检测。"""

TASK_STALL_DETECTED = "task_stall_detected"
"""停滞被检出（由调度器触发）。订阅方：编排器（交接复盘）。"""


# ---------- 事件载荷 ----------


class ProfileFieldUpdatedPayload(BaseModel):
    """profile_field_updated 的载荷。

    影响面传播的输入：命中 depends_on_profile_keys 的资产才重算。
    """

    model_config = ConfigDict(extra="forbid")

    user_id: str
    field_key: str
    confidence: float
    source: str
    profile_version: int
    updated_at: datetime


class BehaviorLoggedPayload(BaseModel):
    """behavior_logged 的统一载荷。"""

    model_config = ConfigDict(extra="forbid")

    user_id: str
    behavior_log_id: str
    behavior_event_type: BehaviorEventType
    occurred_at: datetime
    payload: dict[str, Any]
    related_asset_ids: list[str]


class AssetVersionChangedPayload(BaseModel):
    """asset_version_changed 的载荷。"""

    model_config = ConfigDict(extra="forbid")

    user_id: str
    asset_type: str
    asset_id: str
    from_version: Optional[int] = None
    to_version: int
    diff_from_previous: Optional[str] = None


class LoopStageChangedPayload(BaseModel):
    """loop_stage_changed 的载荷。显式告知的落点之一。"""

    model_config = ConfigDict(extra="forbid")

    user_id: str
    task_id: str
    from_stage: Optional[str] = None
    to_stage: str
    from_agent: Optional[str] = None
    to_agent: str
    reason: str


class TaskStallDetectedPayload(BaseModel):
    """task_stall_detected 的载荷。携带停滞天数供打扰度控制使用。"""

    model_config = ConfigDict(extra="forbid")

    user_id: str
    days_inactive: int
    last_event_at: Optional[datetime] = None
