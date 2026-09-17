"""M3 关键词 + pgvector 的 RRF 混合检索实现。"""

from __future__ import annotations

from collections.abc import Sequence
import time
from typing import Any

from zhiyin_data_sdk.gateways.ai import EmbedGateway, SearchGateway, SearchHit
from zhiyin_data_sdk.gateways.vector import VectorGateway


class RrfHybridSearchGateway(SearchGateway):
    """用 Reciprocal Rank Fusion 合并关键词与向量结果。

    任一通道不可用时降级到另一通道；命中 metadata 会保留通道排名，便于离线评估。
    """

    IMPLEMENTATION_STATUS = "wired"

    def __init__(
        self,
        keyword_gateway: SearchGateway,
        embedding: EmbedGateway,
        vector_gateway: VectorGateway,
        *,
        namespace: str = "theory",
        rrf_k: int = 60,
        candidate_multiplier: int = 3,
        audit: Any | None = None,
        org_id: str = "default",
    ) -> None:
        if rrf_k <= 0 or candidate_multiplier <= 0:
            raise ValueError("rrf_k 与 candidate_multiplier 必须为正数")
        self._keyword = keyword_gateway
        self._embedding = embedding
        self._vector_gateway = vector_gateway
        self._namespace = namespace
        self._rrf_k = rrf_k
        self._candidate_multiplier = candidate_multiplier
        self._audit = audit
        self._org_id = org_id

    def configure_audit(self, audit: Any, *, org_id: str) -> None:
        self._audit = audit
        self._org_id = org_id

    async def keyword(self, query: str, *, top_k: int = 10) -> list[SearchHit]:
        return await self._keyword.keyword(query, top_k=top_k)

    async def vector(
        self, embedding: list[float], *, top_k: int = 10
    ) -> list[SearchHit]:
        hits = await self._vector_gateway.search(
            self._namespace,
            embedding,
            model=self._embedding.model_id,
            top_k=top_k,
        )
        return [
            SearchHit(
                id=hit.id,
                content=hit.text,
                score=hit.score,
                metadata={**hit.metadata, "source_id": hit.source_id},
            )
            for hit in hits
        ]

    async def hybrid(self, query: str, *, top_k: int = 10) -> list[SearchHit]:
        started = time.perf_counter()
        if top_k <= 0:
            return []
        candidate_count = min(100, top_k * self._candidate_multiplier)
        keyword_hits: Sequence[SearchHit] = []
        vector_hits: Sequence[SearchHit] = []
        degraded: list[str] = []
        try:
            keyword_hits = await self.keyword(query, top_k=candidate_count)
        except Exception:
            degraded.append("keyword")
        try:
            embeddings = await self._embedding.embed([query])
            if len(embeddings) != 1:
                raise ValueError("嵌入返回数量与输入不一致")
            vector_hits = await self.vector(embeddings[0], top_k=candidate_count)
        except Exception:
            degraded.append("vector")
        if len(degraded) == 2:
            raise RuntimeError("关键词与向量检索通道均不可用")
        result = self._fuse(keyword_hits, vector_hits, top_k=top_k, degraded=degraded)
        if self._audit is not None:
            await self._audit.record(
                org_id=self._org_id,
                namespace=self._namespace,
                channel="hybrid",
                top_k=top_k,
                source_ids=[str(hit.metadata.get("source_id") or hit.id) for hit in result],
                latency_ms=int((time.perf_counter() - started) * 1000),
                degraded=bool(degraded),
                query=query,
            )
        return result

    def _fuse(
        self,
        keyword_hits: Sequence[SearchHit],
        vector_hits: Sequence[SearchHit],
        *,
        top_k: int,
        degraded: Sequence[str],
    ) -> list[SearchHit]:
        merged: dict[str, SearchHit] = {}
        ranks: dict[str, dict[str, int]] = {}
        scores: dict[str, float] = {}
        for channel, hits in (("keyword", keyword_hits), ("vector", vector_hits)):
            for rank, hit in enumerate(hits, start=1):
                merged.setdefault(hit.id, hit)
                ranks.setdefault(hit.id, {})[channel] = rank
                scores[hit.id] = scores.get(hit.id, 0.0) + 1.0 / (self._rrf_k + rank)
                if not merged[hit.id].content and hit.content:
                    merged[hit.id] = hit
        ordered = sorted(merged, key=lambda item_id: (-scores[item_id], item_id))[:top_k]
        return [
            merged[item_id].model_copy(
                update={
                    "score": scores[item_id],
                    "metadata": {
                        **merged[item_id].metadata,
                        "retrieval": {
                            "algorithm": "rrf",
                            "ranks": ranks[item_id],
                            "degraded_channels": list(degraded),
                        },
                    },
                }
            )
            for item_id in ordered
        ]


__all__ = ["RrfHybridSearchGateway"]
