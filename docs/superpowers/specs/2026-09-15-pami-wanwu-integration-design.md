# 职引内置 pami/zhiyinbase 源码与接口暴露设计

| 项 | 内容 |
| --- | --- |
| 状态 | 已批准设计，作为后续实施计划的依据 |
| 日期 | 2026-09-15 |
| 目标 | 将 zhiyinbase 源码纳入职引仓库与统一部署体系，并通过 zhiyinbase 自身 Nginx/BFF 暴露原生接口 |
| 依据 | 《职引技术架构文档》《职引技术架构文档-第一期》《职引技术架构-分层详细设计》及 zhiyinbase 平台接口与安全文档 |

## 1. 结论

本任务采用“同仓库、统一部署、双入口、边界不变”的方案：

- zhiyinbase 完整源码作为职引内置基础平台源码放在 `platform/wanwu/`；
- zhiyinbase 保持自身 Go、Python、Vue、Nginx、BFF 和微服务边界，独立构建与运行；
- 职引 API 继续只提供 `/api/v1/*` 产品接口；
- zhiyinbase 原生接口由 zhiyinbase 的 Nginx/BFF 入口提供，不经过职引 FastAPI 透明代理；
- 本任务不实现真实 pami Client，不配置真实账号、模型或应用，不要求真实业务响应联调；
- `zhiyin-infrastructure/pami/` 保留生产替换点和显式未实现行为，所有 pami 开关默认关闭。

该方案符合正式架构文档对基础设施边界、Adapter 依赖方向和第一期本地模拟策略的要求，同时满足平台侧“源码接入并暴露已有接口”的交付目标。

## 2. 范围

### 2.1 本次包含

1. 导入可追溯、可重复更新的 zhiyinbase 源码快照；
2. 提供 zhiyinbase 与职引后端的容器构建资产；
3. 提供统一 Docker Compose 网络、环境初始化、启停和配置验证；
4. 通过 zhiyinbase 自身 Nginx/BFF 暴露已有 HTTP 接口；
5. 保持 zhiyinbase 中间件和内部微服务端口不对宿主机公开；
6. 保留职引 pami Adapter 骨架、配置开关和架构守卫；
7. 将现有 zhiyinbase 接口清单和已知问题文档纳入交付索引；
8. 建立源码边界、容器资产、Compose 渲染、路由暴露和文档一致性测试；
9. 提供 CI 与运维说明。

### 2.2 本次不包含

- 不实现真实 zhiyinbase HTTP Client 或职引侧运行/控制 Adapter；
- 不创建、配置或发布真实 zhiyinbase 资源；
- 不维护职引资源代码与 zhiyinbase 资源 ID/API Key 的运行映射；
- 不配置真实用户、JWT、API Key、模型密钥或外部模型；
- 不要求真实 zhiyinbase 业务请求成功；
- 不在职引 FastAPI 中增加 zhiyinbase 全接口透明代理；
- 不把 zhiyinbase 改造成 Python 包或合入职引进程；
- 不直接读写 zhiyinbase MySQL 业务表；
- 不绕过 zhiyinbase 既有认证、组织、权限或资源归属检查；
- 不建设 Kubernetes 或生产高可用部署。

## 3. 架构与边界

