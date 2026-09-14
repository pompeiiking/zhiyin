"""功能块服务实现（**骨架**，方法体未实现）。

落位：`business/services/function.py` —— 业务编排负责人。
依赖：`ObjectStoreGateway`、资产 / 行为 Port；日历与成就的落库走 Repository。

第一期形态（《第一期技术架构文档》§二）：报告全文 P0、日历 P0 登记、
成就 P0 只由行为日志驱动、导出占位、导师占位、演示只读。

两条不要越界的口径：
- 报告全文**只读资产版本**，不重新生成；
- 成就**只由行为日志驱动**，不做登录 / 浏览型徽章（防自嗨）。
"""

from __future__ import annotations

from typing import Literal, Optional

from zhiyin_business.ports.blackboard import AssetService, BehaviorService
from zhiyin_business.ports.function import DemoScript, ExportResult, FunctionService
from zhiyin_data_sdk.gateways.storage import ObjectStoreGateway
from zhiyin_kernel.assets import Achievement, CalendarNode, TrackEvent

_TODO = "TODO(骨架): FunctionService 未实现"


class DefaultFunctionService(FunctionService):
    """功能块服务默认实现（骨架）。"""

    IMPLEMENTATION_STATUS = "skeleton"

    def __init__(
        self,
        *,
        assets: AssetService,
        behaviors: BehaviorService,
        object_store: ObjectStoreGateway,
    ) -> None:
        self._assets = assets
        self._behaviors = behaviors
        self._object_store = object_store

    async def get_report_full_text(
        self, user_id: str, version: Optional[int] = None
    ) -> dict:
        raise NotImplementedError(f"{_TODO}：报告全文（只读资产版本，不重新生成）")

    async def export_asset(
        self, user_id: str, asset_type: str, fmt: Literal["pdf", "docx"]
    ) -> ExportResult:
        raise NotImplementedError(f"{_TODO}：导出占位（available 恒 False）")

    async def list_calendar_nodes(self, user_id: str) -> list[CalendarNode]:
        raise NotImplementedError(f"{_TODO}：读关键节点日历")

    async def write_calendar_node(self, user_id: str, node: CalendarNode) -> CalendarNode:
        raise NotImplementedError(f"{_TODO}：写节点（规划师写、教练读）")

    async def list_achievements(self, user_id: str) -> list[Achievement]:
        raise NotImplementedError(f"{_TODO}：读成就（只由行为日志驱动解锁）")

    async def list_track_events(self, user_id: str) -> list[TrackEvent]:
        raise NotImplementedError(f"{_TODO}：读跟踪时间线（工作台 ⑤ 层）")

    async def get_demo_script(self) -> DemoScript:
        raise NotImplementedError(f"{_TODO}：取自动演示脚本（只读演示数据）")


__all__ = ["DefaultFunctionService"]
