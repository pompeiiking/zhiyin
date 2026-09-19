# 职引 ZHIYIN

以职业咨询方法论为底座的 AI 职业引导产品。本仓是**第一期工程**的文档、原型与代码骨架。

| 项 | 内容 |
| --- | --- |
| 当前阶段 | 架构外壳已铺完，业务实现未开始（`--check --phase=1` 通过，M2 待补） |
| 代码位置 | `zhiyin-src/template/`（模块化单体，7 个 Python 包 + Vue 前端） |
| 上手入口 | [docs/开发指南.md](docs/开发指南.md)（架构地图与落位手册） |
| 文档索引 | [docs/README.md](docs/README.md) |

## 目录

```text
docs/                     需求、架构、评审、前端设计（唯一事实来源）
prototype/                高保真原型与技术方案（视觉与交互基线）
zhiyin-src/template/      第一期工程骨架
  zhiyin-kernel/            共享内核（跨层数据形状，零依赖）
  zhiyin-api/               BFF：Controller / DTO / Mapper / Facade
  zhiyin-business/          业务层：ports / policies / services / workers
  zhiyin-orchestration/     通用编排原语（无业务语义）
  zhiyin-data-sdk/          数据访问契约（只定义，不实现）
  zhiyin-infrastructure/    基础设施实现（local）+ 替换点抽屉（mysql / redis / pgvector / kafka / pami / workers）
  zhiyin-boot/              唯一装配层 + 分级门禁
  zhiyin-web/               前端（Vue 3 + Vite）
  data/registry/            动态资源（文案 / 任务入口 / 智能体 / 开关…）
  contracts/openapi.json    接口契约快照（代码导出 → 前端类型由它生成）
  scripts/                  工程脚本（契约导出 / 校验）
  tests/                    架构守卫 + 落位守卫 + Port 契约测试 + e2e
```

## 五分钟上手

```bash
cd zhiyin-src/template

python -m venv .venv && . .venv/Scripts/activate    # Windows；macOS/Linux 用 source
pip install -e ".[dev,m3]"              # 全量测试包含 M3 数据基础设施用例

python -m pytest -q                      # 架构守卫 + 契约测试 + 单元测试
python -m ruff check .                   # 静态检查
python scripts/export_openapi.py --check # 接口契约快照与代码一致
python -m zhiyin_boot --check --phase=1  # 里程碑门禁：框架可验证（本期退出条件）
python -m zhiyin_boot                    # 启动：http://127.0.0.1:8000/api/v1/docs
```

前端见 [zhiyin-src/template/zhiyin-web/README.md](zhiyin-src/template/zhiyin-web/README.md)。

## 内置 pami/zhiyinbase 部署基线

zhiyinbase 源码位于 `platform/wanwu/`，职引后端与 zhiyinbase 通过 `wanwu-net` 内部网络运行。

```powershell
python zhiyin-src/template/deploy/init_env.py
pwsh zhiyin-src/template/deploy/up.ps1
pwsh zhiyin-src/template/deploy/verify.ps1
pwsh zhiyin-src/template/deploy/down.ps1
```

当前交付包含 zhiyinbase 源码快照、独立构建、统一 Compose 和原生接口路由。
zhiyinbase 原生接口从 `http://127.0.0.1:8081` 的 Nginx/BFF 入口访问，继续使用
zhiyinbase 自身的 JWT、API Key 和权限规则。职引 `/api/v1/*` 不透明代理这些接口。

`ZHIYIN_USE_PAMI_*` 保持关闭，`zhiyin-infrastructure/pami/` 仅保留生产替换
骨架；本交付不宣称真实账号、模型、知识库、Agent、RAG 或工作流已经联通。

**接口字段怎么做到前后端不漂移**（三段链路，任一环断裂 CI 就红）：

```text
后端 Controller / DTO ──(python scripts/export_openapi.py)──▶ contracts/openapi.json
                                                                    │(npm run gen:api)
                                                                    ▼
                                                        src/api/types.ts（生成物）
```

后端改字段后跑一次导出脚本，前端跑一次生成脚本；两边都不是手写的。

## 这套骨架靠什么防跑偏

架构约束不靠 review 记忆，靠这些机械守卫：

| 守什么 | 在哪 |
| --- | --- |
| 层与层不许乱连（依赖矩阵、内核零依赖、无重复契约） | `tests/test_architecture.py` |
| 每个能力位都有实体、骨架不许假装完成、动态资源引用闭合 | `tests/test_shell_completeness.py` |
| 同一套语义断言跑所有实现（内存 → MySQL 不许漂移） | `tests/contracts/` |
| 接口契约快照与代码一致 / 前端类型与快照一致 | `tests/test_api_contract.py` + `python scripts/export_openapi.py --check` + `npm run check:api` |
| 前后端口径对齐（错误码 / 路由锚点 / url 清单 / 组件落位表） | `tests/test_frontend_alignment.py` |
| trace id 有唯一生产者、每个响应带 `X-Trace-Id`、信封与响应头同 id | `tests/test_request_context.py` |
| 装配清单 / 报告 / 门禁三者一致（能力位不许重名、不许拼错、必须有落点） | `tests/test_assembly.py` |
| 文档不漂移（链接、引用的路径、能力位数量、门禁落点） | `tests/test_docs_alignment.py` |
| 装配现状与里程碑门禁（wired / skeleton / not_wired + 归属） | `python -m zhiyin_boot --check --phase=N` |

CI 会跑上面全部内容（见 [.github/workflows/ci.yml](.github/workflows/ci.yml)），
所以"越层 / 漏装配 / 契约漂移"不会靠人发现。

## 六条不可违反的底线

1. 业务层不直接 import 具体实现，只依赖契约（保住八个替换点）。
2. 不建 `utils` / `common` / `helpers` 这类通用包。
3. 动态资源不进代码：文案、任务入口、智能体、理论卡、产出契约、开关、规则参数一律走 `data/registry/`。
4. 编排层不出现业务语义（五环节 / 画像 / 主理），由 AST 守卫强制。
5. 基础设施层不得引用业务层与编排层，由 AST 守卫强制。
6. 生成物不许手改：`contracts/openapi.json` 与 `zhiyin-web/src/api/types.ts` 都由脚本生成（改字段先改 DTO / Mapper，再重新生成）。

落位决策树（新代码该放哪）见 [docs/开发指南.md](docs/开发指南.md) §四。
