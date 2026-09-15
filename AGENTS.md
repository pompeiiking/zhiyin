# AGENTS.md

本文件适用于整个仓库。所有智能体在阅读、规划、实现、测试和评审本项目时都必须遵守。

## 1. 开始工作前

1. 先阅读与任务直接相关的文档和现有实现，不凭目录名或记忆猜测。
2. 当前状态以 `docs/评审/职引-架构与结构评估-最终版.md` 为准。
3. 业务规则以 `docs/评审/业务口径决策记录-v1.0.md` 为准。
4. 文件落位与依赖约束以 `docs/开发指南.md` 为准。
5. 接口签名以实际 Port、DTO 和 `contracts/openapi.json` 为事实来源。旧设计文档中的示例签名或示例路径不能覆盖现有代码契约。
6. 开始修改前先检查工作树状态、相关测试、现有骨架和文件顶部说明，保留用户已有的未提交修改。

## 2. 不确定时先问

出现下列情况时，必须先向用户说明发现的事实、冲突和建议方案，得到确认后再修改代码：

- 文档、代码、OpenAPI、测试或动态资源之间互相矛盾；
- 现有接口缺少完成任务所需的参数、返回值、事件载荷或依赖；
- 需求会改变冻结的 Port、共享模型、枚举、DTO、公开 API 或数据库语义；
- 需求需要修改共享写点、其他成员负责的文件或任务范围以外的模块；
- 现有设计明显不合理、会造成越层依赖、重复契约、静默降级或数据不一致；
- 需要新增抽象、公共目录、跨层通道、事件类型、配置项或能力位；
- 无法判断某文件是生成物、当前实现还是历史骨架；
- 需要进行破坏性操作、迁移、批量改名或改变既有兼容行为。

不要通过猜测、临时兼容层、硬编码、复制模型或放宽架构守卫来绕过不确定性。未经确认，不修改相关代码。

## 3. 仓库与文件结构

工程代码位于 `zhiyin-src/template/`，保持以下结构和职责：

| 位置 | 职责 | 允许依赖 |
| --- | --- | --- |
| `zhiyin-kernel/zhiyin_kernel/` | 跨层共享数据形状、枚举、零依赖最小契约 | 仅自身 |
| `zhiyin-api/zhiyin_api/` | Controller、DTO、Mapper、Facade、统一响应 | `zhiyin_business`、`zhiyin_kernel` |
| `zhiyin-business/zhiyin_business/ports/` | 冻结的业务能力接口和读模型 | 本包 ports、kernel |
| `zhiyin-business/zhiyin_business/policies/` | 可独立测试的纯业务规则 | policies、ports、kernel |
| `zhiyin-business/zhiyin_business/services/` | 业务 Port 的具体实现和流程组织 | policies、ports、orchestration、data-sdk、kernel |
| `zhiyin-business/zhiyin_business/workers/` | 业务规则驱动的异步执行者 | 业务 Port、规则、kernel Worker 契约 |
| `zhiyin-orchestration/zhiyin_orchestration/` | Agent、Workflow、EventBus、Schedule、State、Notify 六类通用原语 | data-sdk、kernel |
| `zhiyin-data-sdk/zhiyin_data_sdk/` | Repository、Gateway、Transaction 抽象；不放实现 | kernel |
| `zhiyin-infrastructure/zhiyin_infrastructure/` | local、MySQL、Redis、Kafka、pgvector、pami 等具体适配器及纯数据 Worker | data-sdk、kernel |
| `zhiyin-boot/zhiyin_boot/` | 唯一装配层、运行驱动、装配报告和门禁 | 全部包 |
| `data/registry/` | 动态内容、智能体、任务入口、契约、功能开关、规则参数和归属清单 | 不写业务代码 |
| `contracts/` | 由后端导出的 OpenAPI 契约快照 | 生成物 |
| `tests/` | 架构守卫、落位守卫、Port 契约测试、单元测试和 e2e | 与被测范围一致 |

业务包内部方向固定为：

```text
services → policies → ports → kernel
```

禁止 ports 依赖 policies 或 services，禁止 policies 依赖具体 Service。

新增文件前使用以下落位顺序，第一个命中项即为归属：

