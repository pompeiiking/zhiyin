# 职引 · 第一期未闭合项与 Mock 标注清单

| 项目 | 内容 |
| --- | --- |
| 文档用途 | 把第一期"代码已实现、但未接入可运行链路"的缺口与 Mock 内容显式标记出来，避免被"门禁通过 / 测试全绿"掩盖 |
| 产生方式 | 对 `data-yuan@93f85f3` 的独立复核（2026-09-15），复核命令与实测结果见本文第四节 |
| 复核范围扩展 | `business-tao@dfd7f34`（业务分支，2026-09-15）：闭合 OPEN-5，新增 OPEN-6 |
| 本轮更新 | `service-tao@6187923`（业务编排分支，2026-09-16）：闭合 OPEN-1、OPEN-2，并迁移为正式 e2e 回归 |
| 与原记录的关系 | 《职引-数据能力全链路完成情况记录》的个人自评保持原样；**两份文档必须合读**，本文只补充其未覆盖的缺口 |
| 当前状态 | OPEN-1、OPEN-2、OPEN-3、OPEN-4、OPEN-5 已闭合；OPEN-6 已修（见第五节）；MOCK-1、MOCK-2 于 2026-09-19 因「清除 Mock」变更失去对象（见第五节）；**MOCK-3（检索内容仍是演示卡）于 2026-09-19 新发现，已如实上报并加护栏，内容本身待平台/内容侧（见 §五之后）** |
| 清理约定 | 每项修好后，删除对应代码标记与 `tests/e2e/test_phase1_open_items.py` 中的用例，并把本文状态改为"已闭合" |

> **当前结论**：OPEN-1、OPEN-2 已由业务编排链路接通并转为正式 e2e 回归；
> OPEN-3 已按“预留能力位”决策闭合，OPEN-5 的服务状态守卫已经恢复；
> OPEN-4、OPEN-6 与 MOCK-1 仍按本文继续跟踪。原始复核证据保留，避免覆盖问题历史。

---

## 一、未闭合项

状态图例：**未闭合** = 组件已实现且测试通过，但主链路没有调用方；**部分闭合** = 链路可用但有一环仍是占位。

### OPEN-1 · 资产正文从未落库，报告页 / 工作台 ②③④ 读不到内容 —— 已闭合

闭环说明：`DefaultOrchestrator._persist_output` 已分别调用 `save_report`、
`save_direction_plans`、`save_action_plan`；正文与版本元数据由资产服务原子保存。
原 xfail 已迁移为 `tests/e2e/test_main_path.py::test_acceptance_8_orchestrator_persists_full_assets_and_knowledge`。

| 项 | 内容 |
| --- | --- |
| 现象 | 走完五环节后，报告、方向方案、行动计划都有版本号（v1），但 `GET /app/report/full-text` 返回 `code=1002「尚未生成诊断报告」`；工作台 ②③④ 面板同时显示 `version=1` 与"尚未生成…"，对前端自相矛盾 |
| 根因 | `DefaultOrchestrator._persist_output` 只调 `assets.save_version(AssetUpdateDraft(...))` 写**版本元数据**，丢弃了 `DiagnoseOutput` / `DecideOutput` / `ActOutput` 中的正文；本轮新增的 `save_report` / `save_direction_plans` / `save_action_plan` 三个正文写入 API **只有测试在调用** |
| 为什么测试没拦住 | 现有用例直接构造正文调用 `save_report(...)`，绕过了"对话 → 落库 → 读回"这条真实路径，因此 297 条测试全绿也不能证明报告页可读 |
| 归属 | 待定：写入触发点在编排侧（`_persist_output`），写入 API 在数据侧。建议由**编排负责人**接线；数据侧负责提供 API（已完成） |
| 退出判据 | 诊断环节结束后 `get_report()` 非空且版本与 `list_versions(REPORT)[-1]` 一致；`tests/e2e/test_phase1_open_items.py::test_open1_*` 由 xfail 变 XPASS 并删除标记 |
| 代码标记 | `business/services/orchestrator.py` · `business/services/asset.py` |

### OPEN-2 · 本地知识检索未接入诊断 / 决策链路 —— 已闭合

