"""影响面传播 Worker（**骨架**，方法体未实现）。

落位：`business/workers/impact.py` —— 业务编排负责人。
依赖：`AssetService` + `EventBus`（订阅 `profile_field_updated`）。

职责：消费画像字段更新事件 → 调 `AssetService.propagate` → 只重算受影响片段。
本类**不实现重算范围判定**（那在 `policies/impact.py`），只负责"什么时候跑、跑谁"。

幂等要求（`Worker` 基类已声明）：同一字段可能被重复投递，`run_once` 必须可重入。
注册方式见 `zhiyin_boot/container/services.py::build_workers`——注册进装配表即受
lifespan 统一启停，未注册时 `--check` 会如实报 `not_wired`。
"""

from __future__ import annotations

from zhiyin_business.ports.blackboard import AssetService
from zhiyin_kernel.worker import Worker
from zhiyin_orchestration import EventBus

_TODO = "TODO(骨架): ImpactPropagationWorker 未实现"


class ImpactPropagationWorker(Worker):
    """影响面传播执行者（骨架）。"""

    name = "impact"
    IMPLEMENTATION_STATUS = "skeleton"

    def __init__(self, assets: AssetService, event_bus: EventBus) -> None:
        self._assets = assets
        self._event_bus = event_bus

    async def run_once(self) -> int:
        """处理一轮待传播的画像字段更新，返回本轮处理条数（0 = 无待处理）。"""
        raise NotImplementedError(
            f"{_TODO}：订阅 profile_field_updated → 调 AssetService.propagate"
        )


__all__ = ["ImpactPropagationWorker"]
