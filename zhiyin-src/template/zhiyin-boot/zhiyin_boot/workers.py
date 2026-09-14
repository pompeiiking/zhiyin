"""Worker 驱动：把"跑一轮"变成"一直跑 / 随生命周期跑"。

为什么驱动逻辑在装配层，而不在 Worker 基类里
--------------------------------------------
Worker 契约（`zhiyin_kernel.worker.Worker`）只有 `name` 与 `run_once`——
因为它必须被**业务层与基础设施层同时**依赖，而这两层唯一的公共依赖是内核，
内核又不允许出现行为（asyncio 循环属于行为）。

于是分工变成：

- 谁需要知道"该跑了" → 只有装配层（boot 允许 import 全部层）；
- Worker 自己只管"跑一轮做什么"。

这样换启动方式（同进程 lifespan / 独立进程 / 未来 Kubernetes CronJob）只改本文件，
Worker 实现与契约都不动。
"""

from __future__ import annotations

import asyncio
import contextlib
from typing import Protocol


class Runnable(Protocol):
    """驱动方需要的最小形状（鸭子类型）。

    用 Protocol 而不是继承抽象类：驱动方不应该反过来要求 Worker 继承什么，
    只要它有 `name` 与 `run_once` 就能被驱动。
    """

    name: str

    async def run_once(self) -> int:  # pragma: no cover - 协议声明
        ...


async def run_forever(worker: Runnable, interval_s: float) -> None:
    """按固定间隔轮询，直到被取消。"""
    if interval_s <= 0:
        raise ValueError("interval_s 必须为正数")
    while True:
        await worker.run_once()
        await asyncio.sleep(interval_s)


async def run_until_cancelled(
    worker: Runnable, interval_s: float, stop: asyncio.Event
) -> None:
    """在 `stop` 被设置前轮询；用于 lifespan 内的统一启停。"""
    task = asyncio.create_task(run_forever(worker, interval_s))
    try:
        await stop.wait()
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


__all__ = ["Runnable", "run_forever", "run_until_cancelled"]
