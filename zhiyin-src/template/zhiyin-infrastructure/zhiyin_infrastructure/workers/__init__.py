"""基础设施侧后台任务目录（**空抽屉**，尚未实现）。

这里放**纯数据管道**，不放业务规则。按《目标架构设计》§5.4 的分家口径：

| Worker | 归属 | 为什么 |
| --- | --- | --- |
| 影响面传播 / 停滞干预 | `zhiyin_business/workers/` | "什么该重算、停几天该提醒"是业务规则 |
| 向量同步 / 嵌入补偿 | **本目录** | 纯数据管道，没有业务语义 |

基类来自哪里（已定案）
----------------------
`tests/test_architecture.py` 的矩阵**禁止** `zhiyin_infrastructure` import
`zhiyin_business` 与 `zhiyin_orchestration`（否则基础设施会依赖业务，依赖倒置失效）。
因此本目录的 Worker **不能**继承业务侧的类。

契约已下放到双方唯一的公共依赖——内核：

    from zhiyin_kernel.worker import Worker   # name + async run_once() -> int

只有这两个成员，没有 asyncio 循环（行为留在驱动方
`zhiyin_boot/workers.py`）。业务侧 Worker（`zhiyin_business/workers/`）用的是
**同一个**基类，不存在两份同义定义。

落位：`vector_sync.py` 之类的纯数据管道实现写在本目录，装配在
`zhiyin_boot/container/services.py::build_workers`。
"""
