"""功能块服务实现。

落位：`business/services/function.py`；第一期排期实现工位：后端-2（数据访问负责人）。
依赖：`ObjectStoreGateway`、资产 / 行为 Port；日历与成就的落库走 Repository。

第一期形态（《第一期技术架构文档》§二）：报告全文 P0、日历 P0 登记、
成就 P0 只由行为日志驱动、导出占位、导师占位、演示只读。

两条不要越界的口径：
- 报告全文**只读资产版本**，不重新生成；
- 成就**只由行为日志驱动**，不做登录 / 浏览型徽章（防自嗨）。
"""

from __future__ import annotations

import asyncio
import json
from typing import Literal, Optional
from zhiyin_business.ports.blackboard import AssetService, BehaviorService
from zhiyin_business.ports.function import DemoScript, ExportResult, FunctionService
from zhiyin_data_sdk.gateways.storage import ObjectStoreGateway
from zhiyin_kernel.assets import Achievement, CalendarNode, TrackEvent
from zhiyin_kernel.enums import BehaviorEventType


_ACHIEVEMENT_BADGES = {
    BehaviorEventType.GAP_CLAIM: "first_gap_claimed",
    BehaviorEventType.DECISION_SELECT: "direction_selected",
    BehaviorEventType.DECISION_RESELECT: "direction_reselected",
    BehaviorEventType.TASK_DONE: "first_task_done",
    BehaviorEventType.REVIEW: "first_review_completed",
}


class DefaultFunctionService(FunctionService):
    """功能块服务默认实现。"""

    IMPLEMENTATION_STATUS = "wired"

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
        self._calendar_locks: dict[str, asyncio.Lock] = {}

    async def get_report_full_text(
        self, user_id: str, version: Optional[int] = None
    ) -> dict:
        report = await self._assets.get_report(user_id, version)
        if report is None:
            return {"available": False, "report": None, "message": "尚未生成诊断报告"}
        return {
            "available": True,
            "report": report.model_dump(mode="json"),
            "message": "",
        }

    async def export_asset(
        self, user_id: str, asset_type: str, fmt: Literal["pdf", "docx"]
    ) -> ExportResult:
        return ExportResult(
            asset_type=asset_type,
            format=fmt,
            available=False,
            object_key=None,
            message="第一期仅预留导出入口，未生成文件",
        )

    async def list_calendar_nodes(self, user_id: str) -> list[CalendarNode]:
        key = self._calendar_key(user_id)
        if await self._object_store.stat(key) is None:
            return []
        raw = json.loads((await self._object_store.get(key)).decode("utf-8"))
        nodes = [CalendarNode.model_validate(item) for item in raw.get("items", [])]
        nodes.sort(key=lambda item: (item.due_at is None, item.due_at, item.node_id))
        return nodes

    async def write_calendar_node(self, user_id: str, node: CalendarNode) -> CalendarNode:
        if node.user_id and node.user_id != user_id:
            raise PermissionError("不能为其他用户写入日历节点")
        stored = node.model_copy(update={"user_id": user_id})
        lock = self._calendar_locks.setdefault(user_id, asyncio.Lock())
        async with lock:
            key = self._calendar_key(user_id)
            for _ in range(32):
                metadata = await self._object_store.stat(key)
                nodes = await self.list_calendar_nodes(user_id)
                by_id = {item.node_id: item for item in nodes}
                by_id[stored.node_id] = stored
                payload = {
                    "items": [
                        item.model_dump(mode="json")
                        for item in sorted(by_id.values(), key=lambda item: item.node_id)
                    ]
                }
                saved = await self._object_store.compare_and_swap(
                    key,
                    json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                    expected_etag=metadata.etag if metadata is not None else None,
                    content_type="application/json",
                )
                if saved is not None:
                    return stored
                await asyncio.sleep(0)
        raise RuntimeError("日历并发写入冲突，请重试")

    async def list_achievements(self, user_id: str) -> list[Achievement]:
        logs = await self._behaviors.recent(user_id, limit=1000)
        first_by_badge = {}
        for log in reversed(logs):
            badge = _ACHIEVEMENT_BADGES.get(log.event_type)
            if badge is not None:
                first_by_badge.setdefault(badge, log.occurred_at)

        # P0 成就是行为日志的只读投影。读取不得反向写库，否则刷新页面也会
        # 变成“解锁行为”，破坏“只由真实行为驱动”的产品底线。
        return [
            Achievement(
                id=f"ach_{badge}_{user_id}",
                user_id=user_id,
                badge_key=badge,
                unlocked=True,
                unlocked_at=unlocked_at,
                driven_by_behavior_log_only=True,
            )
            for badge, unlocked_at in sorted(first_by_badge.items())
        ]

    async def list_track_events(self, user_id: str) -> list[TrackEvent]:
        logs = await self._behaviors.recent(
            user_id,
            event_types=[
                BehaviorEventType.TASK_DONE,
                BehaviorEventType.TASK_STALL,
                BehaviorEventType.REVIEW,
            ],
            limit=500,
        )
        # 跟踪时间线同样是行为事实的只读投影，不在 GET 路径制造第二份事实。
        return [
            TrackEvent(
                id=f"track_{log.id}",
                user_id=user_id,
                type=_track_presentation(log.event_type)[0],
                title=_track_presentation(log.event_type)[1],
                detail=str(log.payload.get("detail", "")),
                occurred_at=log.occurred_at,
                related_task_id=str(log.payload.get("task_id") or "") or None,
                related_stage=str(log.payload.get("stage") or "") or None,
            )
            for log in logs
        ]

    async def get_demo_script(self) -> DemoScript:
        return DemoScript(
            script_id="first-phase-main-path",
            name="第一期五环节演示",
            steps=[
                "从首页选择任务入口",
                "在对话页完成采集、诊断、决策、行动与复盘",
                "打开工作台查看画像、报告、方案、计划与跟踪时间线",
            ],
            read_only=True,
        )

    def _calendar_key(self, user_id: str) -> str:
        return self._object_store.build_key(user_id, "calendar", 1, "json")


def _track_presentation(event_type: BehaviorEventType) -> tuple[str, str]:
    if event_type is BehaviorEventType.TASK_DONE:
        return "milestone_done", "完成行动任务"
    if event_type is BehaviorEventType.TASK_STALL:
        return "warning", "行动任务出现停滞"
    return "semester_review", "完成一次复盘"


__all__ = ["DefaultFunctionService"]
