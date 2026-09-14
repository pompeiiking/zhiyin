"""Redis 实现目录（**空抽屉**，尚未实现）。

一个目录 = 一套实现。本目录是 M3「真实存储」里**缓存与调度**的落点：
把第一期进程内的 `local/` 实现换成 Redis 实现，业务层、编排层、接入层
**一行都不用改**（换实现只改 `zhiyin_boot/container/gateways.py` 的装配表）。

为什么要先建空目录而不是"等实现时再说"
--------------------------------------
`local/` 是"内存实现"的家。没有本目录时，Redis 实现只有两个去处：
写进 `local/`（名字与内容不符，后来者找不到），或临时新建目录（命名各写一套）。
空抽屉的成本是一个文件，收益是"实现放哪"这个决定**在实现之前就定了**。

待实现的 Port 清单（唯一事实来源是 `zhiyin_data_sdk/gateways/`，本文件只是索引）
--------------------------------------------------------------------------------
| Port | 契约文件 | 第一期本地实现（对照语义） | 装配位 |
| --- | --- | --- | --- |
| `CacheGateway` | `gateways/cache.py` | `local/cache.py::InMemoryCache` | `gateways.cache` |
| `RateLimitGateway` | `gateways/security.py` | `local/security.py::NoopRateLimit` | `gateways.rate_limit` |
| `SchedulerGateway` | `gateways/messaging.py` | `local/messaging.py::LocalScheduler` | `gateways.scheduler` |

开工前必须满足的条件
--------------------
1. **契约测试通过**：新实现要过 `tests/contracts/test_gateway_contract.py` 的同一套
   语义断言（缓存 TTL 与命名空间隔离、限流窗口、调度冷却期与次数上限）。
   在 `tests/contracts/conftest.py` 的 `GATEWAY_FACTORIES` 里加一行即可自动纳入。
2. **语义不许漂移**：Redis 版与内存版的**可观察行为**必须一致——
   TTL 过期、命名空间互不串扰、冷却期与次数上限的边界，都由契约测试锁住。

不要把这些实现写回 `local/`：那是内存实现的家（`local/` 的实现必须能在
无任何外部依赖的情况下单机跑通，这是第一期"本地可启动"的前提）。
"""

