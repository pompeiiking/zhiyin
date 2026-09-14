"""zhiyin-business · 业务逻辑层。

职责：三轴模型、五环节微循环、动态组队、黑板一致性、影响面传播、工作台聚合。

约束：
- 只允许依赖 zhiyin-orchestration、zhiyin-data-sdk 与共享内核 zhiyin-kernel。
- 禁止直接 import 基础设施实现（必须通过 Port 注入）。
- 跨模块通信只走领域事件，不调用对方私有 Service。

包内结构（分工时按列找人，不要按文件找功能）：

| 目录 | 放什么 | 谁改 |
| --- | --- | --- |
| `ports/` | 服务接口与只读视图（ABC），并行开发前冻结 | 架构 |
| `policies/` | 业务规则（意图→环节、选主理、交接、影响面、干预参数） | 业务编排 |
| `services/` | 服务实现，真正依赖编排层与 SDK 的地方 | 业务编排 / 各业务线 |
| `workers/` | 异步执行者（影响面传播、主动事件） | 业务编排 |
| `contracts/` | 五环节产出契约与通用构件 | 业务编排 |
| `events.py` | 领域事件类型与载荷 | 业务编排 |

关于"对外发布面"：原先的 `published.py`（逐项再导出内核符号给 api）**已删除**。
共享形状归位到零依赖内核 `zhiyin_kernel` 之后，api 按依赖矩阵允许直连内核读枚举与
读模型，再套一层同名再导出只会制造"两条获取路径"。api 访问 `business` 时只面对
`ports/` 抽象与 Facade，不再需要发布面补丁。

包内方向单向：`services/ → policies/ → ports/ → kernel`，禁止倒流
（由 `tests/test_architecture.py::test_business_internal_direction` 守卫）。
"""

from __future__ import annotations

__all__ = ["contracts", "events", "policies", "ports", "services", "workers"]
