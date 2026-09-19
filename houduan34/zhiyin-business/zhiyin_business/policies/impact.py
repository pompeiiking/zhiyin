"""影响面传播规则（FR-ORCH-004 / R-BIZ-012）—— 实现交付（第二波 · 后端-4）。

核心规则：画像字段更新 → 只重算**受影响的**资产片段 → 版本 +1 → 写 diff，
禁止整篇重新生成。

本模块只回答"哪些资产受影响"（重算范围），执行重算的是资产服务 /
ImpactPropagationWorker（不在本任务范围）。把范围判定与执行分开，
是为了让"只重算受影响片段"这条口径可以被独立单测。

实现口径（对着已冻结 ABC 交付）：
- `DependencyImpactPolicy` 是**纯函数规则**：无构造依赖、无 IO；
  `depends_on_profile_keys` 是影响面判定的唯一依据（见
  `zhiyin_kernel/blackboard.py::AssetVersion` 的字段说明）；
- 未命中的资产必须原样保留——本实现直接不把它们放进返回列表，
  既不重算也不升版本，调用方无需再做二次过滤；
- 判定方式是最朴素的集合交集：第一期不引入模糊匹配 / 相似度，
  "命中就是命中"让影响面可解释、可单测（可解释性是产品硬要求）。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence

from zhiyin_kernel.blackboard import AssetVersion


class ImpactPolicy(ABC):
    """资产重算范围判定规则。"""

    @abstractmethod
    def select_affected(
        self,
        *,
        changed_profile_keys: Sequence[str],
        candidates: Sequence[AssetVersion],
    ) -> list[AssetVersion]:
        """从候选资产中挑出依赖命中变更字段的那些。

        `candidates` 是各资产类型的最新版本；未命中的资产必须原样保留，
        既不重算也不升版本。
        """


class DependencyImpactPolicy(ImpactPolicy):
    """影响面判定：依赖字段集合与变更字段集合的交集。"""

    def select_affected(
        self,
        *,
        changed_profile_keys: Sequence[str],
        candidates: Sequence[AssetVersion],
    ) -> list[AssetVersion]:
        changed = set(changed_profile_keys)
        return [
            asset
            for asset in candidates
            if changed.intersection(asset.depends_on_profile_keys)
        ]


__all__ = ["DependencyImpactPolicy", "ImpactPolicy"]
