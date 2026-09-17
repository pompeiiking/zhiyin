# zhiyin 内置 PAMI 接入与接口说明

> 用途：供前后端及平台同学对接。核查日期：2026-09-17。
> PAMI 即内置 Wanwu 平台，部分文档称为 zhiyinbase，源码路径仍为 `platform/wanwu/`。
> 本文说明当前源码与部署配置，不代表所有接口已经通过运行时联调。

## 1. 部署方式

PAMI 以固定版本的源码快照纳入 `platform/wanwu/`，作为独立服务运行，不直接引入职引业务包。

启动脚本合并 PAMI 自带 Compose 与职引覆盖配置，将 PAMI 和 `zhiyin-api` 加入同一个 `wanwu-net` 网络。覆盖配置取消 BFF、AgentScope 和主要中间件的宿主机端口映射，保留 Nginx 的本机 8081 入口。

依据：[统一启动脚本](../../deploy/up.ps1)、[职引部署覆盖配置](../../deploy/compose.yaml)、[源码版本记录](../../platform/wanwu/UPSTREAM.md)。

## 2. 接口入口

| 调用位置 | PAMI 基础地址 | 说明 |
| --- | --- | --- |
| 本机调试工具或程序 | `http://127.0.0.1:8081` | 仅绑定本机回环地址，默认不向其他机器开放 |
| 职引后端容器 | `http://nginx:8081` | 通过 Docker 内部网络访问 |

职引容器已配置 `ZHIYIN_PAMI_BASE_URL=http://nginx:8081`。职引侧 HTTP 适配器已经实现，但能力开关默认关闭；实际可用性仍取决于 PAMI 应用发布、凭据和联调结果。

PAMI 原生接口与职引业务接口是两套入口：**职引 `/api/v1/*` 不透明代理 PAMI 接口。** 前端调用职引业务 API；职引后端按需通过适配器调用 PAMI。

## 3. 路由转发与具体接口（重点）

### 3.1 Nginx 暴露的是路径前缀，不是五个接口

| Nginx 路径前缀 | 转发服务 | 主要用途 |
| --- | --- | --- |
| `/user/api/` | `bff-service:6668` | 登录、组织、用户、权限、模型、知识库及应用管理 |
| `/service/api/` | `bff-service:6668` | Agent/RAG 运行 OpenAPI、文件接口 |
| `/use/model/api/` | `bff-service:6668` | MCP 等接口 |
| `/workflow/api/` | `agentscope-wanwu:6672` | 工作流配置、调试、运行和发布 |
| `/minio/download/api/` | `minio-wanwu:9000` | 文件下载 |

前三个前缀都转发到同一个 BFF，并不是严格的服务或权限隔离边界。具体接口是否存在、允许什么方法、需要什么权限，由服务端路由及中间件决定。

由于 `proxy_pass` 目标以 `/` 结尾，转发时会去掉匹配的前缀：

```text
外部 POST /service/api/openapi/v1/agent/chat
      → BFF POST /openapi/v1/agent/chat

外部 POST /user/api/v1/knowledge/doc/import
      → BFF POST /v1/knowledge/doc/import
```

实现位置：[Nginx 配置](../../platform/wanwu/configs/middleware/nginx/conf.d/aibase.conf)。

### 3.2 对接时优先关注的接口

以下均为完整的原生路径，调用时拼接第 2 节的基础地址。

| 接口 | 用途 | 关键输入 |
| --- | --- | --- |
| `POST /user/api/v1/base/login` | 获取 PAMI 登录会话 | 按登录契约提交账号及验证码等字段 |
| `POST /user/api/v1/appspace/app/key` | 为应用生成 API Key | 按契约指定应用及类型 |
| `POST /service/api/openapi/v1/agent/conversation` | 创建 Agent 会话 | `title` |
| `POST /service/api/openapi/v1/agent/chat` | 调用 Agent | 必填 `conversation_id`、`query`；可选 `stream` |
| `POST /service/api/openapi/v1/rag/chat` | 调用 RAG 应用 | 必填 `query`；可选 `stream` |
| `POST /user/api/v1/knowledge/doc/import` | 导入知识库文档 | 按知识库文档导入契约提交 |
| `POST /workflow/api/workflow/run` | 运行工作流 | 按工作流契约提交；运行镜像待核实 |

