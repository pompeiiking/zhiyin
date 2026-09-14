"""功能块契约（FR-BLOCK）。

功能块 = 能力池外的外围服务：报告全文/导出、关键节点日历、成就体系、
导师共享/建议、自动演示。不占主线导航，挂在资产与产出上。

第一期形态：
- 报告全文        → P0 实现（读资产版本）
- 导出            → P0 占位，P1 真实导出
- 日历            → P0 登记，规划师写入、教练读取
- 成就            → P0 静态，只由行为日志驱动
- 导师建议        → P2，第一期仅占位
- 自动演示        → P0，只读演示数据，不写真实黑板

注：`CalendarNode` 定义在 `zhiyin_kernel.assets`（因为它要落
`key_calendar_node` 表，基础设施层的表清单必须指向契约而不是业务模型），
本模块只做转出，业务规则（规划师写入、教练读取）仍在本层。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from zhiyin_kernel.assets import Achievement, CalendarNode, TrackEvent

__all__ = [
    "CalendarNode",
    "DemoScript",
    "ExportResult",
    "FunctionService",
]


class ExportResult(BaseModel):
    """导出结果。第一期返回占位。"""

    model_config = ConfigDict(extra="forbid")

    asset_type: str
    format: Literal["pdf", "docx"]
    object_key: Optional[str] = Field(default=None, description="对象存储键")
    available: bool = Field(default=False, description="第一期恒 False，标记为占位")
    message: str = Field(default="第一期仅预留导出入口")


class DemoScript(BaseModel):
    """自动演示脚本（FR-BLOCK-005）。

    覆盖主路径：首页 → 对话页三栏 → 工作台资产。
    """

    model_config = ConfigDict(extra="forbid")

    script_id: str
    name: str
    steps: list[str] = Field(default_factory=list)
    read_only: bool = Field(
        default=True, description="只读演示数据，不写真实黑板"
    )


class FunctionService(ABC):
    """功能块服务 Port。"""

    @abstractmethod
    async def get_report_full_text(self, user_id: str, version: Optional[int] = None) -> dict:
        """报告全文视图（FR-BLOCK-001）。读资产版本，不重新生成。"""

    @abstractmethod
    async def export_asset(
        self, user_id: str, asset_type: str, fmt: Literal["pdf", "docx"]
    ) -> ExportResult:
        """导出资产。第一期返回占位结果。"""

    @abstractmethod
    async def list_calendar_nodes(self, user_id: str) -> list[CalendarNode]:
        """读取关键节点日历。"""

    @abstractmethod
    async def write_calendar_node(self, user_id: str, node: CalendarNode) -> CalendarNode:
        """写入节点（规划师写、教练读）。"""

    @abstractmethod
    async def list_achievements(self, user_id: str) -> list[Achievement]:
        """读取成就。只由行为日志驱动解锁，不做登录/浏览型徽章。"""

    @abstractmethod
    async def list_track_events(self, user_id: str) -> list[TrackEvent]:
        """读取跟踪时间线（工作台 ⑤ 层）。"""

    @abstractmethod
    async def get_demo_script(self) -> DemoScript:
        """获取自动演示脚本。"""
