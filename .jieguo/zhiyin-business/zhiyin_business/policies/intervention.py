"""主动干预规则（FR-REVIEW-001）—— 实现交付（第二波 · 后端-4）。

产品口径：不允许"系统自嗨式打扰"。是否打扰用户必须由行为日志的真实信号
决定，并受三个参数约束——停滞阈值、冷却期、打扰上限。

**这三个参数是业务规则而非实现细节**，因此：
- 参数取自动态资源（`data/registry/policy_params.json`，决策 6=A 已 confirmed），
  不得写死在代码里；
- 本模块只给"该不该触发"的判定，真正的触发动作为"交接给教练 + 推一条消息"，
  由编排器与 `workers/active_event.py` 完成。

实现口径（对着已冻结 ABC 交付）：
- ABC 的 `should_intervene` 是**纯同步方法**，因此三个参数在构造时注入；
  动态资源解析经 `from_registry()` 异步工厂完成（编排器 / 装配方调用一次），
  规则本体可以被单测直接驱动，不访问 Repository；
- "未配置即视为不打扰"：`from_registry` 在参数缺失或 `status != confirmed`
  时返回 None，调用方不得自行编造默认值；
- 冷却期比较对 naive / aware datetime 做统一归一（第一期本地实现时间口径
  不完全一致，归一失败比静默误判好——异常直接暴露给调用方）；
- `window_days` 属于同一参数集，由本类**携带**（打扰窗口的重置记账在
  Worker 侧完成，读 `policy.window_days`），保证四个参数只有一处来源。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone

from zhiyin_data_sdk.repositories import RegistryRepository

_PARAM_KEYS = (
    "stall_threshold_days",
    "cooldown_hours",
    "max_notifications_per_window",
    "window_days",
)


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


class ThresholdInterventionPolicy(InterventionPolicy):
    """阈值判定：停滞天数 / 冷却期 / 打扰上限三条件同时满足才允许打扰。"""

    def __init__(
        self,
        *,
        stall_threshold_days: int,
        cooldown_hours: int,
        max_notifications_per_window: int,
        window_days: int,
    ) -> None:
        self.stall_threshold_days = stall_threshold_days
        self.cooldown_hours = cooldown_hours
        self.max_notifications_per_window = max_notifications_per_window
        self.window_days = window_days

    @classmethod
    async def from_registry(
        cls, registry: RegistryRepository
    ) -> "ThresholdInterventionPolicy | None":
        """从动态资源解析参数集（装配方在启动时调用一次）。

        参数缺失或未定稿（`status != "confirmed"`）返回 None——
        未配置即视为不打扰，**不得**回落到代码里的默认值。
        """
        params = await registry.get_policy_params("intervention")
        if params is None or params.status != "confirmed":
            return None

        missing = [key for key in _PARAM_KEYS if key not in params.value]
        if missing:
            raise ValueError(
                f"policy_params.intervention 已配置但缺少参数键：{missing}，"
                "参数集不完整时拒绝臆测口径"
            )
        return cls(
            stall_threshold_days=int(params.value["stall_threshold_days"]),
            cooldown_hours=int(params.value["cooldown_hours"]),
            max_notifications_per_window=int(
                params.value["max_notifications_per_window"]
            ),
            window_days=int(params.value["window_days"]),
        )

    # ---------- ABC 实现 ----------

    def should_intervene(
        self,
        *,
        days_inactive: int,
        last_notified_at: datetime | None,
        notifications_in_window: int,
        now: datetime,
    ) -> bool:
        # ① 停滞阈值：关键动作（作答 / 认领差距 / 选择 / 勾任务 / 更新画像）
        #    距今天数不足阈值 → 不打扰（纯浏览不算动作，见 policy_params 注记）。
        if days_inactive < self.stall_threshold_days:
            return False
        # ② 冷却期：同一条提醒两次实际触发的最小间隔。
        if last_notified_at is not None:
            elapsed = self._as_utc(now) - self._as_utc(last_notified_at)
            if elapsed < timedelta(hours=self.cooldown_hours):
                return False
        # ③ 打扰上限：任意 window_days 天窗口内的触达次数上限
        #    （窗口重置记账由 Worker 完成，这里只做上限判断）。
        if notifications_in_window >= self.max_notifications_per_window:
            return False
        return True

    # ---------- 内部 ----------

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        """时间归一：naive 按 UTC 处理，aware 转换到 UTC 再比较。"""
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


__all__ = ["InterventionPolicy", "ThresholdInterventionPolicy"]
