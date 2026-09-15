"""影响面传播 Worker。

落位：`business/workers/impact.py`；第一期排期实现工位：后端-2（数据访问负责人）。
依赖：`AssetService` + `EventBus`（订阅 `profile_field_updated`）。

职责：消费画像字段更新事件 → 调 `AssetService.propagate` → 只重算受影响片段。
本类**不实现重算范围判定**（那在 `policies/impact.py`），只负责"什么时候跑、跑谁"。

幂等要求（`Worker` 基类已声明）：同一字段可能被重复投递，`run_once` 必须可重入。
注册方式见 `zhiyin_boot/container/services.py::build_workers`——注册进装配表即受
lifespan 统一启停，未注册时 `--check` 会如实报 `not_wired`。
"""

from __future__ import annotations

from collections import deque
from typing import Optional

from zhiyin_business.events import PROFILE_FIELD_UPDATED, ProfileFieldUpdatedPayload
from zhiyin_business.ports.blackboard import AssetService
from zhiyin_data_sdk.gateways.cache import CacheGateway
from zhiyin_kernel.worker import Worker
from zhiyin_orchestration import DomainEvent, EventBus


class ImpactPropagationWorker(Worker):
    """先订阅入队、再由 ``run_once`` 可重入消费画像更新事件。"""

    name = "impact"
    IMPLEMENTATION_STATUS = "wired"

    def __init__(
        self,
        assets: AssetService,
        event_bus: EventBus,
        idempotency_store: Optional[CacheGateway] = None,
        *,
        idempotency_ttl_s: int = 7 * 24 * 60 * 60,
    ) -> None:
        if idempotency_ttl_s <= 0:
            raise ValueError("Worker 幂等保留期必须为正数")
        self._assets = assets
        self._event_bus = event_bus
        self._idempotency_store = idempotency_store
        self._idempotency_ttl_s = idempotency_ttl_s
        self._pending: deque[tuple[str, ProfileFieldUpdatedPayload]] = deque()
        self._queued: set[str] = set()
        self._processed: set[str] = set()
        self._event_bus.subscribe(PROFILE_FIELD_UPDATED, self._enqueue)

    def _enqueue(self, event: DomainEvent) -> None:
        payload = ProfileFieldUpdatedPayload.model_validate(event.payload)
        key = (
            event.idempotency_key
            or f"profile:{payload.user_id}:{payload.field_key}:{payload.profile_version}"
        )
        if key in self._processed or key in self._queued:
            return
        self._pending.append((key, payload))
        self._queued.add(key)

    async def run_once(self) -> int:
        """处理一轮待传播的画像字段更新，返回本轮处理条数（0 = 无待处理）。"""
        processed = 0
        while self._pending:
            key, payload = self._pending.popleft()
            self._queued.discard(key)
            if key in self._processed:
                continue
            applied = False
            try:
                if (
                    self._idempotency_store is not None
                    and await self._idempotency_store.get("idempotency", key)
                ):
                    self._processed.add(key)
                    continue
                await self._assets.propagate(payload.user_id, [payload.field_key])
                applied = True
                if self._idempotency_store is not None:
                    await self._idempotency_store.set(
                        "idempotency",
                        key,
                        "processed",
                        ttl_s=self._idempotency_ttl_s,
                    )
            except Exception:
                if applied:
                    # 业务写已经成功，不能因为幂等标记暂时写失败而在本进程重复升版。
                    self._processed.add(key)
                else:
                    self._pending.appendleft((key, payload))
                    self._queued.add(key)
                raise
            self._processed.add(key)
            processed += 1
        return processed


__all__ = ["ImpactPropagationWorker"]
