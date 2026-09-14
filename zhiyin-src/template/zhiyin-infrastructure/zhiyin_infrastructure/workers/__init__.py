"""基础设施侧后台任务目录（**空抽屉**，尚未实现）。

这里放**纯数据管道**，不放业务规则。按《目标架构设计》§5.4 的分家口径：

| Worker | 归属 | 为什么 |
| --- | --- | --- |
| 影响面传播 / 停滞干预 | `zhiyin_business/workers/` | "什么该重算、停几天该提醒"是业务规则 |
| 向量同步 / 嵌入补偿 | **本目录** | 纯数据管道，没有业务语义 |

⚠️ 一个依赖矩阵上的约束（**动手前先看这条**）
--------------------------------------------
业务侧 Worker 的基类是 `zhiyin_business/workers/base.py::Worker`，但
`tests/test_architecture.py` 的矩阵**禁止** `zhiyin_infrastructure` import
`zhiyin_business`（否则基础设施会依赖业务，整个依赖倒置失效）。因此本目录的
Worker **不能继承那个基类**，也不能从编排层取基类（infra 同样不允许 import
`zhiyin_orchestration`）。

当前可行的形状：本目录的 Worker 用**鸭子类型**对齐 `name` 与
`async run_once() -> int` 两个成员，由 `zhiyin_boot` 的 lifespan 统一驱动
（boot 允许 import 全部层，是唯一能同时认识两边的地方）。

如果希望两处共用同一个基类，需要一次拍板（这是外壳级决策，不是实现细节）：
要么把最小的 Worker 形状下沉到一个双方都允许依赖的位置，要么放宽矩阵给 infra
开一个"只读业务 Base"的口子——**不建议后者**。
"""