Agent 调用顺序为：先配置并发布 PAMI 应用、生成应用 API Key，再创建会话取得会话 ID，最后发送问答请求。例如非流式问答请求体：

```json
{
  "conversation_id": "<PAMI_CONVERSATION_ID>",
  "query": "请分析我的职业方向",
  "stream": false
}
```

运行面支持流式与非流式分支，但这不意味着职引已经提供流式业务接口。PAMI 的管理响应、Agent 响应、RAG 响应及 SSE 格式不同，适配器需要分别解析，不能统一假设为职引的响应信封，也不能仅凭 HTTP 200 判定调用成功。

实现位置：[BFF 路由组](../../platform/wanwu/internal/bff-service/server/http/handler/init.go)、[管理路由入口](../../platform/wanwu/internal/bff-service/server/http/handler/router/v1/router.go)、[运行 OpenAPI 路由](../../platform/wanwu/internal/bff-service/server/http/handler/router/openapi/router.go)。完整字段见 [PAMI 接口清单](../技术架构文档/pami/pami-Wanwu/接口.md)。

### 3.3 “135 个接口”的正确口径

135 是文档中的“HTTP 方法＋路径”清单，不能直接当作当前内置版本全部已联通。

| 清单分类 | 数量 | 当前源码/配置核查结果 |
| --- | --- | --- |
| BFF 接口 | 107 | 有路由注册，且 Nginx 覆盖对应路径；不代表已逐项联调成功 |
| 工作流接口 | 18 | 有 Nginx 转发，需核实 AgentScope 运行镜像的路由及可用性 |
| 资源授权接口 | 6 | 文档存在，内置 BFF 源码未找到对应路由注册 |
| 模型回调接口 | 4 | BFF 已注册，但 Nginx 没有原样 `/callback/` 前缀 |

六项缺少注册的资源接口位于 `/user/api/v1/resource/` 下：`GET workflow-key-access`、`GET/PUT permissions`、`GET members`、`GET access`、`GET visible`。这反映文档与源码快照存在版本差异。

回调接口虽没有原样入口，但现有 BFF 宽前缀转发可产生 `/service/api/callback/v1/...` 等别名，不能据此认定回调完全不对外可达。实际接口及鉴权仍须以部署镜像和联调结果确认。

## 4. 鉴权方式

| 接口类别 | 凭据与检查 |
| --- | --- |
| 登录及部分公共接口 | 按各自路由规则，无需已有 JWT |
| 管理接口 | `Authorization: Bearer <JWT>`；通常携带 `X-Org-Id: <ORG_ID>`，并检查用户状态或权限 |
| Agent/RAG 运行 OpenAPI | `Authorization: Bearer <APP_API_KEY>`，检查 API Key 关联的应用类型 |
| 工作流、下载及内部回调 | 按各自服务规则，不能统一认定为 JWT 或 API Key 鉴权 |

Agent/RAG 的应用 ID、用户 ID 和组织 ID由 API Key 的关联记录确定，不是通过问答请求任意指定。凭据只供后端配置使用，不应提交到代码、前端或日志中。

依据：[API Key 鉴权](../../platform/wanwu/internal/bff-service/server/http/middleware/auth_openapi.go)、[管理接口中间件](../../platform/wanwu/internal/bff-service/server/http/middleware/init.go)。

## 5. 职引侧调用方式

目标链路为：

```text
职引业务 Service / 编排层
  → Data SDK Gateway 契约
  → PAMI Adapter（HTTP 调用与契约转换已实现）
  → HTTP 请求 Nginx
  → PAMI BFF / AgentScope
```

适配器集中在 `zhiyin-src/template/zhiyin-infrastructure/zhiyin_infrastructure/pami/adapters.py`，包括 `PamiLLMGateway`、`PamiEmbedGateway`、`PamiKnowledgeGateway`、`PamiSearchGateway` 和 `PamiAuthGateway`。

