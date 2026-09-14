"""后台执行者的**最小契约**（2 个成员，无任何实现）。

为什么这一层要放它
------------------
业务层有 Worker（影响面传播 / 停滞干预），基础设施层也有 Worker（向量同步 /
嵌入补偿）。两边的基类必须能被双方同时依赖，否则只能各写一份——
那就是"同一能力两处定义"，改一处漏一处。

可用位置只有两个：

- `zhiyin_kernel`：零依赖，所有层可读 ✅
- `zhiyin_data_sdk`：所有层也可读，但它是**数据访问契约**的家，
  "跑一轮"不是数据访问 ❌

因此契约下放到内核，并且**只保留两个成员**：

- `name`：装配报告与 `python -m zhiyin_boot worker <name>` 的寻址键；
- `async run_once() -> int`：处理一轮，返回处理条数。

"怎么被启动"（轮询、随 lifespan 启停、信号处理）属于**驱动方**，
放在 `zhiyin_boot/workers.py`——只有装配层同时认识业务与基础设施。
把它留在基类里会让内核持有行为（asyncio 循环），那是越界。

以后要在内核加接口契约，先看 `zhiyin_kernel/__init__.py` 的准入规则。
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class Worker(ABC):
    """后台执行者契约。

    - `name` 必须与 `zhiyin_boot/container/ports.py` 的能力位名一致；
    - `run_once` 必须**幂等且可重入**：事件驱动的可能被重复投递触发，
      定时 Worker 成长期可能被两个实例同时启动；
    - 异常不得吃掉：交给驱动方决定重试与告警，避免"静默失败"。
    """

    name: str = ""

    @abstractmethod
    async def run_once(self) -> int:
        """处理一轮，返回本轮处理条数（0 表示无待处理）。"""


__all__ = ["Worker"]