1. 跨层共享的枚举、数据形状或零依赖最小契约：`zhiyin_kernel`。
2. 外部能力抽象：在 `zhiyin_data_sdk` 定义契约，在 `zhiyin_infrastructure` 实现。
3. 与职引无关的 Agent、事件、调度、状态、通知或通用流程：`zhiyin_orchestration`。
4. 职引业务规则：`zhiyin_business/policies/`。
5. 职引业务服务实现：`zhiyin_business/services/`。
6. 业务规则驱动的后台执行：`zhiyin_business/workers/`；纯数据管道进入 `zhiyin_infrastructure/workers/`。
7. HTTP、DTO、Mapper、Facade：`zhiyin_api`。
8. 依赖选择和对象装配：`zhiyin_boot/container/`。

不得新建 `utils`、`common`、`helpers`、`shared` 等含义模糊的通用杂物包。确需复用时，先判断其真实职责并放入已有明确模块；仍无法归属时先询问。

## 4. 契约唯一归属

- 共享数据形状和跨层枚举只定义在 `zhiyin_kernel`。
- Repository、Gateway、Transaction 只定义在 `zhiyin_data_sdk`，其公开 IO 方法一律 `async`。
- EventBus、Scheduler、Notifier、State、Agent、Workflow 的语义契约只定义在 `zhiyin_orchestration`。
- 五环节 `CollectOutput`、`DiagnoseOutput`、`DecideOutput`、`ActOutput`、`ReviewOutput` 只定义在 `zhiyin_business/contracts/`。
- 业务 Service 接口只定义在 `zhiyin_business/ports/`，实现放在 `services/`。
- API View DTO 只定义在 `zhiyin_api/dto/`，业务形状到 View 的映射只放在 `zhiyin_api/dto/mappers.py`。

同一能力、模型、枚举或事件抽象不得在两个位置重复定义。生产方和消费方必须引用同一个模型，不能各复制一份字段相同的类。

Pydantic 契约默认 `extra="forbid"`。不要为了吞掉未知字段而私自改成允许额外字段。

## 5. 冻结接口与实现规则

`zhiyin_business/ports/`、`zhiyin_data_sdk/repositories/`、`zhiyin_data_sdk/gateways/`、`zhiyin_orchestration` 六原语契约及 `zhiyin_kernel` 公共形状均视为冻结接口。

- 实现任务默认只填写现有骨架的方法体，不改变公开方法名、参数、返回类型、类名和模块路径。
- 确需修改冻结接口时，先询问并说明调用方、实现方、测试、OpenAPI、前端类型和兼容性影响。
- 业务层通过构造函数接收 Repository、Gateway 包装后的语义原语及其他 Port，不自行创建具体基础设施实现。
- `zhiyin-boot/container/` 是唯一决定使用哪套实现和进行装配的位置。
- 骨架必须如实声明 `IMPLEMENTATION_STATUS = "skeleton"`，未完成时不得装配为已实现能力；完成后的状态、装配表、守卫和测试必须协调更新。
- 未配置或未实现的能力必须明确失败或明确降级，不得静默返回伪成功。

## 6. 业务编排与黑板规则

### 6.1 Profile Service

`DefaultProfileService` 只负责画像活状态读写和事件发布：

- 实现冻结的 `ProfileService` 方法：`get`、`get_fields`、`get_gaps`、`update_field`、`replace_gaps`、`overall_confidence`；
- 只通过 `ProfileRepository` 访问数据；
- `update_field` 成功后必须发布 `profile_field_updated`；
- 不直接调用 Asset Service，不直接执行影响面重算；
- 不包含采集话术；
- 置信度必须在 `0..1` 范围内。

采集口径来自动态规则参数：关键字段覆盖率达到 80% 且整体置信度不低于 0.7 才完成；未覆盖或置信度低于 0.6 的关键字段属于缺口。不得在 Service、Policy 或 `Settings` 中重复硬编码这些阈值。

### 6.2 Behavior Service

`DefaultBehaviorService` 只负责行为日志追加、查询、时间计算和事件发布：

- 实现冻结的 `BehaviorService` 方法：`log`、`recent`、`days_since_last`；
- 只通过 `BehaviorRepository` 访问数据；
- 行为日志只追加，不得提供修改历史记录的路径；
- `recent` 按时间倒序；
- 从未发生指定行为时，`days_since_last` 返回 `None`；
- 写入成功后必须发布 `behavior_logged`。

停滞和成就只能由真实行为事件驱动，纯浏览、登录或页面停留不能伪装成有效行动。

### 6.3 Orchestrator

`DefaultOrchestrator` 只做装配式编排：读黑板、调用规则、执行能力、统一写回并发布事件。不得在类内内联业务规则。

必须实现冻结的 `Orchestrator` 方法：