```text
同一职引仓库与交付单元
|
|-- zhiyin-src/template/
|   `-- zhiyin-api
|       `-- /api/v1/*                  职引产品接口
|
|-- platform/wanwu/
|   |-- web/                           zhiyinbase 前端
|   |-- internal/ + cmd/               zhiyinbase Go 服务
|   |-- agent/                         zhiyinbase Python 能力
|   `-- Nginx -> BFF/AgentScope        zhiyinbase 原生 HTTP 入口
|       |-- /user/api/*
|       |-- /use/model/api/*
|       |-- /service/api/*
|       |-- /workflow/api/*
|       `-- /minio/download/api/*
|
`-- deploy/
    `-- Compose 覆盖、环境初始化、启停与验证脚本
```

依赖规则保持为：

```text
zhiyin-business / zhiyin-orchestration
                  |
                  v
             Port / Gateway
                  ^
                  |
zhiyin-infrastructure/pami  --HTTP（后续生产替换）--> zhiyinbase Nginx/BFF
```

本次只交付 zhiyinbase 源码、部署和原生接口入口。真实 HTTP 调用仍是后续生产替换工作。

### 3.1 不增加职引透明代理

职引 API 是产品/BFF 接入层，zhiyinbase 是基础设施平台。在职引 FastAPI 中透传全部 zhiyinbase 接口会产生第二套网关、鉴权、SSE、上传和错误语义，破坏既有边界。

因此：

- 职引产品接口继续使用职引 DTO、Facade 和 OpenAPI；
- zhiyinbase 原生接口继续使用 zhiyinbase 请求模型、错误码、JWT、API Key 和流式协议；
- 两套入口可以由部署环境使用不同域名或端口发布，但应用代码不互相代理。

## 4. 源码纳入

zhiyinbase 快照固定在 `platform/wanwu/`，保存上游地址、完整提交哈希、导入日期和排除项。本地补丁通过职引 Git 历史单独追溯。

`scripts/import_wanwu.py` 只从已提交的 Git 对象导出源码，不复制上游脏工作区。重复导入同一提交应产生相同源码内容与元数据。

导入过程排除：

- 上游 `.git`；
- `.env`、备份环境文件和运行密钥；
- 日志、PID、缓存和输出目录；
- Python/pytest 临时文件；
- 本地数据库、对象存储和运行卷。

构建必需的非密钥前端环境文件、版本插件和占位目录必须保留。

## 5. 构建与统一部署

- `platform/wanwu` 是独立构建单元，不加入职引 `pyproject.toml`；
- zhiyinbase 沿用自身 Dockerfile/Compose 模型；
- 职引后端使用 `zhiyin-src/template/Dockerfile`，以非 root 用户运行；
- zhiyinbase 与职引共享 `wanwu-net`；
- MySQL、Redis、Kafka、Elasticsearch、MinIO、BFF、Agent、RAG、AgentScope 等内部端口不映射到宿主机；
- zhiyinbase HTTP 流量只从 zhiyinbase Nginx 进入；
- 本地开发默认绑定 `127.0.0.1:8081`，不是公网监听；
- 生产域名、TLS 和公网策略由部署环境外层网关负责。

`deploy/.env.example` 只保存非秘密默认值和空秘密字段。`deploy/init_env.py` 生成被 Git 忽略的 `deploy/.env`，不得覆盖已有文件或打印秘密。

## 6. zhiyinbase 原生接口暴露

zhiyinbase Nginx 保持上游路由：

| 路径 | 用途 | 信任面 |
| --- | --- | --- |
| `/user/api/*` | 登录、用户、组织、资源管理 | zhiyinbase JWT、组织与权限规则 |
| `/use/model/api/*` | 模型调用与相关能力 | zhiyinbase 对应中间件规则 |
| `/service/api/*` | 通用服务与 OpenAPI | 按接口使用 JWT、API Key 或开放规则 |
| `/workflow/api/*` | AgentScope 工作流能力 | 工作流协议与平台身份透传 |
| `/minio/download/api/*` | 受控文件下载 | Wanwu/MinIO 既有规则 |

“暴露接口”只表示路由能从 zhiyinbase Nginx 到达目标服务，不表示接口免认证、业务数据已配置或真实调用成功。

### 6.1 静态验收

在不启动真实业务环境时，以以下证据验收：

1. Nginx 配置存在对应路径；
2. 路径转发到正确 BFF、AgentScope 或 MinIO 服务；
3. 目标服务与 Nginx 位于同一 Compose 网络；
4. 个体微服务端口没有宿主机映射；
5. Compose 合并配置可以成功渲染；
6. 字段级接口清单记录路径、方法、认证和验证状态。

本任务不以 HTTP 200 或真实业务结果作为完成条件。

### 6.2 不改变信任面

统一部署不得删除 zhiyinbase 认证中间件、注入固定管理员身份、泄露秘密、把 Callback 改成匿名公网接口，或把“路由存在”描述成“业务已联通”。

## 7. 职引侧 pami 替换点

第一期继续使用 `DefaultPassAuth`、`LocalOrMockLLM`、`LocalKnowledgeRepo` 及其他 Local/Mock/Noop Gateway。

`zhiyin-infrastructure/pami/` 中的 Adapter 类保留为生产替换目标。配置开关默认关闭；如果误开启，未实现方法必须显式抛错，不得静默回落。

架构守卫保证：

- 业务层不 import `zhiyin_infrastructure`；
- 基础设施层不 import 业务层或编排层；
- zhiyinbase 源码不进入职引 Python 包；
- API 层不直接引用 zhiyinbase DTO。

## 8. 文档与测试

文档职责：

| 文档 | 职责 |
| --- | --- |
| `外部平台/pami-Wanwu/接口.md` | 字段级接口、方法、路径、认证和验证状态 |
| `外部平台/pami-Wanwu/平台报错和未连通接口.md` | 已实际确认的问题 |
| `外部平台/pami-Wanwu/架构文档/` | zhiyinbase 路由、服务、安全和部署事实 |
| 本设计 | 职引纳入源码与暴露原生接口的工程边界 |

测试分为：

- 源码与边界：导入器、追溯元数据、秘密排除、Python 包边界；
- 容器与部署：非 root、统一网络、内部端口隔离、环境生成；
- 路由暴露：静态解析 Nginx 配置，覆盖五组路由并验证目标服务；
- 职引回归：pytest、Ruff、OpenAPI 快照、阶段一门禁和前端类型检查。

路由测试只证明“配置已接入”，不得伪造真实业务联通结论。

## 9. 五阶段实施

### 阶段 1：源码快照

- 安全、可重复的导入工具；
- 固定 zhiyinbase 提交及追溯元数据；
- 秘密与运行文件排除。

### 阶段 2：构建与统一部署

- 职引后端容器化；
- zhiyinbase 独立构建资产；
- 统一 Compose 网络、环境初始化、启停和配置验证。

### 阶段 3：原生接口路由暴露

- 核对 zhiyinbase Nginx/BFF 原生路由；
- 增加路由静态契约测试；
- 确认内部端口隔离；
- 与《接口.md》交叉校验。

### 阶段 4：职引边界与替换点

- 保留 pami Adapter 骨架和关闭状态；
- 增加误开启时显式失败测试；
- 增加 zhiyinbase 源码不得被职引包引用的架构守卫；
- 确认职引产品 API 与行为不变。

### 阶段 5：CI、文档与验收

- CI 执行源码、容器、部署、路由和架构测试；
- 更新仓库入口、运维命令和文档索引；
- 运行完整静态验收并记录未执行的真实联调项。

## 10. 完成标准

同时满足以下条件才算完成：

1. zhiyinbase 快照、上游提交和本地补丁可追溯；
2. 重复导入不会带入秘密或运行状态；
3. zhiyinbase 与职引拥有独立构建单元和统一 Compose 网络；
4. Compose 合并配置可成功渲染；
5. zhiyinbase 原生路由通过 Nginx/BFF 暴露并通过静态契约测试；
6. zhiyinbase 内部微服务和中间件端口不映射到宿主机；
7. 职引 `/api/v1/*` 不承担 zhiyinbase 全接口透明代理；
8. pami 开关默认关闭，误开启未实现能力时显式失败；
9. 接口清单准确标记认证方式和实际验证状态；
10. 后端测试、静态检查、OpenAPI 快照、前端类型和 CI 配置通过；
11. 文档明确说明未完成真实 zhiyinbase 业务接入；
12. 工作树无意外修改，密钥文件未被 Git 跟踪。