闭环说明：诊断、决策现在读取当前主理的动态理论卡，调用
`KnowledgeGateway.search(namespace="theory")`，把命中注入 Agent 上下文，并只将真实命中转换为 TheoryRef。
同一正式 e2e 同时校验引用 ID 属于 `data/knowledge/theory.json`。

| 项 | 内容 |
| --- | --- |
| 现象 | 对话产出里的 `theory_refs`、结论、画像字段值全部是占位串；`zhiyin-business` 与 `zhiyin-orchestration` 中**零处**引用 `knowledge` / `search` Gateway |
| 影响 | 《工作清单》4.5 要求"保证诊断与决策能通过关键词检索引用来源"未达成：检索组件与 `data/knowledge/` 数据都在（含中文二元切分、禁用来源过滤、命名空间拆分），但没有调用方，产品上等于"诊断不引用来源" |
| 归属 | 检索适配与知识数据 = 数据侧（已完成）；把检索结果接进 ②③ 产出 = 编排 / 业务侧 |
| 退出判据 | ②③ 的 `theory_refs` 至少有一条 `theory_id` 存在于 `data/knowledge/theory.json`；`test_open2_*` 由 xfail 变 XPASS 并删除标记 |
| 代码标记 | `infrastructure/local/knowledge.py` |

### OPEN-3 · Redis DB 1–6 六个域存储已装配、无消费方 —— 已闭合（2026-09-16）

| 项 | 内容 |
| --- | --- |
| 现象 | `build_gateways` 装配了 `redis_session` / `redis_schedule` / `redis_guard` / `redis_crawl` / `redis_knowledge` / `redis_vector_sync` 六个 `RedisDomainStore`，全部只放进 `container.extra`，仓库内**没有任何读取方**（`rg "redis_schedule"` 只有装配行） |
| 额外风险 | `RedisDomainStore` 与 `RedisCacheGateway` 不同，**没有降级兜底**：Redis 不可用时直接抛异常。下一个接线的人如果不知道这一点，会把"缓存降级可用"误当成"这六个域也降级可用" |
| 同类项 | 采集管线的 `raw_store`（原始响应进短期缓存 / DB 4）只在测试里注入 `RawStore` 假实现，生产装配未接 |
| 归属 | 数据侧（本期"基础能力可用"已达成；"被业务使用"未达成） |
| 退出判据 | 六个域至少各有一个真实调用方，或明确降级为"预留能力位"并在装配报告里如实标注（二选一，需记录决策） |
| 闭合决策 | 采用退出判据的第二种方式：DB 1–6 明确降级为**预留能力位**。Boot 只装配 `RedisClientFactory` 与有真实消费方的 DB 0 缓存；具体域由后续真实 Adapter / Worker 在出现调用方时通过 `domain_store(env, domain)` 惰性创建，不再把无人消费、无降级兜底的六个对象塞入 `container.extra`。分库映射、键规范和 TTL 规则继续保留，不代表六个域已经接入业务链路。 |
| 原始响应说明 | 采集管线 `raw_store` 仍是可选注入点；M3 生产采集 Runner 落地时才从工厂创建 `crawl` 域并注入。在此之前不虚构生产消费方。 |
| 代码位置 | `zhiyin-boot/zhiyin_boot/container/gateways.py` · `infrastructure/redis/__init__.py` · `infrastructure/crawl/pipeline.py` |

### OPEN-4 · Mock 门面成为死配置，且与新契约不同步 —— 已闭合（2026-09-19）