- `read_blackboard`
- `detect_intent`
- `detect_stage`
- `infer_axis_a`
- `select_lead`
- `handoff`
- `handle_message`

编排顺序保持：

```text
读黑板 → 识别意图 → 判定环节 → 推断轴 A → 选择主理 → 执行产出 → 写回黑板/事件 → 行为引导收尾
```

业务要求：

- 判定不确定时温和澄清一次，仍不确定则回落采集，不得猜测并强行跳转；
- 轴 A 为五段单轨，任务会话可携带就业、考研、留学路径焦点；前台不得让用户自行选择轴 A；
- 主理、协理、理论包和产出契约来自动态 Registry，不得硬编码 agent id；
- 产出契约的唯一查找键是 `(agent_id, stage)`，不是契约 id；
- 所有环节进入前先读同一黑板；
- 前序资产自动继承，支持从任意环节进入和跨会话续接；
- 长内容不进对话流，消息只包含最短结论；
- 换主理、换理论或结论变化必须返回 `Disclosure`；无变化时 `Disclosure` 保持 `None`，不得用空字符串或默认文案代替；
- 每轮必须返回 `BehaviorGuide`，类型只能是追问、选项、小任务或提醒；
- 导师建议仅作线索，不自动触发资产重算；
- 画像影响面只重算命中的资产片段，版本加一并写 diff，禁止整篇重新生成。

### 6.4 Policies

- `routing.py`：只回答意图和目标环节。
- `teaming.py`：只回答主理、协理和是否需要信息侦查员。
- `handoff.py`：只回答是否交接以及显式告知。
- `impact.py`：只选择受影响资产，不执行重算。
- `intervention.py`：只判断是否允许干预，不发送通知。

策略只依赖 Port、Kernel 和动态参数，不依赖具体 Service。规则参数统一从 `data/registry/policy_params.json` 获取；缺失时显式处理，不得静默编造默认值。

## 7. 事件规则

- 业务模块之间优先通过 `zhiyin_orchestration.EventBus` 发送 `DomainEvent`，发布方不得了解订阅方的私有实现。
- 业务层不得直接调用传输层 `EventBusGateway`。
- `DomainEvent` 使用统一信封：`event_id`、`event_type`、`occurred_at`、`payload`、`trace_id`、`idempotency_key`。
- 业务事件名称和载荷集中在 `zhiyin_business/events.py`；禁止在业务代码中散写魔法字符串。
- 已有事件包括 `profile_field_updated`、`asset_version_changed`、`loop_stage_changed`、`behavior_logged`、`task_stall_detected`。
- 新增事件或改变事件载荷属于契约变更，必须先询问并同步订阅方、测试和文档。

当前 `behavior_logged` 尚无独立 Payload 模型。实现前必须先确认统一载荷形状，不能由发布方与订阅方各自猜测。

## 8. 动态资源与配置

以下内容不得硬编码到 Python、Vue、HTML 或 `Settings`：

- 菜单、路由、任务入口、文案、横幅、信任块、FAQ；
- 智能体、理论卡、产出契约、提示词、工作流模板；
- 功能开关、规则参数、通知模板、负责人归属；
- 停滞阈值、冷却期、打扰上限、画像覆盖率和置信度阈值。

第一期从 `data/registry/*.json` 读取；后续替换为数据库时保持接口不变。动态资源之间的引用必须闭合：agent、theory、task entry、output contract 的引用不能悬空。

主动干预现行参数为停滞 3 天、冷却 48 小时、7 天最多 2 次，但实现必须读取 `policy_params.json`，不能复制为代码常量。

## 9. API 与前后端契约

真实接口以 Controller 和 `contracts/openapi.json` 为准。当前公开路径：

- `GET /api/v1/app/bootstrap`
- `GET /api/v1/app/sessions`
- `POST /api/v1/app/task/enter`
- `POST /api/v1/app/conversation/message`
- `GET /api/v1/app/workspace`
- `GET /api/v1/app/assets/{asset_type}/versions`
- `GET /api/v1/app/report/full-text`
- `POST /api/v1/app/assets/export`
- `POST /api/v1/app/track`
- `GET /healthz`

统一响应信封为 `code`、`message`、`data`、`trace_id`。Controller 只接参数、调 Facade、包信封，不写业务判断。

`/api/v1` 只允许在 `zhiyin_api.app.create_app()` 中统一拼接：

