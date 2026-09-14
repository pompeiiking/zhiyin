"""MySQL 实现目录（**空抽屉**，尚未实现）。

一个目录 = 一套实现。本目录是 M3「真实存储」里程碑的落点：把
`zhiyin_data_sdk` 的 7 个 Repository 与事务契约换成 MySQL 实现，业务层与接入层
**一行都不用改**（换实现只改 `zhiyin_boot/container/repositories.py` 的装配表）。

待实现的 Port 清单（唯一事实来源是 `zhiyin_data_sdk/repositories/` 与
`zhiyin_data_sdk/transaction.py`，本文件只是索引）：

| Port | 契约文件 | 表清单 |
| --- | --- | --- |
| `ProfileRepository` | `repositories/profile.py` | profile / profile_field / profile_gap |
| `BehaviorRepository` | `repositories/behavior.py` | behavior_log（只追加） |
| `ConversationMemoryRepository` | `repositories/memory.py` | conversation_memory |
| `AssetRepository` | `repositories/assets.py` | asset_version / report / direction_plan / action_plan |
| `TaskSessionRepository` | `repositories/session.py` | task_session |
| `RegistryRepository` | `repositories/registry.py` | 动态资源表（agent_registry / theory_card / output_contract / task_entry / policy_param） |
| `UserRepository` | `repositories/identity.py` | user_account / auth_session / guest_session |
| `TransactionManager` | `transaction.py` | 事务边界 |

两条开工前必须满足的条件：
1. **契约测试通过**：新实现必须过 `tests/contracts/test_repository_contract.py`
   的同一套语义断言（版本单调、只追加、影响面只命中依赖字段、读取是快照）。
   在 `tests/contracts/conftest.py` 的 `REPOSITORY_FACTORIES` 里加一行即可自动纳入。
2. **表清单对齐**：物理表与 `persistence/models.py` 的 `TABLE_INVENTORY` 一致。

同目录的 `persistence/` 目前只有表清单与未实现的事务管理器；真正的 Repository
实现放在本目录，不要写回 `local/`（那是内存实现的家）。
"""

