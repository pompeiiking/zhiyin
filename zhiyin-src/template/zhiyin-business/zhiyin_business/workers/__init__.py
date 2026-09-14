"""异步执行者（workers）的归属。

为什么 Worker 不属于编排层
--------------------------
编排层只提供通用原语（调度、事件），**"什么情况该重算""停几天该提醒"是业务规则**，
因此 Worker 属于业务层。基础设施侧的纯数据管道（如向量同步）另放
`zhiyin_infrastructure/workers/`，避免业务规则渗进基础设施。

落位表
------
| Worker | 职责 | 触发方式 |
| --- | --- | --- |
| `impact` | 消费 profile_field_updated，按影响面规则重算并升版本 | 事件订阅 |
| `active_event` | 按干预规则扫描行为日志，触发交接与提醒 | 定时调度 |

两者复用同一个 container（`zhiyin-boot` 装配），第一期可同进程随 lifespan 启动，
成长期用 `python -m zhiyin_boot worker <name>` 独立部署——**部署形态变了，代码不变**。

实现要求：继承 `workers.base.Worker`，只依赖 Port 与 policies，不得 import 基础设施实现。
"""

from zhiyin_business.workers.base import Worker

__all__ = ["Worker"]
