"""五环节产出契约集合。

这五个模型就是"产出契约"的业务侧定义。编排层只持有它们的 JSON Schema
（OutputContractSpec.json_schema）做通用校验，不感知业务字段含义，
从而同时满足 R-ORC-001（编排层无业务语义）与 R-ORC-002（必须校验产出契约）。
"""

from zhiyin_business.contracts.common import (
    AgentBadge,
    AssetUpdateDraft,
    BehaviorEventDraft,
    BehaviorGuide,
    ConversationMessage,
    Disclosure,
    Evidence,
    GuideOption,
    GuideReminder,
    GuideTask,
    TheoryRef,
)
from zhiyin_business.contracts.collect import CollectOutput, FieldUpdate
from zhiyin_business.contracts.diagnose import (
    DiagnoseGap,
    DiagnoseOutput,
    FactItem,
)
from zhiyin_business.contracts.decide import DecideOutput, PlanOption
from zhiyin_business.contracts.act import ActOutput, NodeReminder
from zhiyin_business.contracts.review import (
    ProgressSnapshot,
    ReviewOutput,
)

__all__ = [
    "AgentBadge",
    "AssetUpdateDraft",
    "BehaviorEventDraft",
    "BehaviorGuide",
    "ConversationMessage",
    "Disclosure",
    "Evidence",
    "GuideOption",
    "GuideReminder",
    "GuideTask",
    "TheoryRef",
    "CollectOutput",
    "FieldUpdate",
    "DiagnoseGap",
    "DiagnoseOutput",
    "FactItem",
    "DecideOutput",
    "PlanOption",
    "ActOutput",
    "NodeReminder",
    "ProgressSnapshot",
    "ReviewOutput",
]