| 项 | 内容 |
| --- | --- |
| 现象 | `DefaultApplicationFacade` 已装配，`MockApplicationFacade` 的接线被整段注释；`settings.mock_facade` / `ZHIYIN_MOCK` 变成无效配置 |
| 连带问题 | 门面契约本轮由同步改为 `async`，但 `MockApplicationFacade` 仍是同步签名——重新打开 `ZHIYIN_MOCK=1` 会直接报错，而不是报"未实现" |
| 归属 | 接口 / 共享装配负责人 |
| 退出判据 | 删除死配置，或把 Mock 门面同步成 async 并补一条装配用例 |
| **闭合方式** | 采用**删除死配置**：删除 `zhiyin-api/zhiyin_api/facade/mock.py`、`Settings.mock_facade` 与 `ZHIYIN_MOCK` 读取、装配侧的注释块，并同步 `docs/开发指南.md` 与 `zhiyin-src/template/README.md` 的失效条目 |
| **为什么不复活它** | 决策 15=A 的前提是"Facade 未实现、前端无法联调"。真实 `DefaultApplicationFacade` 已实现并完整接线，前提不再成立；且本期口径是**不允许保留 Mock**，复活一个全靠 `NotImplementedError` 的替身与口径相悖 |
| 代码位置 | `zhiyin-boot/zhiyin_boot/container/__init__.py` · `zhiyin-boot/zhiyin_boot/settings.py` · `zhiyin-api/zhiyin_api/facade/mock.py`（已删除） |

### OPEN-5 · 服务级"骨架必须自报 skeleton"守卫已空转 —— 已闭合

| 项 | 内容 |
| --- | --- |
| 现象 | `test_shell_completeness.py` 的 `WIRED_SERVICE_PORTS` 被改成"全部 `SERVICE_SHELL`"，导致 `test_remaining_service_skeletons_declare_their_status` 的迭代集合为空——该守卫**一次都不执行**，未来任何服务退回骨架都不会被抓到（Worker 侧守卫仍有效） |
| 归属 | 数据侧 / 测试维护方 |
| 闭合情况 | 已在 `business-tao@dfd7f34` 闭合：空转的守卫被换成对**全部** `SERVICE_SHELL` 参数化的 `test_service_declares_valid_status`，断言每个服务能力位如实声明 `skeleton` 或 `wired`；同时 `test_first_phase_is_wired_and_later_worker_stays_pending` 改为用 `WIRED_SERVICE_PORTS` / `WIRED_WORKER_PORTS` 常量断言装配结果。守卫恢复为非空集，原来的 `TODO(第一期未闭合)` 标记按其触发条件被删除 |
| 遗留 | 该守卫断言的仍是"状态合法"，不是"状态与预期一致"；能力位增减时仍需人工同步 `WIRED_SERVICE_PORTS` |

### OPEN-6 · 决策 5 的画像口径没有在工作台生效，且规则被重复实现 —— 未闭合

| 项 | 内容 |
| --- | --- |
| 现象 | `business-tao@dfd7f34` 新增 `policies/profile.py` 按决策 5 计算"关键字段的整体置信度（等权平均）"，但该结果只经 `ProfileService.overall_confidence` 暴露，生产路径**没有调用方**；工作台面板的取值仍由 `zhiyin-api/zhiyin_api/dto/mappers.py::workspace_page_view` 内联计算：`overall_confidence = Σ(全部字段 confidence) / 字段数`、`coverage = 字段数 / (字段数 + 缺口数)` |
| 影响 | 决策 5 的口径（关键字段覆盖 80% + 置信度 ≥ 0.7；缺口 < 0.6）在产品上看不到效果；同一口径在两处实现，会随任一侧修改而漂移；业务规则写在 API 层，与"Mapper 只做形状映射、API 层不写业务判断"的分层要求相悖 |
| 归属 | 业务侧提供算法（已完成）+ 接口侧收敛取值路径；`mappers.py` 是 `AGENTS.md` §11.2 的共享写点，`WorkspaceView` / `ProfileService` 是冻结契约，需先协调再改 |
| 退出判据 | 工作台面板的覆盖率与整体置信度由业务层按 `policy_params.profile_collection` 计算并透传，`mappers.py` 只做映射；两处公式收敛为一处；口径措辞（决策记录写"加权平均"、实现为"等权平均"）需拍板并在 `policy_params` 里给出权重或改正文 |
| 代码标记 | `zhiyin-business/zhiyin_business/policies/profile.py` |

---

## 二、Mock 内容标注

### MOCK-1 · 后端未透出"内容来源"标记，前端标注组件无法工作 —— 未闭合

