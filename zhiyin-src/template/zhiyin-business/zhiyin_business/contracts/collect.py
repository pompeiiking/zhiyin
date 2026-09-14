"""① 采集建模产出契约（FR-COLLECT）。

验收锚点：目标不是"问完 6 个问题"，而是"画像置信度提升"。
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from zhiyin_kernel.blackboard import ProfileGap
from zhiyin_kernel.enums import ProfileSource
from zhiyin_business.contracts.common import (
    BehaviorGuide,
    Disclosure,
    TheoryRef,
)


class FieldUpdate(BaseModel):
    """一次采集对画像字段的更新。"""

    model_config = ConfigDict(extra="forbid")

    key: str
    value: object = Field(description="字段值，结构由画像 schema 决定")
    confidence: float = Field(ge=0.0, le=1.0)
    source: ProfileSource
    evidence: list[str] = Field(default_factory=list)


class CollectOutput(BaseModel):
    """① 采集建模的产出契约。"""

    model_config = ConfigDict(extra="forbid")

    field_updates: list[FieldUpdate] = Field(default_factory=list)
    remaining_gaps: list[ProfileGap] = Field(default_factory=list)
    confidence_overall: float = Field(
        default=0.0, ge=0.0, le=1.0, description="画像整体置信度，用于判定是否可交接"
    )
    ready_to_handoff: bool = Field(
        default=False, description="是否达到目标环节所需最低置信度（FR-COLLECT-007）"
    )
    theory_refs: list[TheoryRef] = Field(default_factory=list)
    guide: BehaviorGuide = Field(description="下一步：一次一问的追问")
    disclosure: Disclosure | None = None
