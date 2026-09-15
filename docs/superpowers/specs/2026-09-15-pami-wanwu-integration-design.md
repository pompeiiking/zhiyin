# 职引内置 pami/Wanwu 基础平台接入设计

| 项 | 内容 |
| --- | --- |
| 日期 | 2026-09-15 |
| 状态 | 待用户评审 |
| 目标 | 将 pami/Wanwu 完整源码纳入职引交付，在不破坏现有分层的前提下打通后端调用、资源部署与统一发布 |
| 依据 | 职引目标架构、分层设计、Wanwu 真实 API 契约与实测报告 |

## 1. 结论

采用“单仓库、双系统、统一发布”的方式：

- Wanwu 完整源码作为职引内置平台源码放在 `platform/wanwu/`，保持自身 Go、Python、Vue 和微服务边界；
- 职引仅通过 `zhiyin-infrastructure/pami/` 调用 Wanwu，不允许业务层直接引用 Wanwu 源码、DTO、数据库或凭据；
- 职引后端通过控制面 API 在 Wanwu 中创建、配置和发布知识库、RAG、智能体与工作流，通过运行面 API 执行这些资源；
- 对外只暴露职引的 `/api/v1/*` 产品接口，Wanwu 管理接口只在内部网络可访问；
- 职引与 Wanwu 由同一套 Compose/后续 Helm 配置构建、启动、健康检查和升级。

这能满足“pami 平台接到代码里、接口打通、后端可调用、后续可在其上部署”的目标，同时保留职引现有的分层守卫与替换能力。

## 2. 范围

### 2.1 本次包含

1. 导入可追溯的 Wanwu 完整源码快照；
2. 建立 Wanwu 控制面和运行面 HTTP Client；
3. 打通知识库、RAG、智能体、工作流和平台健康检查；
4. 支持职引资源代码与 Wanwu 资源 ID/API Key 的映射；
5. 将 pami Adapter 接入 `zhiyin-boot` 装配与健康报告；
6. 由 `zhiyin-api` 暴露职引语义接口；
7. 提供统一 Docker Compose 部署、初始化和就绪检查；
8. 建立单元、契约、集成和部署冒烟测试。

### 2.2 本次不包含

- 不把 Wanwu 改造成 Python 库并塞入职引 FastAPI 进程；
- 不允许 `zhiyin-business` 直接调用 Wanwu；
- 不直接读写 Wanwu MySQL 业务表；
- 不把 Wanwu 的全部管理接口无差别代理到公网；
- 不在首期承诺已知不稳定能力：子组织启停、资源成员授权写入、Python 单节点调试、工作流静态 Token；
- 不在首期建设 Kubernetes 高可用，先交付可重复的单机 Compose 拓扑。

## 3. 总体架构

```text
Browser / 第三方调用方
          |
          | HTTPS /api/v1/*
          v
+---------------------------+
| zhiyin-api                | 公开接口、DTO、trace_id、统一错误
+-------------+-------------+
              |
              v
+---------------------------+
| zhiyin-business           | 职业引导规则、资源部署用例、业务服务
+-------------+-------------+
              |
              v
+---------------------------+
| zhiyin-orchestration      | Agent/Workflow/Event/Schedule 语义原语
+-------------+-------------+
              |
              | zhiyin-data-sdk Ports
              v
+---------------------------+
| zhiyin-infrastructure     |
| pami control/runtime      | 协议转换、鉴权、重试、错误映射、审计
+-------------+-------------+
              |
              | 内部 HTTP
              v
+-------------------------------------------------------------+
| platform/wanwu                                              |
| Nginx/BFF -> IAM/Model/MCP/Knowledge/RAG/Assistant/App       |
|            -> AgentScope/RAG Engine/Python Agent             |
+-----------------------------+-------------------------------+
                              |
                              v
              MySQL / Redis / MinIO / Kafka / Elasticsearch
```

### 3.1 依赖边界

保留现有依赖矩阵：

| 模块 | 可依赖 |
| --- | --- |
| `zhiyin_kernel` | 仅自身 |
| `zhiyin_data_sdk` | `kernel` |
| `zhiyin_orchestration` | `kernel`、`data_sdk` |
| `zhiyin_infrastructure` | `kernel`、`data_sdk` |
| `zhiyin_business` | `kernel`、`data_sdk`、`orchestration` |
| `zhiyin_api` | `kernel`、`business` |
| `zhiyin_boot` | 全部职引模块 |