| 项 | 内容 |
| --- | --- |
| 现状 | 仓库已有一套 Mock 标注设计：`zhiyin-web/src/components/common/MockBadge.vue`（自述"第二期接真实模型后，**由后端把来源标记为 real**，本组件自动不渲染"）+ 文案资源 `data/registry/copies.json:mock.source_notice` |
| 缺口 | 后端任何 DTO 都没有来源字段（`rg "is_mock\|source" zhiyin-api` 无结果），前端只能靠**字符串匹配占位文案**才能判断，这既脆弱又会随文案改动失效；而且 `MockBadge.vue` 自身仍是空骨架 |
| 归属 | 后端接口契约 + 前端联调（需一次契约评审，会改动 `contracts/openapi.json` 与前端生成物 `types.ts`） |
| 退出判据 | 响应中出现可机器判定的来源标记；`test_mock_content_carries_*` 由 xfail 变 XPASS 并删除标记 |
| **2026-09-19 收尾** | 前端 `MockBadge.vue` 与文案键 `mock.source_notice` 已删除；对应的 `xfail(strict=True)` 用例与 `phase1_open` 标记**按本清单的清理约定一并删除**——Mock 产出已归零，该断言不再有可标记的对象，留着只是永久失效的守卫。证据见[修改日志](../00-索引与变更/职引-数据全链路修改日志.md)第十四节 |

### MOCK-2 · Mock 内容已经流到用户可见字段（现状存档，不是缺陷）

占位串单点定义在 `infrastructure/local/llm.py::_PLACEHOLDER_TEXT`（这一点做得对，没有散落硬编码）。
实测它**已经出现在以下用户可见位置**，因此 Mock 标注不是"锦上添花"，而是防止演示被误读的必要手段：

| 用户可见位置 | 实测内容 |
| --- | --- |
| 对话消息正文 | `messages[].text` = 占位串 |
| 主理徽标 / 理论引用 | `badge.theory_refs[].theory_id/name/stage` = 占位串 |
| 行为引导 | `guide.text`、`guide.options[].option_id/label` = 占位串 |
| 画像字段 | `ProfileField.value`（进而让画像覆盖度、工作台 ① 层显示占位内容） |
| 工作台依赖图 | `dependencies[].from_asset` / `via_profile_keys` = 占位串 |

> 说明：Mock 模型本身是**全仓既有状态**（`main` 上 `local/llm.py` 未改动），不是本分支引入；
> 本分支引入的变化是：此前 `/app/*` 全部返回 503，现在会把这些占位内容真的送到前端。

---

## 三、比对他第一期（M2）自评的核验结论

《完成情况记录》中可核验的数字**全部属实**（见第四节）。差异只出现在"完成"的**范围口径**上：

| 他的声明 | 核验结论 |
| --- | --- |
| M1 已完成 100% | ✅ 属实 |
| M2 已完成（本人范围）100% / 三波 100% | ✅ 当前属实：OPEN-1 / OPEN-2 已随 service 合并接入编排主链，OPEN-3 已按“预留能力位”决策闭合；正式 E2E 已覆盖资产正文落库与知识引用 |
| 装配 39 wired / 1 skeleton / 3 not_wired（43 个能力位） | ✅ 实测完全一致 |
| 297 passed / 1 skipped；真实 Redis 13 passed；M2 门禁通过 | ✅ 实测完全一致 |
| 契约 / 装配改动 | ⚠️ 按他自己的《开发须知》§11.1，新增或改变跨层契约方法应先升级确认；本轮向 Port 新增了抽象方法（`AssetRepository.save_snapshot`、`ConversationMemoryRepository.compare_and_swap`、`ObjectStoreGateway.compare_and_swap` + `StoredObject.etag`、`AssetService.save_*`、`StagePanel.task_id/lead_agent`），决策记录里只有 DEC-DATA-003（不新增能力位），没有"新增契约方法"的评审条目 |

---

## 四、复核证据（可复现）

在分支 `data-yuan@93f85f3` 的干净检出下执行：

