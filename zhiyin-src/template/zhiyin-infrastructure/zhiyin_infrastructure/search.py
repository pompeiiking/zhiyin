"""M3 关键词 + pgvector 的 RRF 混合检索实现。"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import time
from typing import Any

from zhiyin_data_sdk.gateways.ai import EmbedGateway, SearchGateway
from zhiyin_data_sdk.gateways.vector import VectorGateway
from zhiyin_kernel.retrieval import RetrievalEvidence, RetrievalQuery


def _qualified(namespace: str, record_id: str) -> str:
    """把向量库的记录 id 规范成 `namespace:id`（D11）。

    为什么在**读**的时候做、而不是只改写入方：向量库里可能已经存在裸 id 的行
    （历史数据），读时兜底才能立刻让两通道对同一篇文档用同一个键，RRF 去重才成立。

    幂等：已经是 `namespace:` 前缀的（新写入或平台侧自带）不再叠加，避免出现
    `theory:theory:x`。
    """
    prefix = f"{namespace}:"
    return record_id if record_id.startswith(prefix) else f"{prefix}{record_id}"


class RrfHybridSearchGateway(SearchGateway):
    """用 Reciprocal Rank Fusion 合并关键词与向量结果。

    任一通道不可用时降级到另一通道；命中 metadata 会保留通道排名，便于离线评估。

    ⚠️ 降级必须能**分辨原因**，否则排查会被自己骗
    ------------------------------------------------
    只记"vector 通道降级了"是不够的：向量维度不匹配（`ValidationError`，配置/模型换版
    导致）与连不上向量库（`UnavailableError`）在结果里长得一模一样，而处置动作完全
    不同。因此除 `degraded_channels` 外还写 `degraded_reasons`。

    这里**只写异常类名，不写异常消息**：异常文本可能带上 DSN、口令或上游地址，而
    检索 metadata 会随报告与接口响应外流（《AGENTS.md》§10 禁止秘密进入日志、
    动态资源与响应）。类名已足够区分"配置错"与"连不上"，需要细节时按类名去查日志。

    ⚠️ 还有第二种"静默变空"：权威回填把命中丢光（D13）
    --------------------------------------------------
    有 authority 时，命中必须能在权威库里找到才算数。权威表为空时**每一条**都会被
    丢掉，于是返回空列表——而它与"确实没有命中"完全同形（`degraded=False`、审计与
    `/healthz` 都正常）。现在丢弃量会进入 (`retrieval.dropped_non_authoritative`)
    与审计的 `degraded`，至少让"空结果到底是没内容还是被门挡掉"可分辨。
    """

    IMPLEMENTATION_STATUS = "wired"

    def __init__(
        self,
        keyword_gateway: SearchGateway,
        embedding: EmbedGateway,
        vector_gateway: VectorGateway,
        *,
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
        self._rrf_k = rrf_k
        self._candidate_multiplier = candidate_multiplier
        self._audit = audit
        self._authority: Any | None = None
        self._org_id = org_id

    def configure_audit(self, audit: Any, *, org_id: str) -> None:
        self._audit = audit
        self._org_id = org_id

    @property
    def serves_demo_content(self) -> bool:
        """任一内部通道提供演示语料即算（D12）。

        **包装类必须透传这个信号**：容器里装配的 `search` 是本类（不是
        `LocalSearchGateway`），如果只让被包装的通道自己有这个属性，装配报告就会
        漏报——那正是 D12 想解决的"系统不知道内容是演示的"。
        """
        return any(
            getattr(channel, "serves_demo_content", False)
            for channel in (self._keyword, self._embedding, self._vector_gateway)
        )

    def configure_authority(self, authority: Any) -> None:
        """注入 Infrastructure 内部的权威数据回填器，不新增跨层 Port。"""
        self._authority = authority

    async def _vector(
        self, request: RetrievalQuery, embedding: list[float]
    ) -> list[RetrievalEvidence]:
        hits = await self._vector_gateway.search(
            request.namespace.value,
            embedding,
            model=self._embedding.model_id,
            top_k=request.top_k,
            filters=request.filters or None,
        )
        return [
            RetrievalEvidence(
                evidence_id=_qualified(request.namespace.value, hit.id),
                namespace=request.namespace,
                content=hit.text,
                score=hit.score,
                source_id=hit.source_id,
                source_url=str(hit.metadata.get("source_url") or ""),
                version=max(int(hit.metadata.get("version") or 1), 1),
                metadata={**hit.metadata, "source_id": hit.source_id},
            )
            for hit in hits
        ]

    async def search(self, request: RetrievalQuery) -> list[RetrievalEvidence]:
        started = time.perf_counter()
        candidate_count = min(100, request.top_k * self._candidate_multiplier)
        candidate_request = request.model_copy(update={"top_k": candidate_count})
        keyword_hits: Sequence[RetrievalEvidence] = []
        vector_hits: Sequence[RetrievalEvidence] = []
        degraded: list[str] = []
        reasons: dict[str, str] = {}
        if request.mode in {"keyword", "hybrid"}:
            try:
                keyword_hits = await self._keyword.search(
                    candidate_request.model_copy(update={"mode": "keyword"})
                )
            except Exception as exc:
                degraded.append("keyword")
                reasons["keyword"] = type(exc).__name__
        if request.mode in {"vector", "hybrid"}:
            try:
                embeddings = await self._embedding.embed([request.query])
                if len(embeddings) != 1:
                    raise ValueError("嵌入返回数量与输入不一致")
                vector_hits = await self._vector(candidate_request, embeddings[0])
            except Exception as exc:
                degraded.append("vector")
                reasons["vector"] = type(exc).__name__
        expected = {"hybrid": 2, "keyword": 1, "vector": 1}[request.mode]
        if len(degraded) == expected:
            raise RuntimeError("请求的检索通道均不可用")
        result = self._fuse(
            keyword_hits,
            vector_hits,
            top_k=request.top_k,
            degraded=degraded,
            reasons=reasons,
        )
        dropped_any = False
        if self._authority is not None:
            outcome = await self._authority.hydrate(request, result)
            result = outcome.hits
            dropped_any = bool(outcome.dropped)
            if outcome.dropped:
                # 权威回填把命中丢掉了（D13）。必须让它**可识别**：权威表为空时
                # 每一条都会被丢掉，调用方只会看到一个空列表——与"确实没命中"
                # 完全同形。这里把丢弃量写进 (a) 幸存命中的 metadata、(b) 审计。
                # 一条都没幸存时 (a) 无处可写，只能靠审计——所以 (b) 是主通道。
                result = [
                    hit.model_copy(
                        update={
                            "metadata": {
                                **hit.metadata,
                                "retrieval": {
                                    **hit.metadata.get("retrieval", {}),
                                    "dropped_non_authoritative": outcome.dropped,
                                },
                            }
                        }
                    )
                    for hit in result
                ]
        if self._audit is not None:
            # 审计里要能看出**是哪种降级**（D13 残留）：通道故障去查通道/平台，
            # 命中被权威门丢则去查权威表有没有内容——处置动作不同。
            reasons_log = []
            if degraded:
                reasons_log.append("channels")
            if dropped_any:
                reasons_log.append("authority_drop")
            await self._audit.record(
                org_id=request.org_id or self._org_id,
                namespace=request.namespace.value,
                channel=request.mode,
                top_k=request.top_k,
                source_ids=[hit.source_id or hit.evidence_id for hit in result],
                latency_ms=int((time.perf_counter() - started) * 1000),
                degraded=bool(reasons_log),
                degraded_reason="+".join(reasons_log),
                query=request.query,
            )
        return result

    def _fuse(
        self,
        keyword_hits: Sequence[RetrievalEvidence],
        vector_hits: Sequence[RetrievalEvidence],
        *,
        top_k: int,
        degraded: Sequence[str],
        reasons: Mapping[str, str] | None = None,
    ) -> list[RetrievalEvidence]:
        merged: dict[str, RetrievalEvidence] = {}
        ranks: dict[str, dict[str, int]] = {}
        scores: dict[str, float] = {}
        for channel, hits in (("keyword", keyword_hits), ("vector", vector_hits)):
            for rank, hit in enumerate(hits, start=1):
                item_id = hit.evidence_id
                merged.setdefault(item_id, hit)
                ranks.setdefault(item_id, {})[channel] = rank
                scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (self._rrf_k + rank)
                if not merged[item_id].content and hit.content:
                    merged[item_id] = hit
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
                            "degraded_reasons": dict(reasons or {}),
                        },
                    },
                }
            )
            for item_id in ordered
        ]


__all__ = ["RrfHybridSearchGateway"]