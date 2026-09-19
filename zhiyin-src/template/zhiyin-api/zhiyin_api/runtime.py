"""运行时装配状态（只读）。

为什么放在 api 层：`/healthz` 需要回答"哪些部件真的装上了、哪些还是骨架"，
但 api 不允许 import `zhiyin-boot`（会构成反向依赖）。因此约定：

- `zhiyin-boot` 在 wire 阶段构造一份 `AssemblyReport` 并调用 `configure_runtime()`；
- api 只读这份报告，不认识 boot 的任何类型。

这样 §九 验收项 8「骨架隔离」变得可观测：healthz 会列出所有仍走本地/默认通过
实现的部件，以及第一期已知的功能缺口。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# 部件状态取值
WIRED = "wired"
SKELETON = "skeleton"
NOT_WIRED = "not_wired"


@dataclass
class AssemblyReport:
    """一次启动的装配快照。

    分组与装配清单（`zhiyin_boot.container.ports`）一一对应：
    Gateways / Repositories / Transactions / Orchestration / Services / Workers。
    """

    env: str = "local"
    gateways: dict[str, str] = field(default_factory=dict)
    repositories: dict[str, str] = field(default_factory=dict)
    transactions: dict[str, str] = field(default_factory=dict)
    orchestration: dict[str, str] = field(default_factory=dict)
    services: dict[str, str] = field(default_factory=dict)
    workers: dict[str, str] = field(default_factory=dict)
    missing: list[str] = field(default_factory=list)
    skeletons: list[str] = field(default_factory=list)
    placeholders: list[str] = field(default_factory=list)
    """装上了、但实现是**占位**的能力位（当前只会是 `llm`）。

    与 `skeletons` / `missing` 是三件事：`missing` = 外壳都没有；`skeleton` = 外壳
    有了但方法体没填；`placeholders` = 实现完整、能跑通产出契约，但**产出内容不是
    真的**（例如按 Schema 合成结果的本地模型）。后者的危险在于它看起来一切正常，
    所以必须单独成一类，不能混进 `wired`。
    """

    @property
    def serves_fabricated_content(self) -> bool:
        """是否在对外提供**虚构内容**（占位实现）。供 `/healthz` 降级使用。"""
        return bool(self.placeholders)

    @property
    def healthy(self) -> bool:
        """没有任何部件处于 not_wired 才算健康。

        注意：`healthy` **不**把 skeleton 算作不健康（第一期允许骨架存在，门禁按
        里程碑分级判断）。"骨架有多少、分别属于谁"看 `skeletons`——它回答的是
        "外壳铺好了但能力还没接"，与 not_wired 的"外壳都没有"是两件事。
        """
        groups = (
            self.gateways,
            self.repositories,
            self.transactions,
            self.orchestration,
            self.services,
            self.workers,
        )
        return not any(NOT_WIRED in group.values() for group in groups)

    def to_dict(self) -> dict:
        return {
            "env": self.env,
            "healthy": self.healthy,
            "gateways": dict(self.gateways),
            "repositories": dict(self.repositories),
            "transactions": dict(self.transactions),
            "orchestration": dict(self.orchestration),
            "services": dict(self.services),
            "workers": dict(self.workers),
            "missing": list(self.missing),
            "skeletons": list(self.skeletons),
            "placeholders": list(self.placeholders),
        }


_report: Optional[AssemblyReport] = None


def configure_runtime(report: AssemblyReport) -> None:
    """由 zhiyin-boot 在启动时调用。"""
    global _report
    _report = report


def get_runtime() -> AssemblyReport:
    """读取装配报告。未装配时返回空报告，healthz 仍可用。"""
    return _report if _report is not None else AssemblyReport()


def reset_runtime() -> None:
    """清空装配报告。供测试隔离使用，业务代码不应调用。"""
    global _report
    _report = None