Boot 层通过 `ZHIYIN_USE_PAMI_LLM`、`ZHIYIN_USE_PAMI_EMBEDDING`、`ZHIYIN_USE_PAMI_KNOWLEDGE`、`ZHIYIN_USE_PAMI_AUTH` 选择本地或 PAMI 实现，并读取基础地址、组织 ID 与 Embedding 模型 ID 等连接配置。Agent 与 RAG 的 API Key 绑定不同应用类型，应分别配置 `ZHIYIN_PAMI_AGENT_API_KEY` 和 `ZHIYIN_PAMI_RAG_API_KEY`；旧的 `ZHIYIN_PAMI_API_KEY` 只保留单能力兼容。知识库开关同时替换 `KnowledgeGateway` 与关键词/混合检索的 `SearchGateway`；PAMI 不接受调用方裸向量或 metadata filters 的接口会显式报不可用，不静默伪造结果。知识范围由 RAG API Key 所绑定的应用决定，不能把 `namespace` 文本拼进 query 冒充服务端隔离。

当前适配器已完成参数转换、非流式响应解析、超时及统一错误映射，并有 MockTransport 契约测试。2026-09-17 已补齐 PAMI 冻结版本全部镜像并启动完整 Compose；MySQL、Redis、MinIO、Kafka、Elasticsearch、七个 PAMI 后端服务、BFF、AgentScope、Nginx、职引 pgvector 和 `zhiyin-api` 均完成运行检查，所有带健康探针的常驻服务为 `healthy`，PAMI Web 返回 200。职引侧真实 MySQL Repository、TransactionManager、RawQuery、Redis、MinIO 与 pgvector 已装配并通过运行验收和 21 项 MySQL 契约测试。

尚未完成的是 Agent/RAG/模型配置、应用发布与凭据发放。当前 `deploy/.env` 中模型 ID、组织 ID、Agent/RAG API Key 均为空，所以 Embedding 与 VectorSync 不装配，不能用 Mock 结果代替真实模型调用。Embedding 回调使用 `/service/api/callback/v1/model/{modelId}/embeddings` 这一 Nginx 别名；它已由源码路由核对，但必须经实际凭据联调后才能标记为运行验收通过。

PAMI Agent 上游源码另有两个部署问题：多处服务地址写死为默认网桥 `172.17.0.1`，与当前 `wanwu-net` 隔离网络不一致；Action 子服务要求 `[ACTION]` 应用凭据，但仓库配置未提供。当前 Agent 主服务、网络搜索、文档处理及部分 MinIO 辅助服务已运行，Action 端口 1992 与文件上传辅助端口 15001 未就绪。该问题需要平台负责人确认服务发现方式与凭据，职引侧不写假值、不修改平台契约来伪造健康。

依据：[适配器](../../zhiyin-src/template/zhiyin-infrastructure/zhiyin_infrastructure/pami/adapters.py)、[配置](../../zhiyin-src/template/zhiyin-boot/zhiyin_boot/settings.py)、[装配入口](../../zhiyin-src/template/zhiyin-boot/zhiyin_boot/container/gateways.py)。

## 6. 当前完成度与对接口径

已具备源码纳管、统一部署配置、内部网络、原生接口代理配置，以及职引侧 LLM、Embedding、知识库/检索、鉴权 HTTP 适配器。PAMI 能力开关默认关闭，未配置凭据时职引仍使用本地实现。

业务级接入尚需完成：模型与 Agent/RAG/知识库配置、应用发布与凭据配置、职引资源映射，以及真实接口联调。部分平台接口存在已记录的问题，不能默认所有接口稳定可用，见 [已知问题清单](../技术架构文档/pami/pami-Wanwu/平台报错和未连通接口.md)。

**对外建议表述：PAMI 的部署级接入、原生接口暴露和职引侧适配代码已完成；真实应用/模型配置与运行联调尚未验收，接口是否可用以当前部署版本和联调记录为准。**
