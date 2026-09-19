"""第三期 RAG 跨层共享数据形状。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from zhiyin_kernel.enums import LoopStage, RetrievalNamespace


RetrievalMode = Literal["keyword", "vector", "hybrid"]


class RetrievalQuery(BaseModel):
    """一个知识域内可独立执行的检索请求。"""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1)
    namespace: RetrievalNamespace
    mode: RetrievalMode = "hybrid"
    top_k: int = Field(default=5, ge=1, le=100)
    filters: dict[str, Any] = Field(default_factory=dict)
    org_id: str = ""
    user_id: str = ""
    trace_id: str = ""


class RetrievalPlan(BaseModel):
    """五环节根据本轮上下文生成的确定性检索计划。"""

    model_config = ConfigDict(extra="forbid")

    stage: LoopStage
    intent: str = ""
    question: str
    required: bool
    queries: list[RetrievalQuery] = Field(default_factory=list)
    reason: str = ""


class RetrievalEvidence(BaseModel):
    """统一检索命中；替代 KnowledgeHit/SearchHit 的重复形状。"""

    model_config = ConfigDict(extra="forbid")

    evidence_id: str
    namespace: RetrievalNamespace
    content: str
    score: float = 0.0
    title: str = ""
    source_id: str = ""
    source_url: str = ""
    version: int = Field(default=1, ge=1)
    updated_at: Optional[datetime] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidencePacket(BaseModel):
    """交给模型前的证据包，保留来源、降级和模型版本。"""

    model_config = ConfigDict(extra="forbid")

    stage: LoopStage
    question: str
    evidences: list[RetrievalEvidence] = Field(default_factory=list)
    channels: list[str] = Field(default_factory=list)
    degraded_channels: list[str] = Field(default_factory=list)
    model_version: str = ""
    trace_id: str = ""


__all__ = [
    "EvidencePacket",
    "RetrievalEvidence",
    "RetrievalMode",
    "RetrievalPlan",
    "RetrievalQuery",
]
