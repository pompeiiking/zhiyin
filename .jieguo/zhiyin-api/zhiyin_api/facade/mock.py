"""Mock Facade 实现 —— 交付（第二波 · 后端-3）。

落位：`api/facade/mock.py`。用途：决策 15 = A——Facade 未接线或演示场景下，
前端用 `ZHIYIN_MOCK=1` 走真实路由联调，数据全部来自动态资源（任务入口 / 菜单 /
文案 / 开关等），并可作为 FR-BLOCK-005 自动演示的数据源。

三条与真实 Facade 相同的边界（本实现逐条遵守）：
- 不写业务规则，不做字段映射（字段口径只在 `dto/mappers.py`）；
- 不直接访问 Repository / Gateway，只面对业务 Port；
- Mock 产出必须显式标注来源——对话正文固定携带 `mock.source_notice`，
  报告结论携带 `demo.data_notice` + `mock.source_notice`
  （硬约束：不得让 Mock 结论被误读为真实能力）。

实现口径
--------
- 取数与 bootstrap 组装**复用真实实现的公共助手**
  （`application.gather_bootstrap` / `build_bootstrap_view` / `await_sync` /
  `stage_entry_index`），保证 Mock 与真实只有"数据从哪来"的差别，
  没有"字段口径"的差别；
- 会话 / 一轮回复都是合成的业务形状（`TaskSession` / `TurnResult`），喂给
  同一套 Mapper；`WorkspaceView` 同理——那是 Mapper 的输入（业务模型），
  不是 dto View，不违反"View 构造不进门面"的守卫口径；
- 演示口径：`free_chat` 等未声明环节的入口回落 ① 采集，主理取该环节在
  任务入口里声明的默认主理（`stage_entry_index`，来自动态资源，不硬编码）；
- 资产版本恒为空、导出恒占位（`available=False`）、埋点只校验归属不落库。
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import Request

from zhiyin_api.dto import mappers
from zhiyin_api.dto.asset import (
    AssetVersionView,
    ExportRequest,
    ExportResultView,
    ReportFullTextView,
)
from zhiyin_api.dto.bootstrap import BootstrapView
from zhiyin_api.dto.conversation import (
    ConversationTurnView,
    MessageRequest,
    SessionListView,
    TaskEnterRequest,
    TaskSessionView,
)
from zhiyin_api.dto.track import TrackEventAck, TrackEventRequest
from zhiyin_api.dto.workspace import WorkspacePageView
from zhiyin_api.facade.application import (
    await_sync,
    build_bootstrap_view,
    gather_bootstrap,
    stage_entry_index,
)
from zhiyin_api.facade.facade import ApplicationFacade
from zhiyin_business.contracts.common import (
    AgentBadge,
    BehaviorGuide,
    ConversationMessage,
)
from zhiyin_business.ports.function import ExportResult
from zhiyin_business.ports.identity import IdentityService
from zhiyin_business.ports.orchestrator import TurnResult
from zhiyin_business.ports.registry import RegistryService
from zhiyin_business.ports.workspace import WorkspaceView
from zhiyin_kernel.assets import Report, Swot, Verdict
from zhiyin_kernel.blackboard import TaskSession
from zhiyin_kernel.enums import AssetType, LoopStage

_FALLBACK_STAGE = LoopStage.COLLECT


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MockApplicationFacade(ApplicationFacade):
    """BFF 门面的 Mock 替身：只读动态资源，不写真实黑板。"""

    IMPLEMENTATION_STATUS = "wired"

    def __init__(self, *, identity: IdentityService, registry: RegistryService) -> None:
        self._identity = identity
        self._registry = registry

    # ---------- 身份 ----------

    async def resolve_user_id(self, request: Request) -> str:
        # Mock 忽略 token：第一期"默认通过"口径（DefaultPassAuth 恒返回演示用户）。
        user = await self._identity.current_user()
        return user.id

    # ---------- 启动 ----------

    def bootstrap(self, user_id: str) -> BootstrapView:
        # 与真实 Facade 同一条取数与组装路径，Mock 差异只体现在对话 / 资产。
        data = await_sync(gather_bootstrap(self._registry, self._identity))
        return build_bootstrap_view(data)

    # ---------- 对话 ----------

    def list_sessions(self, user_id: str) -> SessionListView:
        entries = await_sync(self._registry.list_task_entries())
        routable = [
            item
            for item in entries
            if item.target_stage is not None and item.lead_agent is not None
        ]
        views: list[TaskSessionView] = []
        if routable:
            entry = routable[0]
            assert entry.target_stage is not None and entry.lead_agent is not None
            session = TaskSession(
                id=f"{user_id}:{entry.code}",
                user_id=user_id,
                task_code=entry.code,
                task_name=entry.label,
                loop_stage=entry.target_stage,
                lead_agent=entry.lead_agent,
                created_at=_utcnow(),
                updated_at=_utcnow(),
            )
            lead_agent_name = entry.lead_agent
            agent = await_sync(self._registry.get_agent(entry.lead_agent))
            if agent is not None:
                lead_agent_name = agent.name
            views.append(
                mappers.task_session_view(
                    session, task_name=entry.label, lead_agent_name=lead_agent_name
                )
            )
        return mappers.session_list_view(views)

    async def enter_task(self, user_id: str, body: TaskEnterRequest) -> TaskSessionView:
        entries = await self._registry.list_task_entries()
        entry = next((item for item in entries if item.code == body.task_code), None)
        if entry is None:
            raise ValueError(f"未知任务入口：{body.task_code!r}")

        stage, lead = entry.target_stage, entry.lead_agent
        if stage is None:
            # 演示口径：未声明环节的入口回落 ① 采集，主理取该环节的默认主理。
            stage = _FALLBACK_STAGE
            fallback = stage_entry_index(entries).get(stage.value)
            lead = fallback.lead_agent if fallback is not None else None

        session = TaskSession(
            id=f"{user_id}:{entry.code}",
            user_id=user_id,
            task_code=entry.code,
            task_name=entry.label,
            loop_stage=stage,
            lead_agent=lead or "",
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        lead_agent_name = lead or ""
        if lead:
            agent = await self._registry.get_agent(lead)
            if agent is not None:
                lead_agent_name = agent.name
        return mappers.task_session_view(
            session, task_name=entry.label, lead_agent_name=lead_agent_name
        )

    async def send_message(
        self, user_id: str, body: MessageRequest
    ) -> ConversationTurnView:
        entries = await self._registry.list_task_entries()
        task_code = body.task_id.rsplit(":", 1)[-1]
        entry = next((item for item in entries if item.code == task_code), None)
        if entry is None:
            raise ValueError(f"Mock 未识别的任务会话：{body.task_id!r}")

        stage = entry.target_stage or _FALLBACK_STAGE
        lead = entry.lead_agent
        if lead is None:
            fallback = stage_entry_index(entries).get(stage.value)
            lead = fallback.lead_agent if fallback is not None else ""

        badge = AgentBadge(agent_id=lead, name=lead, role_summary="")
        if lead:
            agent = await self._registry.get_agent(lead)
            if agent is not None:
                badge = AgentBadge(
                    agent_id=lead, name=agent.name, role_summary=agent.role_summary
                )

        copies = await self._registry.get_copy_bundle()
        session = TaskSession(
            id=body.task_id,
            user_id=user_id,
            task_code=entry.code,
            task_name=entry.label,
            loop_stage=stage,
            lead_agent=lead,
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        # TODO(动态资源)：追问话术键待补 copies.json，暂用任务组标题占位。
        question = copies.get("home.task_group_title", "")
        turn = TurnResult(
            task_id=body.task_id,
            session=session,
            stage=stage,
            badge=badge,
            messages=[
                ConversationMessage(
                    role="agent",
                    # 硬约束：Mock 产出必须显式标注来源。
                    text=copies.get("mock.source_notice", ""),
                    agent_id=lead or None,
                    created_at=_utcnow(),
                )
            ],
            disclosure=None,
            guide=BehaviorGuide(kind="question", text=question, question=question),
            asset_versions=[],
        )
        view = mappers.conversation_turn_view(turn)
        view.pipeline_cards = mappers.pipeline_cards(session, turn.asset_versions)
        return view

    # ---------- 工作台 ----------

    def get_workspace(self, user_id: str) -> WorkspacePageView:
        # 合成空工作台（业务形状，Mapper 的输入，不是 dto View）。
        return mappers.workspace_page_view(WorkspaceView(user_id=user_id))

    # ---------- 资产 ----------

    def list_asset_versions(
        self, user_id: str, asset_type: AssetType
    ) -> list[AssetVersionView]:
        # 演示态不产资产版本；需要时经 AssetService 合成后再走 Mapper。
        return []

    def get_report_full_text(
        self, user_id: str, version: Optional[int] = None
    ) -> ReportFullTextView:
        copies = await_sync(self._registry.get_copy_bundle())
        report = Report(
            id=f"demo-report:{user_id}",
            user_id=user_id,
            version=version or 1,
            generated_at=_utcnow(),
            # 硬约束：演示数据必须显式标注（demo.data_notice），
            # 且不得让 Mock 结论被误读为真实能力（mock.source_notice）。
            verdict=Verdict(
                title=copies.get("demo.data_notice", ""),
                summary=copies.get("mock.source_notice", ""),
            ),
            swot=Swot(),  # FR-DIAG-002 的"每项不少于 2 条"是对真实报告的要求，演示报告留空。
        )
        return mappers.report_full_text_view(report)

    async def export_asset(self, user_id: str, body: ExportRequest) -> ExportResultView:
        result = ExportResult(asset_type=body.asset_type.value, format=body.format)
        return mappers.export_result_view(result)

    # ---------- 埋点 ----------

    async def track_event(
        self, user_id: str, body: TrackEventRequest
    ) -> TrackEventAck:
        # 与真实实现同一归属校验：只有 channel=frontend 允许入站；
        # 演示数据不落库，仅确认接收。
        events = await self._registry.list_track_events()
        accepted = any(
            item.code == body.event and item.channel == "frontend"
            for item in events
        )
        return TrackEventAck(accepted=accepted, event=body.event)


__all__ = ["MockApplicationFacade"]
