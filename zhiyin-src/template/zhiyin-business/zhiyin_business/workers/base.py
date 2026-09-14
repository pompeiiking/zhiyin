"""Worker 基类：把"跑一轮"与"怎么被启动"分开。"""

from __future__ import annotations

import asyncio
import contextlib
from abc import ABC, abstractmethod


class Worker(ABC):
    """异步执行者的统一形状。

    - `name` 用于装配报告与 `python -m zhiyin_boot worker <name>` 的寻址，
      必须与 `zhiyin-boot` 装配表里的键一致；
    - `run_once` 必须**幂等且可重入**：事件驱动的 Worker 可能被重复投递触发，
      定时 Worker 可能被两个实例同时启动（成长期）；幂等键由业务规则决定；
    - 异常不得吃掉：让调用方（启动器）决定重试与告警，避免"静默失败"。
    """

    name: str = ""

    @abstractmethod
    async def run_once(self) -> int:
        """处理一轮，返回本轮处理条数（0 表示无待处理）。"""

    async def run_forever(self, interval_s: float) -> None:
        """按固定间隔轮询，直到被取消。

        写在基类是为了让"怎么被启动"只有一种实现；子类只需实现 `run_once`。
        """
        if interval_s <= 0:
            raise ValueError("interval_s 必须为正数")
        while True:
            await self.run_once()
            await asyncio.sleep(interval_s)

    async def run_until_cancelled(self, interval_s: float, stop: asyncio.Event) -> None:
        """在 `stop` 被设置前轮询；用于 lifespan 内的启停。"""
        task = asyncio.create_task(self.run_forever(interval_s))
        try:
            await stop.wait()
        finally:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task


__all__ = ["Worker"]