`platform/wanwu` 是独立构建单元，不加入 `pyproject.toml` 的 Python 包清单。职引与 Wanwu 的代码边界以 HTTP 契约为准。

## 4. 目标目录

```text
zhiyin/
|-- platform/
|   `-- wanwu/                         # Wanwu 完整、可追溯的源码快照
|       |-- UPSTREAM.md                # 上游仓库、提交号、导入日期、补丁清单
|       |-- LICENSE
|       |-- cmd/ internal/ proto/ api/
|       |-- agent/ web/ configs/
|       `-- Dockerfile.*
|
|-- zhiyin-src/template/
|   |-- zhiyin-data-sdk/zhiyin_data_sdk/
|   |   |-- gateways/pami_runtime.py   # Agent/RAG 运行面契约
|   |   `-- gateways/pami_control.py   # 知识/Agent/RAG/Workflow 控制面契约
|   |
|   |-- zhiyin-infrastructure/zhiyin_infrastructure/pami/
|   |   |-- client.py                  # 共享 HTTP、连接池、trace、响应信封
|   |   |-- credentials.py             # JWT/API Key 提供者
|   |   |-- errors.py                  # Wanwu 错误映射
|   |   |-- dto.py                     # 仅本包可见的 Wanwu DTO
|   |   |-- control.py                 # 控制面 Client
|   |   |-- runtime.py                 # 运行面 Client
|   |   |-- knowledge.py
|   |   |-- rag.py
|   |   |-- agent.py
|   |   |-- workflow.py
|   |   |-- auth.py
|   |   `-- health.py
|   |
|   |-- zhiyin-boot/zhiyin_boot/container/
|   |   |-- ports.py
|   |   `-- gateways.py
|   `-- tests/
|       |-- contracts/
|       |-- integration/pami/
|       `-- e2e/
|
`-- deploy/
    |-- docker-compose.yml
    |-- docker-compose.pami.yml
    |-- .env.example
    |-- nginx/
    `-- scripts/
        |-- bootstrap-pami.ps1
        `-- readiness-check.ps1
```

源码导入不得包含 `.git`、`.env`、缓存、日志、PID、测试结果和运行输出。Apache 2.0 `LICENSE`、NOTICE/版权信息及本地修改说明必须保留。

## 5. Port 设计

现有 `LLMGateway` 继续表达“原始模型调用”，不把 Wanwu 智能体强行伪装成普通 LLM。新增以下平台能力契约：

### 5.1 运行面

```text
AgentRuntimeGateway
  create_conversation(agent_code, user_context) -> ConversationRef
  chat(agent_code, conversation_id, message, stream) -> AgentResult/EventStream

RagRuntimeGateway
  query(rag_code, query, stream) -> RagResult/EventStream

WorkflowRuntimeGateway
  run(workflow_code, inputs, idempotency_key) -> WorkflowRun
  get_status(run_id) -> WorkflowRun
```

### 5.2 控制面

```text
KnowledgeControlGateway
  ensure_knowledge(spec) -> PlatformResourceRef
  import_document(knowledge_code, document) -> ImportTask
  get_import_status(task_id) -> ImportTask

AgentControlGateway
  ensure_agent(spec) -> PlatformResourceRef
  publish(agent_code) -> PublishedApplication

RagControlGateway
  ensure_rag(spec) -> PlatformResourceRef
  publish(rag_code) -> PublishedApplication

WorkflowControlGateway
  ensure_workflow(spec) -> PlatformResourceRef
  publish(workflow_code) -> PublishedWorkflow

PlatformHealthGateway
  check() -> PlatformHealth
```

`ensure_*` 采用期望状态语义：不存在则创建，存在且配置变化则更新，配置一致则不操作。这样部署脚本可重复执行，不把 Wanwu 非幂等细节泄漏到业务层。

## 6. 控制面与运行面

### 6.1 控制面

使用路径：

- `/user/api/v1/*`
- `/use/model/api/v1/*`
- `/workflow/api/*`

