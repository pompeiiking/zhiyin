# 外部平台参考文档

本目录存放**第三方平台**的架构与接口资料，用于对接与替换点设计，**不属于职引自身的架构文档**。

## pami（联通元景葩米 Lite / Wanwu）

| 文件 | 内容 |
| --- | --- |
| `pami-Wanwu/架构文档/00~10` | Wanwu 平台整体架构（分层、服务边界、前端、智能体与工作流、模型与 RAG、数据、通信、安全、部署），从该平台仓库反向梳理，含 Git 基线 |
| `pami-Wanwu/接口.md` | 字段级真实 API 契约（HTTP 方法与路径、必填、请求结构、调用凭证口径） |
| `pami-Wanwu/平台报错和未连通接口.md` | 已知报错与未连通接口清单 |

**为什么放在"外部平台"而不是原来的"基础设施层架构文档"**

原来的位置是 `docs/技术架构文档/基础设施层架构文档/`。这批文档标题写的是
「Wanwu 平台架构文档」，代码路径与进程名都沿用 Wanwu（即职引总架构中的 pami 平台），
属于**第三方平台的资料**；放在"基础设施层"下面容易被误读成职引自身的基础设施层设计。
移到本目录后，职引自身的架构文档与外部平台资料不再混淆。

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

> 注意：本目录文档描述的是 pami 平台的现状，**不代表职引第一期的实现范围**。
> 第一期这些适配器只是骨架，未实现的方法会在首次调用时明确报错，不会静默回落。
