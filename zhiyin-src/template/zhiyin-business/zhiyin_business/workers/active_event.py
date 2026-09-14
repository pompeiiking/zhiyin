"""主动事件 / 停滞检测 Worker（**骨架**，方法体未实现）。

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

from zhiyin_business.policies.intervention import InterventionPolicy
from zhiyin_business.ports.blackboard import BehaviorService
from zhiyin_data_sdk.repositories import RegistryRepository
from zhiyin_kernel.worker import Worker
from zhiyin_orchestration import Notifier, Scheduler

_TODO = "TODO(骨架): ActiveEventWorker 未实现"


class ActiveEventWorker(Worker):
    """停滞检测与主动干预执行者（骨架）。"""

    name = "active_event"
    IMPLEMENTATION_STATUS = "skeleton"

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
        raise NotImplementedError(
            f"{_TODO}：按 intervention 参数扫描真实行为信号，不满足即静默"
        )


__all__ = ["ActiveEventWorker"]