使用服务账号 JWT，只允许内部部署任务和授权后台调用。职责包括创建、配置、发布和查询平台资源。

### 6.2 运行面

使用路径：

- `/service/api/openapi/v1/agent/conversation`
- `/service/api/openapi/v1/agent/chat`
- `/service/api/openapi/v1/rag/chat`
- 工作流发布后返回的实际路径

使用资源对应的 API Key。运行面不得持有管理员 JWT。

### 6.3 Client 规则

- 使用一个异步连接池，不在每次请求中创建 Client；
- 默认连接超时 5 秒、普通请求 30 秒、Agent/RAG 运行 60 秒、上传按大小单独配置；
- GET 和显式幂等请求允许有限重试；创建、发布、工作流运行没有幂等键时不得盲目重试；
- 同时检查 HTTP 状态、Wanwu 业务码和响应正文；HTTP 200 空正文不视为成功；
- `X-Trace-Id` 从职引入口透传，日志记录职引资源代码、Wanwu 资源 ID、耗时与结果；
- Authorization、API Key、模型密钥、上传正文不得写入日志。

## 7. 资源映射与部署

职引业务使用稳定代码，不直接保存环境相关的 Wanwu ID：

```text
career-diagnosis-agent -> assistantId + appId + apiKeyRef
career-rag             -> ragId + appId + apiKeyRef
career-knowledge       -> knowledgeId
career-workflow        -> workflowId + publishedPath + tokenRef
```

资源映射应包含：

- `resource_code`
- `resource_type`
- `wanwu_resource_id`
- `wanwu_app_id`
- `credential_ref`
- `desired_spec_hash`
- `remote_revision`
- `status`
- `last_synced_at`
- `last_error_code`

API Key 与服务账号凭据只保存为密钥引用；本地开发可从环境变量读取，生产环境接入密钥管理服务。普通数据库和 JSON 不保存明文凭据。

部署流程：

```text
1. 启动 Wanwu 中间件
2. 执行 Wanwu schema 初始化
3. 启动 Wanwu 领域服务和 AI 引擎
4. 等待 Wanwu 业务级 readiness
5. 启动职引后端
6. 执行 pami bootstrap/reconcile
7. 创建或更新知识库、RAG、智能体和工作流
8. 发布应用并保存资源映射/API Key 引用
9. 执行运行面冒烟测试
10. 职引 readiness 变为 ready
```

只检测端口监听不足以判定 ready；至少验证登录、模型列表、知识服务、Agent/RAG 运行面和职引到 Wanwu 的完整链路。

## 8. 职引对外 API

对外提供职引语义，不暴露 Wanwu DTO：

```text
POST /api/v1/platform/deployments
GET  /api/v1/platform/deployments/{id}
GET  /api/v1/platform/health

POST /api/v1/knowledge/documents
GET  /api/v1/knowledge/documents/{id}/status
POST /api/v1/knowledge/search

POST /api/v1/agents/{agentCode}/conversations
POST /api/v1/agents/{agentCode}/chat
POST /api/v1/rags/{ragCode}/query
POST /api/v1/workflows/{workflowCode}/runs
GET  /api/v1/workflows/runs/{runId}
```

平台部署接口属于受保护的内部管理接口；普通用户只能调用业务允许的运行接口。Controller 只负责参数与响应，部署和调用逻辑进入业务 Service，外部协议转换进入 pami Adapter。

## 9. 错误与降级

Wanwu 错误统一映射为 SDK 异常：

| 场景 | 职引错误 |
| --- | --- |
| 连接失败、超时、5xx | `UnavailableError` |
| JWT/API Key 无效 | `AuthenticationError` |
| Wanwu 权限拒绝 | `AuthorizationError` |
| 资源不存在 | `ResourceNotFoundError` |
| 请求或配置不合法 | `ValidationError` |
| 非幂等冲突、重复发布 | `ConflictError` |
| 响应字段缺失、空正文 | `UpstreamProtocolError` |

运行面失败时由业务用例决定是否降级到本地实现；控制面部署失败不得静默回落，也不得把资源标记为已发布。装配报告必须显示真实状态。

## 10. 已知 Wanwu 风险处理

首期处理策略：

