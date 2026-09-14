"""Kafka 实现目录（**空抽屉**，尚未实现）。

一个目录 = 一套实现。本目录是「事件与消息传输」的落点：把进程内事件总线换成
Kafka（或复用 pami 平台的 Kafka），业务层与编排层**一行都不用改**
（换实现只改 `zhiyin_boot/container/gateways.py` 的装配表）。

口径提醒（容易踩）：**语义契约在编排层，传输契约在 SDK**
-------------------------------------------------------
| 层次 | 归属 | 第一期实现 | 换 Kafka 时改什么 |
| --- | --- | --- | --- |
| 语义（信封 / 幂等 / 订阅关系） | `zhiyin_orchestration::EventBus` | `impl/event_bus.py::GatewayEventBus` | **不动**（业务只面向它编程） |
| 传输（怎么把消息送出去） | `zhiyin_data_sdk.gateways.messaging::EventBusGateway` | `local/messaging.py::InMemoryEventBus` | 本目录新增实现，装配表换一行 |

因此本目录**不建第二套事件抽象**：只实现 SDK 的传输契约，
信封与幂等语义仍由编排层包装（见《开发指南》§五 的两条容易踩的约定）。

待实现的 Port 清单（唯一事实来源是 `zhiyin_data_sdk/gateways/messaging.py`）
-------------------------------------------------------------------------
| Port | 契约文件 | 第一期本地实现 | 装配位 |
| --- | --- | --- | --- |
| `EventBusGateway` | `gateways/messaging.py` | `local/messaging.py::InMemoryEventBus` | `gateways.event_bus` |
| `SchedulerGateway` | `gateways/messaging.py` | `local/messaging.py::LocalScheduler` | `gateways.scheduler` |
| `NotifyGateway` | `gateways/messaging.py` | `local/messaging.py::LocalNotify` | `gateways.notifier` |

开工前必须满足的条件
--------------------
1. **至少一次投递 + 重试 + 死信**（M4 门禁 manual 项）：投递失败不能静默丢，
   否则"影响面传播"与"主动干预"会偶发不执行而不报错。
2. **幂等由编排层保证，传输层不得重复放大**：`GatewayEventBus` 已带 LRU 幂等，
   Kafka 版重放消息时不得绕过它（消费者组语义与幂等窗口的配合要一起验证）。
3. **契约测试通过**：在 `tests/contracts/conftest.py` 的 `GATEWAY_FACTORIES`
   里加一行，让同一套语义断言也跑 Kafka 实现。
"""

