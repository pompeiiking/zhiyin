"""调度实现：到点投递 + 冷却期 / 次数上限策略。"""

from __future__ import annotations

from datetime import datetime

from zhiyin_data_sdk.gateways.messaging import ScheduledTask, SchedulerGateway
from zhiyin_orchestration.event import DomainEvent, EventBus
from zhiyin_orchestration.impl._shared import SCHEDULE_TICK_EVENT
from zhiyin_orchestration.schedule import ScheduleSpec, Scheduler


class GatewayScheduler(Scheduler):
    """调度器：把注册项落到 SchedulerGateway，并在到点时执行投递策略。

    策略（R-ORC-004）：
    - cooldown_s：两次实际触发的最小间隔，冷却期内的到点被丢弃；
    - max_triggers：累计触发上限，达到后自动注销。
    """

    def __init__(self, gateway: SchedulerGateway, event_bus: EventBus) -> None:
        self._gateway = gateway
        self._bus = event_bus
        self._specs: dict[str, ScheduleSpec] = {}
        self._fire_count: dict[str, int] = {}
        self._last_fired_at: dict[str, datetime] = {}
        self._cancelled: set[str] = set()
        self._tick_subscribed = False

    def register(self, spec: ScheduleSpec) -> ScheduleSpec:
        self._specs[spec.task_id] = spec
        self._fire_count.setdefault(spec.task_id, 0)
        self._cancelled.discard(spec.task_id)
        task = ScheduledTask(
            task_id=spec.task_id,
            event_type=SCHEDULE_TICK_EVENT,
            payload={"spec": spec.model_dump(mode="json")},
            trigger_at=spec.trigger_at,
            interval_s=spec.interval_s,
            owner_id=spec.payload.get("user_id"),
        )
        self._gateway.register(task)
        self._subscribe_tick()
        return spec

    def cancel(self, task_id: str) -> None:
        self._cancelled.add(task_id)
        self._specs.pop(task_id, None)
        self._gateway.cancel(task_id)

    def list_registered(self) -> list[ScheduleSpec]:
        return [self._specs[k] for k in sorted(self._specs)]

    # ---------- 内部 ----------

    def _subscribe_tick(self) -> None:
        if self._tick_subscribed:
            return
        self._tick_subscribed = True
        self._bus.subscribe(SCHEDULE_TICK_EVENT, self._on_tick)

    async def _on_tick(self, event: DomainEvent) -> None:
        raw = event.payload.get("spec")
        if not isinstance(raw, dict):
            return
        spec = ScheduleSpec.model_validate(raw)
        if spec.task_id in self._cancelled:
            return

        fired = self._fire_count.get(spec.task_id, 0)
        if spec.max_triggers is not None and fired >= spec.max_triggers:
            self.cancel(spec.task_id)
            return

        last = self._last_fired_at.get(spec.task_id)
        if (
            spec.cooldown_s is not None
            and last is not None
            and (event.occurred_at - last).total_seconds() < spec.cooldown_s
        ):
            return

        self._fire_count[spec.task_id] = fired + 1
        self._last_fired_at[spec.task_id] = event.occurred_at
        await self._bus.publish(
            DomainEvent(
                event_id=f"{event.event_id}:{spec.task_id}:{fired + 1}",
                event_type=spec.event_type,
                occurred_at=event.occurred_at,
                payload=dict(spec.payload),
                trace_id=event.trace_id,
            )
        )


__all__ = ["GatewayScheduler"]