| Wanwu 问题 | 处理 |
| --- | --- |
| 智能体专用删除路由漂移 | 使用统一应用删除接口或能力探测 |
| 文件续传路径漂移 | 以实测 `/file/check/list` 契约为准 |
| 知识文档列表默认过滤 | 查询全部时显式传 `status=-1` |
| 重复发布不幂等 | 发布前查询状态并保存 `desired_spec_hash` |
| 组织启停 panic | 不纳入首期公开能力 |
| 资源授权写入 EOF | 修复并回归通过前保持禁用 |
| Python 单节点调试契约不完整 | 不作为工作流部署成功的前置条件 |
| HTTP 200 空正文 | Client 按协议错误处理 |

集成测试固定 Wanwu 镜像/源码提交号，避免源码、Swagger、Nginx 和运行二进制漂移。

## 11. 测试设计

### 11.1 单元测试

- DTO 映射；
- 错误映射；
- 凭据选择；
- 资源映射；
- 幂等部署决策；
- 日志脱敏。

### 11.2 Port 契约测试

对 local/mock 与 pami 实现运行同一组语义断言，验证返回类型、顺序、空值、异常和降级口径一致。

### 11.3 模拟服务集成测试

覆盖成功、401、403、404、业务码非零、5xx、超时、空正文、畸形 JSON、SSE 中断和重复发布。

### 11.4 真实 Wanwu 集成测试

按依赖顺序执行并清理：

```text
登录 -> 知识库 -> 文档上传/导入 -> RAG -> 发布/API Key -> 查询
     -> 智能体 -> 会话 -> 发布/API Key -> 对话
     -> 工作流 -> 保存 -> 运行 -> 发布 -> 调用
```

测试资源全部使用唯一前缀，清理失败必须报告残留，不能忽略。

### 11.5 部署冒烟测试

- 单命令可启动完整栈；
- Wanwu 端口不对公网开放；
- 职引 `/healthz` 展示 pami 能力为 `wired`；
- 从职引公开接口完成一次 Agent 和 RAG 调用；
- 重启后资源映射仍有效；
- 重复执行 bootstrap 不产生重复资源。

## 12. 分阶段实施

本设计覆盖多个可独立验收的子项目，实施时不得写成一个超大改动。五个阶段分别建立实现计划、测试和评审门禁；只有前一阶段验收通过，后一阶段才能依赖其产物。首次实施计划只覆盖“阶段 1：源码与部署基线”。

### 阶段 1：源码与部署基线

- 导入干净的 Wanwu 源码快照；
- 记录上游版本和本地补丁；
- 建立统一 Compose 网络、镜像构建和健康检查；
- 不修改职引业务行为。

### 阶段 2：Client 与运行面

- 实现共享 Client、错误和凭据；
- 打通 Agent conversation/chat 与 RAG chat；
- 完成运行面契约和模拟集成测试；
- 接入 boot 装配报告。

### 阶段 3：知识与资源部署

- 实现知识库、文件上传、文档导入和状态查询；
- 实现 RAG/Agent 创建、配置、发布、API Key 获取；
- 建立资源映射与幂等 reconcile。

### 阶段 4：工作流

- 实现工作流保存、运行、状态和发布；
- 解析并保存发布路径；
- 对重复发布和不完整辅助接口做能力探测与保护。

### 阶段 5：职引公开 API 与完整验收

- 通过业务 Service 和 Facade 暴露职引语义接口；
- 导出 OpenAPI 并生成前端类型；
- 完成真实 Wanwu 集成和部署冒烟测试；
- 更新装配门禁和运维文档。

## 13. 完成标准

满足以下条件才算“pami 已接入”，而不是仅有代码骨架：

1. Wanwu 源码和本地补丁可追溯、可构建；
2. 一个命令可启动职引与 Wanwu 完整依赖；
3. 职引后端可以创建或复用知识库、RAG、智能体和工作流；
4. 可以发布资源并通过职引后端调用运行面；
5. 重复部署不会生成重复资源；
6. JWT、API Key 和模型密钥不出现在代码、普通配置、响应或日志中；
7. Wanwu 管理接口不对公网开放；
8. local 与 pami 实现可由 boot 配置切换；
9. pami 能力通过契约、集成和部署冒烟测试；
10. `/healthz` 和分级门禁准确报告是否真实接通。
