"""主动干预规则（FR-REVIEW-001）。

产品口径：不允许"系统自嗨式打扰"。是否打扰用户必须由行为日志的真实信号
决定，并受三个参数约束——停滞阈值、冷却期、打扰上限。

**这三个参数是业务规则而非实现细节**，因此：
- 参数取自动态资源（`data/registry/*.json`，见《业务数据采集与存储来源设计》），
  不得写死在代码里；
- 本模块只给"该不该触发"的判定，真正的触发动作为"交接给教练 + 推一条消息"，
  由编排器与 Worker 完成。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone


class InterventionPolicy(ABC):
    """停滞干预判定规则。"""

    @abstractmethod
    def should_intervene(
        self,
        *,
        days_inactive: int,
        last_notified_at: datetime | None,
        notifications_in_window: int,
        now: datetime,
    ) -> bool:
        """是否允许触发一次主动干预。

        三个输入分别对应：停滞阈值（`days_inactive`）、冷却期
        （`last_notified_at`）、打扰上限（`notifications_in_window`）。
        任一不满足即返回 False，静默不打扰。
        """


class ConfiguredInterventionPolicy(InterventionPolicy):
    """使用动态资源注入的停滞、冷却和窗口上限参数。"""

    IMPLEMENTATION_STATUS = "wired"

    def __init__(self) -> None:
        self.configure({})

    def configure(self, values: dict) -> None:
        self.stall_threshold_days = int(values.get("stall_threshold_days", 3))
        self.cooldown_hours = float(values.get("cooldown_hours", 48))
        self.max_notifications_per_window = int(
            values.get("max_notifications_per_window", 2)
        )

    def should_intervene(
        self,
        *,
        days_inactive: int,
        last_notified_at: datetime | None,
        notifications_in_window: int,
        now: datetime,
    ) -> bool:
        if days_inactive < self.stall_threshold_days:
            return False
        if notifications_in_window >= self.max_notifications_per_window:
            return False
        if last_notified_at is None:
            return True
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        if last_notified_at.tzinfo is None:
            last_notified_at = last_notified_at.replace(tzinfo=timezone.utc)
        return now - last_notified_at >= timedelta(hours=self.cooldown_hours)


__all__ = ["ConfiguredInterventionPolicy", "InterventionPolicy"]