| 命令 | 实测结果 |
| --- | --- |
| `python -m pytest -q` | 297 passed, 1 skipped（`main` 基线为 265 passed, 7 skipped） |
| `python -m ruff check .` | All checks passed |
| `python scripts/export_openapi.py --check` | 快照一致（HTTP 契约未变） |
| `python -m zhiyin_boot --check --phase=1 / =2` | `passed=true, unmet=[]`（M2 通过） |
| `ZHIYIN_TEST_REDIS_URL=redis://127.0.0.1:6379 python -m pytest tests/test_redis_first_phase.py -q` | 13 passed（真实实例，DB 0–6/15） |
| `git merge --no-commit --no-ff origin/data-yuan`（在 `main` 上） | Automatic merge went well（零冲突，可快进） |
| 五环节 HTTP 冒烟（`/app/bootstrap` → `/task/enter` → `/conversation/message` ×5 → `/workspace` → `/report/full-text`） | 环节路由与换主理告知正常；报告全文 404（OPEN-1）；工作台 ②③④ 均为占位（OPEN-1）；依赖图为占位串（MOCK-2） |
| Redis 指向死端口（`redis://127.0.0.1:6399`）冒烟 | 接口仍 200，耗时 4–6ms，降级到内存缓存（容错合格） |

---

## 五、2026-09-19 补充：MOCK-1 / MOCK-2 因清除 Mock 而失去对象

本轮按「不允许保留 Mock」把真实模型接通，并清除了数据库中的 Mock 沉淀数据。实测结论：

| 项 | 本轮事实 | 状态 |
| --- | --- | --- |
| MOCK-2（占位串流到用户可见字段） | 五环节真实端到端跑通后，`/app/bootstrap`、`/app/workspace`、`/app/report/full-text`、会话列表全部**零占位串**；报告正文、画像字段、依赖图均为真实模型产出 | 已消除 |
| MOCK-1（后端无机器可判的来源标记） | 触发前提是"存在 Mock 产出需要被标注"。Mock 产出已归零，来源标记失去对象；`LocalOrMockLLM` 仍保留为本地/测试实现，但其占位路径在部署环境不再被使用 | 失去对象（未做契约变更） |

随之暴露的两条新缺陷与修复（详细证据见[修改日志](../00-索引与变更/职引-数据全链路修改日志.md)第五节）：

1. **五环节此前没有任何提示词**：`ContractAgentEngine` 未配置 system_prompt，模型只收到 `【输入变量】/【共享状态】` 裸 JSON 与输出 Schema，采集环节自造画像字段名，六个关键字段永远覆盖不到。Mock LLM 是按 Schema 机械合成占位串的合成器，因此该缺陷在 Mock 期间**不可能**被任何门禁或测试发现。
2. **PAMI Agent 应用未设输出上限**：`diagnose` / `act` 的 JSON 被截断在对象中途（实测分别停在 `"index": 5, "name": "` 与 `"calendar_synced": false`），契约校验失败后回落成通用兜底文案，报告与行动计划因此从未落库。显式设置 `maxTokens=8192` 后消失。

> 前端仍存在**硬编码演示数据**（工作台日历/成就、报告页正文与导出、智能体 15 维分数、对话页三栏初始值等）。那属于前端展示层与 Mock 模型产出两条不同的问题线，逐字段清单见[前端字段真实性清单](职引-前端字段真实性清单-v1.0.md)，不因 MOCK-1/MOCK-2 失去对象而自动关闭。

### 5.1 前端展示层清理结果（2026-09-19 同日收口）

上面那条"前端仍存在硬编码演示数据"已完成：

- 四个 store（`conversation` / `workspace` / `session` / `agents`）不再预置任何演示状态，加载失败只暴露错误并保持空态；
- 删除前端臆造的 15 维解析（后端报告只有维度名/标签/结论/证据，没有任何 0-100 分值）；
- 工作台与报告页改为真实数据驱动，无数据即空态；报告导出走真实 `POST /app/assets/export` 并如实显示 `available=false`；
- 删除死组件 `MockBadge` / `MessageCenter` / `GrowthShareCard`；
- 首页去演示化（删除编造的产出样例、内嵌假对话、假画像覆盖度与"示例数据声明"）。

