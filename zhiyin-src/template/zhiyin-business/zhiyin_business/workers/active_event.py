"""主动事件 / 停滞检测 Worker。

落位：`business/workers/active_event.py` —— 业务编排负责人。
依赖：`BehaviorService`（真实行为信号）+ `InterventionPolicy` + `Notifier` + `Scheduler`。

产品硬约束：**不允许系统自嗨式打扰**。是否打扰只由行为日志的真实信号决定，
并受三个参数约束——停滞阈值 / 冷却期 / 打扰上限。

这三个参数**不在本文件**，也不在 `Settings`：读
`RegistryRepository.get_policy_params("intervention")`
（`data/registry/policy_params.json`，当前 `status=draft`，待业务定稿）。
未配置即视为不打扰。

判据（同 `policies/intervention.py`）：本类只负责"到点扫描 + 按判定结果触发交接与提醒"，
判定本身在 `InterventionPolicy`。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from zhiyin_business.policies.intervention import InterventionPolicy
from zhiyin_business.ports.blackboard import BehaviorService
from zhiyin_data_sdk.repositories import RegistryRepository
from zhiyin_kernel.enums import BehaviorEventType
from zhiyin_kernel.worker import Worker
from zhiyin_orchestration import Notifier, NotifyMessage, Scheduler

_ACTION_EVENTS = [
    BehaviorEventType.ANSWER,
    BehaviorEventType.GAP_CLAIM,
    BehaviorEventType.DECISION_SELECT,
    BehaviorEventType.DECISION_RESELECT,
    BehaviorEventType.TASK_DONE,
    BehaviorEventType.PROFILE_FIELD_UPDATED,
    BehaviorEventType.REVIEW,
]


class ActiveEventWorker(Worker):
    """停滞检测与主动干预执行者。"""

    name = "active_event"
    IMPLEMENTATION_STATUS = "wired"

    def __init__(
        self,
        *,
        behaviors: BehaviorService,
        policy: InterventionPolicy,
        registry: RegistryRepository,
        scheduler: Scheduler,
        notifier: Notifier,
    ) -> None:
        self._behaviors = behaviors
        self._policy = policy
        self._registry = registry
        self._scheduler = scheduler
        self._notifier = notifier
        self._notifications: dict[str, list[datetime]] = {}

    async def run_once(self) -> int:
        """扫描一轮停滞信号，返回本轮触发的干预条数（0 = 不打扰）。"""
        params = await self._registry.get_policy_params("intervention")
        if params is None or params.status != "confirmed":
            return 0
        configure = getattr(self._policy, "configure", None)
        if callable(configure):
            configure(params.value)

        now = datetime.now(timezone.utc)
        window_days = int(params.value.get("window_days", 7))
        users: dict[str, str | None] = {}
        for spec in self._scheduler.list_registered():
            user_id = str(spec.payload.get("user_id") or "").strip()
            if user_id:
                users[user_id] = str(spec.payload.get("task_id") or "") or None

        triggered = 0
        for user_id, task_id in users.items():
            logs = await self._behaviors.recent(
                user_id, event_types=_ACTION_EVENTS, limit=1
            )
            if not logs:
                continue
            occurred_at = logs[0].occurred_at
            if occurred_at.tzinfo is None:
                occurred_at = occurred_at.replace(tzinfo=timezone.utc)
            days_inactive = max((now - occurred_at).days, 0)
            cutoff = now - timedelta(days=window_days)
            history = [at for at in self._notifications.get(user_id, []) if at >= cutoff]
            self._notifications[user_id] = history
            last_notified = history[-1] if history else None
            if not self._policy.should_intervene(
                days_inactive=days_inactive,
                last_notified_at=last_notified,
                notifications_in_window=len(history),
                now=now,
            ):
                continue
            await self._notifier.push(
                NotifyMessage(
                    user_id=user_id,
                    title="要不要把下一步再拆小一点？",
                    body="我注意到这项行动停了一阵。先选一个今天 10 分钟内能完成的小动作。",
                    action={"type": "resume_review", "task_id": task_id},
                    related_task_id=task_id,
                )
            )
            history.append(now)
            triggered += 1
        return triggered


__all__ = ["ActiveEventWorker"]
