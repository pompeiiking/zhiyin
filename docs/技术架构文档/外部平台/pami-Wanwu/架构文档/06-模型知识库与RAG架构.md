# Wanwu 模型、知识库与 RAG 架构

## 1. 能力边界

Wanwu 将“模型配置”“知识资产管理”“RAG 应用配置”和“文档处理/检索执行”拆开：Go 服务保存配置与业务关系，独立 RAG 镜像执行解析、切分、索引和召回，外部模型提供 Chat、Embedding 和 Rerank 能力。

```ascii
+--------------+      +---------------+      +--------------------+
| Model service|----->| BFF/OpenAI API|----->| Model Provider     |
| 模型配置/类型 |      | 路由与调用入口  |      | Chat/Embed/Rerank  |
+--------------+      +---------------+      +--------------------+
        ^                      ^
        |                      |
+-------+----------+    +------+----------+
| Knowledge service|--->| RAG Engine       |
| 知识/文档/任务    |    | 解析/切分/索引   |
+-------+----------+    +------+----------+
        |                      |
        v                      v
 MySQL / MinIO / Kafka     Elasticsearch
        ^                      ^
        +----------+-----------+
                   |
             +-----+-----+
             | RAG service|
             | 应用/问答   |
             +-----------+
```

## 2. 模型纳管

Model service 管理模型类型、供应商连接、模型配置和可用性信息。平台能力面区分 Chat、Embedding、Rerank 等模型用途；业务应用只引用模型标识，模型连接细节由模型服务和调用入口解析。

模型查询和可用性在当前工作区加入创建者/成员过滤【混合】；授权并不允许成员修改模型密钥或连接配置【未提交】。

## 3. 知识导入链路

```ascii
User -> Web upload -> BFF -> Knowledge service -> MinIO（原始对象）
                                |
                                +-> MySQL（知识库、文档、任务元数据）
                                |
                                +-> Kafka（处理事件）
                                      |
                                      v
                                  RAG Engine
                                      |
                        parse -> split -> embedding -> index
                                      |
                                      v
                                Elasticsearch
```

Knowledge service 还使用进程内异步任务容器处理文档/知识库删除等分步操作。Kafka 主要负责跨进程知识处理事件；二者不是同一种任务机制。

## 4. RAG 查询链路

```ascii
Question -> BFF -> RAG service -> Knowledge metadata
                         |
                         +-> RAG Engine search
                                |
                  query embedding -> ES recall -> rerank
                                |
                                v
                         context documents
                                |
                         Chat model generation
                                |
                         SSE response to Web
```

RAG service 保存 RAG 应用及其模型、知识库和检索参数，`rag-wanwu`镜像承担实际检索执行。配置显示 RAG service 通过 HTTP 调用 RAG Engine，并通过 gRPC 查询 Knowledge service。

## 5. 数据对象与状态

| 对象 | 权威位置 | 衍生位置 | 典型状态 |
|---|---|---|---|
| 模型配置 | Model service 的 MySQL 数据 | Redis 临时数据 | 启用、禁用、模型类型 |
| 知识库 | Knowledge service 的 MySQL 数据 | ES 索引 | 创建、导入、删除 |
| 文档与分段元数据 | MySQL | ES 检索文档 | 上传、解析、索引、失败 |
| 原始文档 | MinIO | 无 | 对象存在、删除 |
| 导入/删除任务 | MySQL/任务容器 | Kafka 事件 | 等待、运行、成功、失败 |
| RAG 应用配置 | RAG service 的 MySQL 数据 | Redis 临时数据 | 草稿、配置、发布关联 |

## 6. 一致性模型

- MySQL 记录业务关系和任务状态，MinIO/ES 是跨组件写入；系统不具备跨三者的原子事务。
- 文档可先保存对象和元数据，再异步建立索引；失败时应保留可重试状态，不能把“已上传”等同于“可检索”。
- 删除知识库或文档需清理 MySQL、MinIO 和 ES；进程内异步任务中断后的恢复能力需要运行验证。
- ES 索引应被视为可重建数据，但重建所需的原文、分段或解析结果必须仍可取得。

## 7. 资源授权影响【未提交】

知识库列表、详情、文档和检索请求通过父知识库追溯资源范围。创建者可管理，被授权成员可使用和绑定知识库；授权策略不复制知识数据，也不改变原创建者。若授权查询数据库失败，设计选择拒绝访问。

## 8. 故障降级

| 故障 | 可继续能力 | 受影响能力 |
|---|---|---|
| Chat 模型故障 | 模型/知识配置管理 | RAG 生成和 Agent 回答 |
| Embedding/Rerank 故障 | 原文保存、已有配置 | 新索引或检索质量 |
| Kafka 故障 | 已有知识查询可能继续 | 新文档处理事件 |
| Elasticsearch 故障 | MySQL/MinIO 中的管理数据 | 知识召回和会话检索 |
| MinIO 故障 | 部分元数据查看 | 上传、下载、解析原文 |
| RAG Engine 故障 | 模型与知识管理 | 解析、索引、召回 |

## 9. 扩展原则

新增模型提供商应扩展 provider 适配层而非业务应用；新增解析器/向量策略应放在 RAG 执行边界并保留状态兼容；新的检索后端必须明确权威数据、重建方式和权限回查位置。
