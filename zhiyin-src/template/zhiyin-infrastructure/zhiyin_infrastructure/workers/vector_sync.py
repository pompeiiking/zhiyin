"""向量同步 / 嵌入补偿 Worker（**骨架**，方法体未实现）。

落位：`infrastructure/workers/vector_sync.py` —— 基础设施负责人（纯数据管道）。
依赖：`KnowledgeGateway`（知识源）+ `EmbedGateway`（嵌入）+ `VectorGateway`（向量库）。

为什么在基础设施层而不是 `business/workers/`
-------------------------------------------
《目标架构设计》§5.4 的分家口径：**"什么情况该重算"是业务规则，"把文档写进向量库"
是纯数据管道**。

- 业务侧 Worker（`impact` / `active_event`）需要判断阈值、冷却期、打扰上限，
  读 `data/registry/policy_params.json` —— 那是业务规则；
- 本 Worker 只做"读取待同步文档 → 嵌入 → 落向量库 → 记账"，不含任何职引业务语义。

基类来自内核
------------
基础设施层**不能**继承业务侧基类（依赖矩阵禁止 infra → business），
两边共享的唯一契约是 `zhiyin_kernel.worker.Worker`（只有 `name` + `run_once`）。
驱动（轮询 / lifespan 启停 / 独立进程）在 `zhiyin_boot/workers.py`，本类不含循环。

幂等要求
--------
同一批文档可能被重复投递，`run_once` 必须可重入（按 doc_id + 模型版本去重 upsert），
否则每次补偿都会把向量库写大一圈。

接入方式：实现后在 `zhiyin_boot/container/services.py::build_workers` 注册一行，
`--check` 随即把 `workers.vector_sync` 从 `not_wired` 变为 `wired`；
独立部署用 `python -m zhiyin_boot worker vector_sync`，**部署形态变了，代码不变**。
"""

from __future__ import annotations

from zhiyin_data_sdk.gateways.ai import EmbedGateway, KnowledgeGateway
from zhiyin_data_sdk.gateways.vector import VectorGateway
from zhiyin_kernel.worker import Worker

_TODO = "TODO(骨架): VectorSyncWorker 未实现"


class VectorSyncWorker(Worker):
    """向量同步执行者（骨架）。"""

    name = "vector_sync"
    IMPLEMENTATION_STATUS = "skeleton"

    def __init__(
        self,
        knowledge: KnowledgeGateway,
        embedding: EmbedGateway,
        vector: VectorGateway,
    ) -> None:
        self._knowledge = knowledge
        self._embedding = embedding
        self._vector = vector

    async def run_once(self) -> int:
        """同步一轮待嵌入 / 待重嵌入的文档，返回本轮处理条数（0 = 无待处理）。"""
        raise NotImplementedError(
            f"{_TODO}：扫待同步文档 → EmbedGateway 嵌入 → VectorGateway upsert（按 "
            "doc_id + 模型版本幂等）"
        )


__all__ = ["VectorSyncWorker"]