字段级依据与复核脚本见[前端字段真实性清单](职引-前端字段真实性清单-v1.0.md)；逐项改动证据见[修改日志](../00-索引与变更/职引-数据全链路修改日志.md)第八节。该清单的第十二节仍列着**需要契约评审**的四项（后端来源标记、前端阈值下沉、15 维来源统一、画像口径三处收敛）——前三项在真实模型接通与展示层清理后已不再阻塞，最后一项已随 OPEN-6 收敛完成。

---

### MOCK-3 · **检索内容本身仍是演示卡**，且被门禁算作已接线 —— 已上报并加护栏（2026-09-19 追加）

MOCK-1/MOCK-2 失去对象说的是"**模型产出**不再有占位串"。这不等于系统里没有 Mock 内容：
**检索知识的语料**是另一条线，它此前没有被这份清单覆盖。

| 项 | 内容 |
| --- | --- |
| 现象 | 线上容器真实的关键词通道是 `LocalSearchGateway`，它读 `data/knowledge/*.json`；该批卡片自述为 DEMO（`theory.json` 的 `_note`、`sources.json` 里 3 条来源名带"（演示数据）"） |
| 实测存量 | 向量库 `zhiyin_vectors` **0 行**；权威文档表 `retrieval_document` **0 行**；本地知识库仅 `occupation` 3 + `theory` 3 = **6 条**（全部 DEMO），其余 4 个 namespace 是空文件 |
| 为什么门禁没发现 | 相位门禁问的是"`search` 能力位有没有装配"，而 `LocalSearchGateway.IMPLEMENTATION_STATUS = "wired"` → phase 3 照常 `passed=true`；`/healthz` 也显示 `status=ok, placeholders=[]`。**"实现装上了"与"内容是真的"是两条不同的轴** |
| **⚠️ 触发条件的实测修正** | "报告引用了演示卡"是**通道层**的可能，不是当前线上事实：真实装配的 `search` 因权威表为空，在 `hydrate()` 阶段把**全部**命中丢弃，所以线上是**检索恒空**而非引用演示卡。两个问题都要修：演示内容要可识别（本项），静默丢弃要可观测（另见 D13） |
| 归属 | 平台侧（RAG 检索缺 rerank）+ 内容侧（理论卡/来源台账待定稿）+ 检索侧（D13） |
| 退出判据 | 向量库与权威文档表有真实内容；演示内容在装配报告与响应里**可识别**且不得成为报告出处 |
| 决策登记 | [待决问题 D12](职引-待决问题与改法选项-v1.0.md)（用户选 A，**已落地**：`/healthz` 如实降级、命中带 `demo` 标、引用核对拒绝演示证据、应答给出提示） |
| **⚠️ 2026-09-19 复查补记（重要）** | 切到 PAMI 检索后，装配期信号**一度失效**：`/healthz` 报 `ok`、`demo_content=[]`，而权威表 22 行**全是 `demo=true`**——原因是该信号只问检索通道实现，而本地通道已退出链路。**已修**：改为查**内容的权威来源**（`RetrievalDocumentStore.demo_namespaces()`），并在查不出来时记 `demo_content_unknown=True`（"不知道"不等于"干净"）。现 `/healthz` = `degraded` + `demo_content=["search"]` + `demo_namespaces=["occupation","theory"]`。详见[修改日志 §28](../00-索引与变更/职引-数据全链路修改日志.md) |
| 当前状态 | **已上报并加护栏**；"内容为空"本身仍待真实内容（D7） |

证据与复现命令见[修改日志 §20/§22](../00-索引与变更/职引-数据全链路修改日志.md)与[检索质量基准 §六](职引-检索质量基准-2026-09-19.md)。

---

## 六、清理约定

1. 修好某项后：删除 `tests/e2e/test_phase1_open_items.py` 中对应 xfail，把目标行为迁移为正式回归，并把本文状态改为“已闭合”。归属方文件中若仍保留历史 TODO，应由对应负责人复核后清理，避免跨负责人顺带修改实现文件。
2. `tests/e2e/test_phase1_open_items.py` 里的用例是 `xfail(strict=True)`：**修好后它们会变红（XPASS）**，这是故意的提醒，不是回归。
3. 本文只做标记与核验，不改动任何业务逻辑；原始自评文档不改写。
