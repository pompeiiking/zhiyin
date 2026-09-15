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
python -m zhiyin_boot            # http://127.0.0.1:8000/api/v1/docs
```

接口契约快照（后端改字段后跑一次，前端类型由它生成）：

```bash
python scripts/export_openapi.py           # 按代码现状覆盖 contracts/openapi.json
python scripts/export_openapi.py --check   # 只校验，不一致退出 1（CI 用）
cd zhiyin-web && npm run gen:api           # 契约快照 → src/api/types.ts（生成物，不要手改）
```

验证装配：

```bash
curl -i http://127.0.0.1:8000/healthz                   # 运维探针（不随版本变化；响应头带 X-Trace-Id）
curl http://127.0.0.1:8000/api/v1/app/bootstrap          # 业务接口（Facade 未装 → 503）
```

`X-Trace-Id` 由 `zhiyin_api/context.py` 生成（上游带了合法值就沿用），并同时写进响应头与
统一信封的 `trace_id`——这是"前端看到的错"与"后端日志"能对上的唯一凭据。生成点全站只有一处。

## 接口前缀：只有一个地方拼 `/api/v1`

所有业务接口都在 `Settings.api_prefix`（默认 `/api/v1`）下，前缀**只由
`zhiyin_api.app.create_app` 统一挂载**：

| 位置 | 正确做法 | 错误做法（会 404） |
| --- | --- | --- |
| Controller 路由 | `@router.get("/app/bootstrap")` | `@router.get("/api/v1/app/bootstrap")` |
| 前端 | `VITE_API_BASE_URL=/api/v1` + `url: '/app/bootstrap'` | baseURL 再拼一次 `/v1` |
| 反向代理 / 网关 | 原样转发 | 再加一层 `/v1` |
| 抓 OpenAPI | `python scripts/export_openapi.py` → `contracts/openapi.json`（或运行时 `GET /api/v1/openapi.json`）；前端 `npm run gen:api` 读的是这份快照 | 手写前缀、手改 `src/api/types.ts` |

唯一的例外是 `/healthz`：运维探针不随 API 版本变化，故意留在版本命名空间之外。
`tests/test_api_prefix.py` 会拦住"路由里再写一次 v1"和"重复嵌套版本段"。

`/healthz` 返回 `status: ok|degraded` 与逐部件的装配状态。**degraded 不代表启动失败**，
它表示有后续阶段部件仍是骨架或未实现，`assembly.missing` 会列出缺口与归属负责人；
第一期 M2 门禁只检查本期所需能力。

跑测试：

```bash
pytest
```

不安装也能跑：`pyproject.toml` 里已通过 `pythonpath` 配好七个源码目录
（kernel / api / business / orchestration / data-sdk / infrastructure / boot）。

## 目录结构

| 目录 | 包名 | 职责 | 只允许依赖 |
| --- | --- | --- | --- |
| `zhiyin-kernel/` | `zhiyin_kernel` | 共享内核：跨层枚举、画像 / 资产 / 身份 / 动态资源与前端页面内容的数据形状 | 无（零依赖） |
| `zhiyin-api/` | `zhiyin_api` | Controller / DTO / `dto/mappers.py`（字段转换唯一处）/ Application Facade | `zhiyin_business`、`zhiyin_kernel` |
| `zhiyin-business/` | `zhiyin_business` | `ports/`（接口，含 api 的两个取数出口）· `policies/`（规则）· `services/`（实现）· `workers/`（异步） | `zhiyin_orchestration`、`zhiyin_data_sdk`、`zhiyin_kernel` |
| `zhiyin-orchestration/` | `zhiyin_orchestration` | Agent / Workflow / EventBus / Schedule / State / Notify | `zhiyin_data_sdk`、`zhiyin_kernel` |
| `zhiyin-data-sdk/` | `zhiyin_data_sdk` | Repository / Gateway / Transaction 抽象（全部 async） | `zhiyin_kernel` |
| `zhiyin-infrastructure/` | `zhiyin_infrastructure` | 第一期本地实现、Redis 分库与合规采集最小链路；另含 M3 替换点抽屉（MySQL/pgvector/Kafka/PAMI/VectorSync） | `zhiyin_data_sdk`、`zhiyin_kernel` |
| `zhiyin-boot/` | `zhiyin_boot` | 装配（`container/`）、报告与门禁（`report.py`）、CLI | 全部 |
| `zhiyin-web/` | — | Vue 3 + Vite 前端（第一期骨架） | — |
| `data/` | — | 第一期动态资源与本地存储（JSON / 对象目录）。`registry/` 下每一类内容改一个 JSON 即可生效，不需要发版 | — |
| `contracts/` | — | 接口契约快照（`openapi.json`）：由代码导出，前端类型由它生成，`test_api_contract.py` 守"代码 == 快照" | — |
| `scripts/` | — | 工程脚本（`export_openapi.py` 导出 / 校验契约快照） | — |
| `tests/` | — | 架构守卫 · 落位守卫 · 文档守卫 · Port 契约测试 · `e2e/`（五环节主路径） | — |

依赖方向由 `tests/test_architecture.py` 用 AST 静态校验，违反即测试失败。

## 容易踩的约定

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
6. **trace id 只有一处生成。** 生成点是 `zhiyin_api/context.py`（由 `create_app` 挂载），
   信封 `trace_id` 由它兜底填充。另造一个"自己的 trace"会让响应头与日志对不上。
7. **生成物不要手改。** `contracts/openapi.json` 与 `zhiyin-web/src/api/types.ts`
   分别由 `python scripts/export_openapi.py` 与 `npm run gen:api` 生成；
   改字段的正确顺序是"改 DTO / Mapper → 重新生成"，冲突时重新生成而不是手工合并。

## 第一期实现边界

已实现：基础设施本地适配（八类内存 Repository、JSON 动态资源、本地事件总线 / 调度 /
通知 / 对象存储 / 关键词检索）、Redis DB 0–6/15 分库适配、合规采集最小链路、编排层
六个原语、五环节 Loop 与 Orchestrator、黑板四件套、Workspace / Function、Identity /
Registry、Application Facade，以及影响传播和停滞干预 Worker。第一期七项 E2E 已执行，
`--check --phase=2` 通过。

M3 仍保留真实 Embedding、`raw_query`、事务管理器和 VectorSync 等替换点；它们会继续在
全量 `/healthz` 中显示为 skeleton/not_wired，但不阻塞第一期 M2 验收。

`--check` 的输出里有两个不同的缺口清单：`missing` 是"能力位没人管"，
`skeletons` 是"外壳就位、实现待补"——本期进度看后者。

> **两个硬前置**：`identity_service`（我是谁）与 `registry_service`（页面长什么样）。
> `/app/bootstrap` 没有它们就没有任何数据可返回，前端也连不上；
> 它们都是"api 需要、契约却在 data_sdk"逼出来的业务侧出口，判据见
> `business/ports/registry.py` 的模块 docstring。

## 团队分工与并行

| 想做的事 | 先看 |
| --- | --- |
| 认领一个业务服务 | `zhiyin_business/services/__init__.py` 的落位表（一人一列） |
| 认领一个前端页面 / 组件 | `zhiyin-web/README.md` 的页面 → 组件 → 接口落位表 |
| 改一个页面字段 | `api/dto/mappers.py`（字段口径唯一处），不要改 Facade 里的字段拼接 |
| 加一条任务入口 / 文案 / 开关 | 只改 `data/registry/*.json`，不发版 |
| 换 MySQL / Redis / pgvector / Kafka | `zhiyin_boot/container/` 装配表 + 对应抽屉（`infrastructure/{mysql,redis,pgvector,kafka}/`）+ 过 `tests/contracts/` |
| 改接口字段 | `api/dto/*.py` + `dto/mappers.py` → `python scripts/export_openapi.py` → `cd zhiyin-web && npm run gen:api` |

完整分工与剩余缺口见仓根 `docs/评审/职引-架构与结构评估-最终版.md`（唯一当前状态）
与 `docs/评审/业务口径决策记录-v1.0.md`（16 项业务口径定稿基线）。

## 切换外部依赖

全部走 `zhiyin-boot/container/` 的装配表，业务代码不改：

| 环境变量 | 作用 |
| --- | --- |
| `ZHIYIN_USE_MYSQL` + `ZHIYIN_DATABASE_URL` | 启用 MySQL 事务管理器 |
| `ZHIYIN_USE_PAMI_LLM` / `_KNOWLEDGE` / `_AUTH` | 切换 pami 适配器（骨架，首次调用会明确报未实现，不静默回落） |
| `ZHIYIN_DATA_DIR` / `_REGISTRY_DIR` / `_KNOWLEDGE_DIR` / `_OBJECT_DIR` | 本地存储位置 |
| `ZHIYIN_LLM_PROVIDER` | 置空走 Mock（按产出契约 Schema 合成合法结果） |
| `ZHIYIN_MOCK` | 前端联调开关（决策 15）：置 1 时 boot 装配 `MockApplicationFacade`；该替身目前是骨架，实现完成后启用 |
