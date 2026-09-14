# 职引 · 第一期工程

模块化单体。共享内核 + 六层单向依赖，接口先于实现冻结：

```
zhiyin-api  →  zhiyin-business  →  zhiyin-orchestration  →  zhiyin-data-sdk  →  zhiyin-infrastructure
   BFF           业务逻辑层             通用编排原语            Data Access SDK        基础设施适配

zhiyin-kernel（共享内核：跨层数据形状，零依赖，任何层都可读）
zhiyin-boot  （唯一装配层，可 import 全部包）
```

对齐文档：`../docs/技术架构文档/第一期工程/`（第一期技术架构 / 分层详细设计 / 分层实现与接口设计 / 业务数据采集与存储来源设计）。

## 快速开始

```bash
cd zhiyin-src/template

# 建议用虚拟环境
python -m venv .venv
. .venv/Scripts/activate        # Windows；macOS/Linux 用 source .venv/bin/activate

pip install -e ".[dev]"          # 需要 MySQL 时再加 ".[mysql]"

# 1. 装配检查：打印每一层实际装了什么，不启动服务
python -m zhiyin_boot --check            # 信息输出，恒退出 0
python -m zhiyin_boot --check --phase=1  # 里程碑门禁：框架可验证（本期退出条件）
python -m zhiyin_boot --check --phase=2  # 里程碑 2：业务主干端到端
python -m zhiyin_boot --check --strict   # 全绿门禁：有部件未装配则退出 1

# 2. 启动
python -m zhiyin_boot            # http://127.0.0.1:8000/docs
```

验证装配：

```bash
curl http://127.0.0.1:8000/healthz
```

`/healthz` 返回 `status: ok|degraded` 与逐部件的装配状态。**degraded 不代表启动失败**，
它表示有部件仍是骨架或未实现（第一期属预期），`assembly.missing` 会列出缺口与归属负责人。

跑测试：

```bash
pytest
```

不安装也能跑：`pyproject.toml` 里已通过 `pythonpath` 配好六个源码目录。

## 目录结构

| 目录 | 包名 | 职责 | 只允许依赖 |
| --- | --- | --- | --- |
| `zhiyin-kernel/` | `zhiyin_kernel` | 共享内核：跨层枚举、画像 / 资产 / 身份 / 动态资源数据形状 | 无（零依赖） |
| `zhiyin-api/` | `zhiyin_api` | Controller / DTO / Application Facade | `zhiyin_business`、`zhiyin_kernel` |
| `zhiyin-business/` | `zhiyin_business` | `ports/`（接口）· `policies/`（规则）· `services/`（实现）· `workers/`（异步） | `zhiyin_orchestration`、`zhiyin_data_sdk`、`zhiyin_kernel` |
| `zhiyin-orchestration/` | `zhiyin_orchestration` | Agent / Workflow / EventBus / Schedule / State / Notify | `zhiyin_data_sdk`、`zhiyin_kernel` |
| `zhiyin-data-sdk/` | `zhiyin_data_sdk` | Repository / Gateway / Transaction 抽象（全部 async） | `zhiyin_kernel` |
| `zhiyin-infrastructure/` | `zhiyin_infrastructure` | local / pami / MySQL 适配器 | `zhiyin_data_sdk`、`zhiyin_kernel` |
| `zhiyin-boot/` | `zhiyin_boot` | 装配（`container/`）、报告与门禁（`report.py`）、CLI | 全部 |
| `zhiyin-web/` | — | Vue 3 + Vite 前端（第一期骨架） | — |
| `data/` | — | 第一期动态资源与本地存储（JSON / 对象目录） | — |

依赖方向由 `tests/test_architecture.py` 用 AST 静态校验，违反即测试失败。

## 两条容易踩的约定

1. **编排层没有第二套契约。** 事件 / 调度 / 通知只有一套语义契约（`zhiyin_orchestration`，
   业务层面向它编程，带信封与幂等）和一套传输契约（`zhiyin_data_sdk.gateways`，
   由基础设施实现）。不要再新建同义抽象。
2. **动态资源不许写进代码。** 文案、任务入口、智能体、理论卡、产出契约、功能开关
   一律走 `data/registry/*.json`（或第二期的动态资源表）。`Settings` 里只放环境与连接参数。
3. **IO 契约一律 async。** Repository 与 Gateway 都是 IO 边界，同步方法会在接真实存储时
   阻塞事件循环。纯内存的私有辅助函数保持同步。换实现时调用方不改。
4. **骨架必须自报家门。** 适配器声明 `IMPLEMENTATION_STATUS = "wired" | "skeleton"`，
   `/healthz` 与 `--check` 据此如实标注，不允许"看起来装好了其实没实现"。
5. **同一能力只有一处定义。** 共享形状在 `zhiyin_kernel`，数据访问契约在 `data_sdk`，
   业务规则在 `policies/`；同名影子定义会被架构守卫拒绝。

## 第一期实现边界

已实现：基础设施本地适配（内存 Repository、JSON 动态资源、本地事件总线 / 调度 / 通知 /
对象存储 / 关键词检索）、编排层六个原语的默认实现、五环节 Loop 的参考实现、
应用工厂与启动入口。

待实现（见 `/healthz` 的 `assembly.missing`）：Orchestrator、黑板四件套服务
（Profile / Behavior / ConversationMemory / Asset）、Workspace / Function Service、
Application Facade、两个 Worker（影响面传播 / 停滞干预）。接口已冻结在
`zhiyin_business/ports/`，规则落位在 `policies/`；接上后 `facade` 与 `services`
会从 `not_wired` 变成 `wired`，`--check --phase=2` 随即转绿。

## 切换外部依赖

全部走 `zhiyin-boot/container/` 的装配表，业务代码不改：

| 环境变量 | 作用 |
| --- | --- |
| `ZHIYIN_USE_MYSQL` + `ZHIYIN_DATABASE_URL` | 启用 MySQL 事务管理器 |
| `ZHIYIN_USE_PAMI_LLM` / `_KNOWLEDGE` / `_AUTH` | 切换 pami 适配器（骨架，首次调用会明确报未实现，不静默回落） |
| `ZHIYIN_DATA_DIR` / `_REGISTRY_DIR` / `_KNOWLEDGE_DIR` / `_OBJECT_DIR` | 本地存储位置 |
| `ZHIYIN_LLM_PROVIDER` | 置空走 Mock（按产出契约 Schema 合成合法结果） |
