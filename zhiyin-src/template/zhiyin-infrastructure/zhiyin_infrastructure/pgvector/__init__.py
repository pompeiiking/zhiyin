"""pgvector 实现目录（**空抽屉**，尚未实现）。

一个目录 = 一套实现。本目录是 M3「真实存储」里**向量检索**的落点：把哈希伪嵌入
与进程内向量库换成真实嵌入模型 + pgvector，业务层与编排层**一行都不用改**
（换实现只改 `zhiyin_boot/container/gateways.py` 的装配表）。

待实现的 Port 清单（唯一事实来源是 `zhiyin_data_sdk/gateways/`，本文件只是索引）
--------------------------------------------------------------------------------
| Port | 契约文件 | 第一期本地实现（对照语义） | 装配位 |
| --- | --- | --- | --- |
| `VectorGateway` | `gateways/vector.py` | `local/vector_store.py::LocalVectorStore`（wired） | `gateways.vector` |

嵌入模型不在这里，在 `llm/` 抽屉（生成与嵌入同属"模型"这一类外部能力，
契约上已分开成 `LLMGateway` / `EmbedGateway`）。

本期最需要说清的一件事：`LocalHashEmbedder`（在 `local/embedding.py`）是**骨架**——
确定性伪向量，不具备语义能力，装配报告会如实标 `skeleton`。因此"链路通了"不等于
"检索可用了"：换真实嵌入模型时**只换 embedding 这一格**（在 `llm/`），
向量库这一格可以继续用 pgvector 实现。

开工前必须满足的条件
--------------------
1. **契约测试通过**：`tests/contracts/test_gateway_contract.py` 的向量语义断言
   （写入 / 检索 / 删除 + 模型版本路由）必须同样通过；在
   `tests/contracts/conftest.py` 的 `GATEWAY_FACTORIES` 里加一行即可自动纳入。
2. **模型版本必须参与检索过滤**：换嵌入模型后旧向量与新查询不在同一空间，
   检索必须按模型版本隔离（`VectorGateway` 的契约已把版本作为一等参数）。
   这条属 M3 门禁的 manual 项："向量模型版本路由验证（换嵌入模型后检索不串空间）"。

不要把这些实现写回 `local/`：`local/` 是"无外部依赖即可跑通"的那一套。
"""
