"""真实模型实现目录（**空抽屉**，尚未实现）。

一个目录 = 一套实现。本目录是"真实模型"这个替换点的落点：把
`LocalOrMockLLM`（无模型时按产出契约 Schema 合成合法结果）与 `LocalHashEmbedder`
（确定性伪向量）换成真实供应商的生成模型与嵌入模型，业务层与编排层**一行都不用改**
（换实现只改 `zhiyin_boot/container/gateways.py` 的装配表）。

为什么生成与嵌入放在同一个抽屉
------------------------------
两者是**两条独立的技术链路**（不同供应商、不同配额、不同版本策略），但同属
"模型"这一类外部能力，而且换模型时的动作都是"换一个实现 + 可能改一次嵌入版本"。
契约上也已经分开（`LLMGateway` / `EmbedGateway`），放在同一目录不会让它们混用。

若是走 pami 平台提供的模型，那属于 `pami/` 抽屉（平台适配），不要写在本目录：
本目录是"直连模型供应商"的那一套。

待实现的 Port 清单（唯一事实来源是 `zhiyin_data_sdk/gateways/ai.py`）
------------------------------------------------------------------
| Port | 契约文件 | 第一期本地实现 | 装配位 |
| --- | --- | --- | --- |
| `LLMGateway` | `gateways/ai.py` | `local/llm.py::LocalOrMockLLM` | `gateways.llm` |
| `EmbedGateway` | `gateways/ai.py` | `local/embedding.py::LocalHashEmbedder`（**skeleton**） | `gateways.embedding` |

开工前必须满足的条件
--------------------
1. **产出契约校验不许绕过**：模型返回必须仍交给编排层的 `ContractAgentEngine`
   做 Schema 校验；校验失败时的降级由调用方决定，不能在实现里"顺手改成返回空"。
2. **嵌入必须带模型标识**：`EmbedGateway.model_id` 是检索隔离的依据——
   与 `pgvector/` 的实现配合，保证换模型后旧向量与新查询不在同一空间。
3. **降级要显式**：`LLMResult.degraded` 标出"走了降级"，产品侧据此显示
   Mock / 降级来源标注（第一期硬约束：不得让 Mock 结论被误读为真实能力）。
4. **契约测试**：在 `tests/contracts/conftest.py` 的 `GATEWAY_FACTORIES` 里加一行，
   让同一套语义断言也跑新实现。
"""

