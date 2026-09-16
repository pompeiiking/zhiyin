# pami 平台参考文档（自有平台模块）

本目录存放 **pami（联通元景葩米 Lite / Wanwu，内部也称 zhiyinbase）平台的架构与接口资料**。
pami 是职引**自有的平台模块**，不是第三方：它承载基础设施层能力，由平台模块负责部署与演进。
本目录只放"这个模块长什么样、对外暴露什么接口"，不放职引自身的架构设计。

## pami（联通元景葩米 Lite / Wanwu）

| 文件 | 内容 |
| --- | --- |
| `pami-Wanwu/架构文档/00~10` | Wanwu 平台整体架构（分层、服务边界、前端、智能体与工作流、模型与 RAG、数据、通信、安全、部署），从该平台仓库反向梳理，含 Git 基线 |
| `pami-Wanwu/接口.md` | 字段级真实 API 契约（HTTP 方法与路径、必填、请求结构、调用凭证口径） |
| `pami-Wanwu/平台报错和未连通接口.md` | 已知报错与未连通接口清单 |

**目录边界**

本目录＝pami 模块的资料；职引自身的架构设计在上一级目录（《职引技术架构文档》
《职引-目标架构设计》等）。两边分开是为了让"模块现状"和"职引设计"各自可追溯，
**不代表 pami 属于外部**。

**职引如何用它**

只作为替换点的落地依据：

| 职引的 Port | 对接的 pami 能力 | 参考 |
| --- | --- | --- |
| `PamiLLMGateway` | pami Assistant / Model | `架构文档/05-智能体与工作流架构.md`、`接口.md` |
| `PamiKnowledgeGateway` | pami knowledge-service | `架构文档/06-模型知识库与RAG架构.md` |
| `PamiSearchGateway` | pami ES / 检索 | `架构文档/07-数据架构.md` |
| `PamiAuthGateway` | pami IAM / Permission | `架构文档/09-身份权限与安全架构.md` |

替换点清单见《职引技术架构文档-第一期》§十。对应适配器骨架在
`zhiyin-src/template/zhiyin-infrastructure/zhiyin_infrastructure/pami/adapters.py`。

pami 模块自身的组件扩展与部署（含职引所需的 PostgreSQL / pgvector 等组件）在 pami 模块内进行，
职引侧只经受冻结的接口与连接配置使用。

> 注意：本目录文档描述的是 pami 平台的现状，**不代表职引第一期的实现范围**。
> 第一期这些适配器只是骨架，未实现的方法会在首次调用时明确报错，不会静默回落。
