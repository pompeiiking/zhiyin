"""主动事件 / 停滞检测 Worker —— 实现交付（第三波 · 后端-3）。

落位：`business/workers/active_event.py`。
依赖：`BehaviorService`（真实行为信号）+ `InterventionPolicy` + `Notifier` + `Scheduler`。

产品硬约束：**不允许系统自嗨式打扰**。是否打扰只由行为日志的真实信号决定，
并受三个参数约束——停滞阈值 / 冷却期 / 打扰上限。

这三个参数**不在本文件**，也不在 `Settings`：每轮扫描前读
`RegistryRepository.get_policy_params("intervention")`
（`data/registry/policy_params.json`，决策 6=A：停滞 3 天 / 冷却 48 小时 /
7 天窗口最多 2 次）。未配置或未定稿（`status != "confirmed"`）即视为不打扰。

实现口径
--------
- 判定本身在 `InterventionPolicy`（`policies/intervention.py`），本类只负责
  "到点扫描 + 按判定结果触发提醒"；
- 扫描入口：业务侧在启动时为每个需要停滞检测的用户注册一条
  `ScheduleSpec(event_type=TASK_STALL_DETECTED, payload={"user_id": ...})`
  （`orchestration/schedule.py` 的契约分工），本 Worker 遍历
  `scheduler.list_registered()` 里的该类规格逐个检查；
- 关键动作口径（`policy_params.intervention.note`，决策 6=A）：作答 / 认领差距 /
  选择方案（含修改选择）/ 勾任务 / 更新画像；纯浏览不算。停滞天数取各类关键
  动作"距今天数"的最小值——最近一次动作的间隔才代表真实活跃度；
- 一条关键动作记录都没有的用户**跳过**（无行为信号即无打扰依据，
  不按注册时间臆测停滞）；
- 冷却期与打扰窗口的记账写在 `ScheduleSpec.payload`
  （`last_notified_at` / `window_start` / `notifications_in_window`），触发后
  以同 task_id 重注册覆盖（`GatewayScheduler.register` 按 task_id 覆盖），
  进程内记账，第一期不追求持久化；
- 提醒文案：标题用 `app.name` 拼装、正文用任务入口 `review_due` 的动态文案，
  动作为 `enter_task(review_due)`——"最小可执行动作"（验收项 7）。
  TODO(动态资源)：教练消息话术键（如 `coach.stall_title` / `coach.stall_body`）
  待补 copies.json，键就位后切到动态文案，删除这里的拼装占位。
"""

from __future__ import annotations

from datetime import datetime, timezone

from zhiyin_business import events
from zhiyin_business.policies.intervention import InterventionPolicy
from zhiyin_business.ports.blackboard import BehaviorService
from zhiyin_data_sdk.repositories import RegistryRepository
from zhiyin_kernel.enums import BehaviorEventType, NotifyChannel
from zhiyin_kernel.worker import Worker
from zhiyin_orchestration import Notifier, Scheduler
from zhiyin_orchestration.notify import NotifyMessage

# 关键动作类型（决策 6=A：有动作 = 作答 / 认领差距 / 选择方案 / 勾任务 /
# 更新画像；纯浏览不算）。TASK_STALL 本身是停滞信号，不是关键动作。
_KEY_ACTION_TYPES: tuple[BehaviorEventType, ...] = (
    BehaviorEventType.ANSWER,
    BehaviorEventType.GAP_CLAIM,
    BehaviorEventType.DECISION_SELECT,
    BehaviorEventType.DECISION_RESELECT,
    BehaviorEventType.TASK_DONE,
    BehaviorEventType.PROFILE_FIELD_UPDATED,
)

_REVIEW_DUE_CODE = "review_due"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    """时间归一：naive 按 UTC 处理，aware 转换到 UTC 再比较。"""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _parse_dt(value: object) -> datetime | None:
    """payload 里的时间可能是 datetime 也可能是 ISO 字符串（序列化往返后）。"""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return None


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

    async def run_once(self) -> int:
        """扫描一轮停滞信号，返回本轮触发的干预条数（0 = 不打扰）。"""
        params = await self._registry.get_policy_params("intervention")
        if params is None or params.status != "confirmed":
            return 0
        window_days = int(params.value.get("window_days", 0))

        # 提醒文案与动作取自动态资源（review_due 入口 = "好久没管了 / 该复盘了"）。
        entries = await self._registry.list_task_entries()
        copies = await self._registry.get_copy_bundle()
        review_entry = next(
            (entry for entry in entries if entry.code == _REVIEW_DUE_CODE), None
        )
        app_name = copies.get("app.name", "")

        triggered = 0
        for spec in self._scheduler.list_registered():
            if spec.event_type != events.TASK_STALL_DETECTED:
                continue
            user_id = spec.payload.get("user_id")
            if not user_id:
                continue

            days_inactive = await self._days_inactive(user_id)
            if days_inactive is None:
                # 从未有过关键动作：无行为信号，不打扰。
                continue

            now = _utcnow()
            window_start = _parse_dt(spec.payload.get("window_start"))
            notified_in_window = int(spec.payload.get("notifications_in_window") or 0)
            if (
                window_start is None
                or (_as_utc(now) - _as_utc(window_start)).total_seconds()
                >= window_days * 86400
            ):
                # 打扰窗口过期：计数重置。
                window_start, notified_in_window = now, 0

            last_notified_at = _parse_dt(spec.payload.get("last_notified_at"))
            if not self._policy.should_intervene(
                days_inactive=days_inactive,
                last_notified_at=last_notified_at,
                notifications_in_window=notified_in_window,
                now=now,
            ):
                continue  # 静默：不满足阈值 / 冷却期内 / 超打扰上限。

            body = (
                f"{review_entry.label}（已停滞 {days_inactive} 天）"
                if review_entry is not None
                else f"已停滞 {days_inactive} 天"
            )
            await self._notifier.push(
                NotifyMessage(
                    user_id=str(user_id),
                    title=_stall_title(app_name, review_entry.label if review_entry else ""),
                    body=body,
                    channel=NotifyChannel.IN_APP.value,
                    action={
                        "type": "enter_task",
                        "task_code": _REVIEW_DUE_CODE,
                    },
                    related_task_id=spec.task_id,
                )
            )
            triggered += 1

            # 触发后按原 task_id 重注册，把冷却与窗口记账写回 payload
            # （GatewayScheduler.register 按 task_id 覆盖，调度参数不变）。
            self._scheduler.register(
                spec.model_copy(
                    update={
                        "payload": {
                            **spec.payload,
                            "last_notified_at": now.isoformat(),
                            "window_start": window_start.isoformat(),
                            "notifications_in_window": notified_in_window + 1,
                        }
                    }
                )
            )
        return triggered

    # ---------- 内部 ----------

    async def _days_inactive(self, user_id: str) -> int | None:
        """距最近一次关键动作的天数（各类关键动作取最小值）。

        返回 None 表示从未有过任何关键动作记录。
        """
        days: list[int] = []
        for event_type in _KEY_ACTION_TYPES:
            gap = await self._behaviors.days_since_last(user_id, event_type)
            if gap is not None:
                days.append(gap)
        return min(days) if days else None


def _stall_title(app_name: str, review_label: str) -> str:
    """提醒标题。

    TODO(动态资源)：占位拼装——app_name 缺失时回落 review 入口文案，
    专用话术键补齐后本函数应改为纯读 copies。
    """
    if app_name:
        return f"{app_name} · 复盘提醒"
    return review_label or "复盘提醒"
