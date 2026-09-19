"""向量同步、重嵌入与删除补偿 Worker。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from zhiyin_data_sdk.gateways.ai import EmbedGateway
from zhiyin_data_sdk.gateways.vector import VectorGateway, VectorRecord
from zhiyin_infrastructure.persistence.embed_tasks import EmbedTaskStore
from zhiyin_kernel.worker import Worker


class VectorSyncWorker(Worker):
    """从关系库领取任务并幂等写入 pgvector。"""

    name = "vector_sync"
    IMPLEMENTATION_STATUS = "wired"

    def __init__(
        self,
        tasks: EmbedTaskStore,
        embedding: EmbedGateway,
        vector: VectorGateway,
        *,
        batch_size: int = 50,
    ) -> None:
        self._tasks = tasks
        self._embedding = embedding
        self._vector = vector
        self._batch_size = batch_size

    async def run_once(self) -> int:
        claimed = await self._tasks.claim(limit=self._batch_size)
        completed = 0
        for task in claimed:
            try:
                if task.operation == "delete":
                    await self._vector.delete(task.namespace, [task.source_id])
                else:
                    if task.model != self._embedding.model_id:
                        raise ValueError(
                            f"任务模型 {task.model} 与当前模型 {self._embedding.model_id} 不一致"
                        )
                    vectors = await self._embedding.embed([task.text])
                    if len(vectors) != 1:
                        raise ValueError("嵌入返回数量与任务数量不一致")
                    await self._vector.upsert(
                        task.namespace,
                        [
                            VectorRecord(
                                id=task.source_id,
                                vector=vectors[0],
                                text=task.text,
                                source_id=task.source_id,
                                metadata={
                                    **task.metadata,
                                    "content_hash": task.content_hash,
                                },
                            )
                        ],
                        model=task.model,
                    )
                await self._tasks.succeed(task.id)
                completed += 1
            except Exception as exc:
                await self._tasks.fail(task.id, exc)
        return completed


class VectorSyncPlanner:
    """把全量、增量和删除变更统一写入 ``embed_task``。"""

    def __init__(
        self,
        tasks: EmbedTaskStore,
        vector: VectorGateway,
        *,
        model: str,
    ) -> None:
        self._tasks = tasks
        self._vector = vector
        self._model = model

    async def schedule_incremental(
        self, namespace: str, documents: list[dict[str, Any]]
    ) -> int:
        queued = 0
        for document in documents:
            source_id = str(document.get("id") or "").strip()
            if not source_id:
                raise ValueError("向量文档必须包含稳定 id")
            text = "\n".join(
                str(document.get(field) or "").strip()
                for field in ("title", "summary", "content")
                if document.get(field)
            )
            content_hash = str(document.get("content_hash") or "") or hashlib.sha256(
                json.dumps(document, ensure_ascii=False, sort_keys=True).encode("utf-8")
            ).hexdigest()
            await self._tasks.enqueue(
                namespace=namespace,
                source_id=source_id,
                model=self._model,
                content_hash=content_hash,
                text=text,
                metadata={
                    key: document[key]
                    # `status` / `user_id` 必须带上：检索计划会给查询带
                    # `filters={"status": "enabled"}`（私有域还带 user_id），而
                    # `PgVectorGateway` 是用 `metadata @> filters` 过滤的——向量行里
                    # 没有这些字段就会被**全部过滤掉**，表现为"向量通道 0 条"。
                    # 之前只透传来源字段，于是"权限/状态过滤"在向量通道上等于恒假。
                    for key in (
                        "source_id", "source_url", "fetched_at", "version",
                        "status", "user_id", "org_id",
                    )
                    if key in document
                },
            )
            queued += 1
        return queued

    async def schedule_full(self, namespace: str, knowledge_file: str | Path) -> int:
        payload = json.loads(Path(knowledge_file).read_text(encoding="utf-8"))
        documents = payload.get("items", payload) if isinstance(payload, dict) else payload
        if not isinstance(documents, list):
            raise ValueError("知识文件必须是数组或包含 items 的对象")
        await self._vector.clear_namespace(namespace)
        return await self.schedule_incremental(
            namespace,
            [item for item in documents if isinstance(item, dict) and item.get("status") == "enabled"],
        )

    async def schedule_delete(
        self, namespace: str, source_id: str, *, content_hash: str
    ) -> str:
        return await self._tasks.enqueue(
            namespace=namespace,
            source_id=source_id,
            model=self._model,
            content_hash=content_hash,
            operation="delete",
        )


__all__ = ["VectorSyncPlanner", "VectorSyncWorker"]