- Controller 路由只写 `/app/...`；
- 前端 base URL 使用 `/api/v1`，endpoint 只写 `/app/...`；
- 代理和网关原样转发，不重复添加版本段；
- `/healthz` 是唯一位于版本命名空间之外的端点；
- 第一期不做 SSE/WS，不新增流式端点。

API 层不得 import `zhiyin_data_sdk`。API 需要身份时通过 `IdentityService`，需要菜单、路由、文案、任务入口或功能开关时通过 `RegistryService`。

Facade 只组织业务调用并把结果交给 Mapper，不直接访问数据库、模型、知识库或鉴权 Gateway，不直接构造 View DTO。

## 10. Trace、错误与安全

- `X-Trace-Id` 只能由 `zhiyin_api/context.py` 的请求上下文中间件生成或沿用上游合法值。
- Controller、Facade、业务层和编排层不得再生成自己的 trace id。
- 业务层抛业务异常，不暴露底层数据库或驱动异常。
- Data Access SDK 负责统一包装数据库、检索和对象存储错误。
- 降级必须可识别，不得将失败静默伪装为成功。
- 第一阶段只使用 DEMO、脱敏或本地测试数据，禁止提交真实手机号、身份证、简历及其他敏感信息。
- API Key、JWT、数据库连接串等秘密不得写入代码、动态资源、日志、URL、测试快照或提交记录。
- 职引侧不得自行修改 `docs/技术架构文档/外部平台/pami-Wanwu/` 所描述的平台契约；未提交或未验证的平台能力不能视为可用的冻结接口。

## 11. 不能直接修改的文件

### 11.1 生成物：禁止手改

- `zhiyin-src/template/contracts/openapi.json`
- `zhiyin-src/template/zhiyin-web/src/api/types.ts`

接口字段变更只走：

```text
后端 DTO / Mapper
→ python scripts/export_openapi.py
→ cd zhiyin-web && npm run gen:api
```

发生生成物冲突时重新生成，不手工合并。

### 11.2 团队共享写点：先协调负责人

- `zhiyin-src/template/zhiyin-boot/zhiyin_boot/container/ports.py`
- `zhiyin-src/template/zhiyin-business/zhiyin_business/services/__init__.py`
- `zhiyin-src/template/zhiyin-api/zhiyin_api/dto/mappers.py`
- `zhiyin-src/template/data/registry/ownership.json`
- `zhiyin-src/template/contracts/openapi.json`
- `zhiyin-src/template/zhiyin-web/src/api/types.ts`

这些文件是已知并行冲突点。除生成物始终禁止手改外，其他文件需要变更时先说明原因、影响和具体改动，请用户或共享文件负责人确认。

`zhiyin-boot/zhiyin_boot/container/services.py` 也是集中装配热点。服务实现者完成方法体后，不应在没有协调的情况下自行接线；装配状态、`IMPLEMENTATION_STATUS`、装配表和相关守卫应作为一个一致变更处理。

## 12. 已知漂移与实现前检查

- `services/orchestrator.py` 顶部仍写着四项口径未定、规则参数为 draft；该说明已过期。业务决策记录和 `data/registry/policy_params.json` 均已标记 confirmed。
- 旧接口设计文档中的 `/zhiyin/api/...` 只是历史示例，真实接口统一为 `/api/v1/...`。
- `Orchestrator.infer_axis_a()` 已冻结，但当前 `policies/` 没有独立的阶段推断 Policy，构造函数也没有该依赖；不得在 Orchestrator 中悄悄内联规则或私自新增契约，开始实现前先确认处理方式。
- `behavior_logged` 尚无独立 Payload 模型；实现发布和订阅前先确认载荷契约。
- 当前部分落位守卫仍断言业务类为 skeleton；能力完成后必须协调更新状态、装配和守卫，不能只删除 `NotImplementedError`。

## 13. 验证要求

修改必须配套最小充分测试。实现 Repository 或 Gateway 时，同一套 Port 契约测试必须能覆盖本地实现和后续真实实现。

提交前从 `zhiyin-src/template/` 运行：

```bash
python -m pytest -q
python -m ruff check .
python -m zhiyin_boot --check --phase=1
python scripts/export_openapi.py --check
```

涉及前端或 API 契约时再运行：

```bash
cd zhiyin-web
npm run typecheck
npm run check:api
```

M2 业务主干完成时还必须通过：

```bash
python -m zhiyin_boot --check --phase=2
python -m pytest tests/e2e -v
```

不得通过删除测试、放宽断言、增加无条件 skip、伪造装配状态或隐藏错误来让门禁变绿。

