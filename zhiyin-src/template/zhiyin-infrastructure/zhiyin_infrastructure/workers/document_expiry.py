"""检索文档过期下架 Worker（JD 等高时效内容的治理执行者）。

落位：`zhiyin-infrastructure/workers/document_expiry.py`。

为什么放在基础设施层而不是业务层：这是一条**纯数据治理管道**——扫描权威文档表，
把已过截止时间的行落成 `expired`，不做任何业务判断、不需要配置阈值、不发通知。
《AGENTS.md》§3 的落位规则是"业务规则驱动的后台执行进 business/workers，
纯数据管道进 infrastructure/workers"，本类属后者（与 `vector_sync` 同类）。

背景（《第三期 RAG 检索内容与检索流程设计》§4.3）：
JD 默认是高时效内容，**已过截止时间、来源下架、连续复核失败的记录必须标记 `expired`**，
不得作为"现在可以申请"的证据；历史 JD 可保留用于要求分析，但要明确标记为历史样本。

三条触发里本类实现两条：
1. **已过截止时间** —— `run_once()` 扫全表，见 `RetrievalDocumentStore.expire_due`；
2. **来源下架** —— 采集/治理流程调用 `RetrievalDocumentStore.expire_by_source`，
   不由本 Worker 定时猜测（来源是否下架是采集侧的事实，不是时间函数）。

第三条（**连续复核失败**）**未实现**：它依赖"复核"这条流程本身，而招聘来源的
条款/robots/频率/保存期审核尚未完成（见待决问题 D7 的待确认项）。在复核机制落地前
实现它只能靠猜，故留空并在此写明，不做一个看起来有、实际没有的东西。
"""

from __future__ import annotations

import asyncio

from zhiyin_infrastructure.persistence.retrieval_documents import RetrievalDocumentStore
from zhiyin_kernel.worker import Worker


class DocumentExpiryWorker(Worker):
    """定时把已过截止时间的检索文档落成 `expired`。"""

    name = "document_expiry"
    IMPLEMENTATION_STATUS = "wired"

    def __init__(self, documents: RetrievalDocumentStore) -> None:
        self._documents = documents

    async def run_once(self) -> int:
        """扫描一轮，返回本轮标记为过期的文档数（0 = 没有到期的）。

        `RetrievalDocumentStore` 是同步 SQLAlchemy 存储，放进线程执行：
        直接在事件循环里做批量 UPDATE 会阻塞整个进程的其它协程。
        """
        expired = await asyncio.to_thread(self._documents.expire_due)
        return len(expired)


__all__ = ["DocumentExpiryWorker"]
