"""Application Facade 实现。

落位：`api/facade/application.py` —— 接口/前端联调负责人。
依赖：业务层的服务 Port（只调不实现）+ `api/dto/mappers.py`。

为什么它决定前端能否并行开工
----------------------------
前端只需要这一个实现：它把业务模型翻成 `dto/` 的 View，前端就拿到稳定的 JSON 形状。
第一期实现已经装配，`/app/*` 通过稳定 DTO 返回业务数据；若未来装配缺失，接口仍按
约定返回 503（code 1007）。

三条不越界的要求：
- 不写业务规则（规则在 `business/policies/`，调用在 `business/services/`）；
- 不直接访问 Repository / Gateway（只经业务服务）；
- 只做"编排调用 + 交给 Mapper"，字段映射全部在 `api/dto/mappers.py`；
  本文件里不应出现 `XxxView(...)` 的直接构造。

两个硬前置（构造时必须注入，否则 `/app/bootstrap` 无数据可返回）
---------------------------------------------------------------
- `IdentityService`：解析当前用户（api 拿不到 `AuthGateway`）；
- `RegistryService`：菜单 / 路由 / 任务入口 / 文案 / 开关（api 拿不到 `RegistryRepository`）。

两者都是"api 需要、契约却在 data_sdk"逼出来的业务侧出口，
判据与决策见 `business/ports/identity.py` 与 `business/ports/registry.py` 的模块 docstring。

装配：`zhiyin_boot.wire_application()` 在启动时调用
`configure_facade(DefaultApplicationFacade(...))`；未装配时 `get_facade()` 抛
`FacadeNotConfiguredError`，由 `create_app` 统一映射为 DEPENDENCY_UNAVAILABLE。
"""

from __future__ import annotations

import asyncio
import hashlib
from datetime import datetime
from typing import Optional

from fastapi import Request

from zhiyin_api.dto.asset import (
    AssetVersionView,
    CalendarNodeRequest,
    CalendarNodeView,
    DecisionSelectionRequest,
    DecisionSelectionView,
    ExportRequest,
    ExportResultView,
    GapClaimRequest,
    GapClaimView,
    ReportFullTextView,
    TaskDoneRequest,
    TaskDoneView,
)
from zhiyin_api.dto.bootstrap import BootstrapView
from zhiyin_api.dto.conversation import (
    ConversationHistoryView,
    ConversationTurnView,
    MessageRequest,
    SessionListView,
    TaskEnterRequest,
    TaskSessionView,
)
from zhiyin_api.dto.workspace import WorkspacePageView
from zhiyin_api.dto.track import TrackEventAck, TrackEventRequest
from zhiyin_api.facade.facade import ApplicationFacade
from zhiyin_api.dto import mappers
from zhiyin_business.contracts.common import BehaviorEventDraft
from zhiyin_business.ports.blackboard import (
    AssetService,
    BehaviorService,
    ConversationMemoryService,
)
from zhiyin_business.ports.function import FunctionService
from zhiyin_business.ports.identity import IdentityService
from zhiyin_business.ports.loop import EntrySource, LoopCoordinator, LoopEntry
from zhiyin_business.ports.orchestrator import Orchestrator, TurnRequest
from zhiyin_business.ports.registry import RegistryService
from zhiyin_business.ports.workspace import WorkspaceService
from zhiyin_kernel.assets import CalendarNode
from zhiyin_kernel.enums import AssetType, BehaviorEventType, LoopStage


def calendar_node_id(
    title: str, due_at: Optional[datetime], related_task_text: str
) -> str:
    """由提醒内容派生稳定的日历节点 id（FR-ACT-004 幂等）。

    日历是"规划师写入、教练读取"的共享状态。同一批提醒有两条写入路径：
    ④ 环节编排器按此规则派生 id 写入，报告页「加入日历」也走这个端点。
    两条路径只要标题 / 截止时间 / 关联任务一致，就必须落到**同一条**节点上，
    否则同一个提醒会在日历里叠成两条。

    口径必须与 `zhiyin_business/services/orchestrator.py::_calendar_node_id`
    逐字一致（分隔符、字段顺序、`isoformat()`、sha1 取前 12 位）；两处任一处改了
    规则，报告页写入就会与编排器写入错开，日历重新出现重复节点。
    """
    key = "|".join(
        [
            title,
            due_at.isoformat() if due_at is not None else "",
            related_task_text,
        ]
    )
    return f"cal_{hashlib.sha1(key.encode('utf-8')).hexdigest()[:12]}"


class DefaultApplicationFacade(ApplicationFacade):
    """BFF 门面默认实现。"""

    IMPLEMENTATION_STATUS = "wired"

    def __init__(
        self,
        *,
        identity: IdentityService,
        registry: RegistryService,
        loop: LoopCoordinator,
        orchestrator: Orchestrator,
        workspace: WorkspaceService,
        assets: AssetService,
        functions: FunctionService,
        behaviors: BehaviorService,
        memories: ConversationMemoryService,
    ) -> None:
        """构造依赖由 boot 注入。

        身份解析走业务 Port：api 被禁止 import `zhiyin_data_sdk`，拿不到
        `AuthGateway`；由 `DefaultIdentityService` 把它包成业务抽象
        （决策见 `business/ports/identity.py` 的模块 docstring）。

        动态资源同理：菜单 / 路由 / 任务入口 / 文案 / 开关经
        `DefaultRegistryService` 取（`business/ports/registry.py`）。

        `resolve_user_id` 的职责边界：**只做 HTTP → 业务形状的翻译**
        （从请求里取 token），用户记录的补齐、游客会话、登录合并都在业务侧。

        `BehaviorService` 用于把用户的写操作记成行为日志：成就与跟踪时间线都是
        行为日志的只读投影，缺了它，"认领差距 / 选方案 / 勾任务"就只是改了几个
        字段，界面上的成就与时间线永远不动（B-2 断链）。
        """
        self._identity = identity
        self._registry = registry
        self._loop = loop
        self._orchestrator = orchestrator
        self._workspace = workspace
        self._assets = assets
        self._functions = functions
        self._behaviors = behaviors
        self._memories = memories

    # ---------- 身份 ----------

    async def resolve_user_id(self, request: Request) -> str:
        authorization = request.headers.get("authorization", "")
        token = authorization[7:].strip() if authorization.lower().startswith("bearer ") else None
        return (await self._identity.current_user(token=token)).id

    # ---------- 启动 ----------

    async def bootstrap(self, user_id: str) -> BootstrapView:
        (
            identity,
            copies,
            menus,
            routes,
            entries,
            trust,
            banners,
            faqs,
            flags,
            capabilities,
        ) = await asyncio.gather(
            self._identity.current_user(),
            self._registry.get_copy_bundle(),
            self._registry.list_menus(),
            self._registry.list_routes(),
            self._registry.list_task_entries(),
            self._registry.list_trust_blocks(),
            self._registry.list_banners(),
            self._registry.list_faqs(),
            self._registry.feature_flags(),
            # 能力池（D9）：业务层已把"负责环节（由产出契约反推）"与"理论中文名"解析好
            self._registry.list_agent_capabilities(),
        )
        agent_ids = {entry.lead_agent for entry in entries if entry.lead_agent}
        descriptors = await asyncio.gather(
            *(self._registry.get_agent(agent_id) for agent_id in agent_ids)
        )
        agents = {
            item.id: item for item in descriptors if item is not None
        }
        return mappers.bootstrap_view(
            copy_bundle=copies,
            menus=menus,
            routes=routes,
            task_entries=entries,
            agents=agents,
            capabilities=capabilities,
            trust_blocks=trust,
            banners=banners,
            faqs=faqs,
            feature_flags=flags,
            identity=identity if identity.id == user_id else None,
        )

    # ---------- 对话 ----------

    async def list_sessions(self, user_id: str) -> SessionListView:
        panels = await self._workspace.list_sessions_summary(user_id)
        agent_ids = {panel.lead_agent for panel in panels if panel.lead_agent}
        descriptors = await asyncio.gather(
            *(self._registry.get_agent(agent_id) for agent_id in agent_ids)
        )
        names = {item.id: item.name for item in descriptors if item is not None}
        # 当前会话：取最近活跃（`updated_at` 最新）的那条任务会话。
        # 会话切换此前只在浏览器内存里保留，刷新后前端只能落到 `sessions[0]`，
        # 于是中栏标题会从用户选中的任务回落到列表首项。这里把"最近活跃"作为
        # 后端的当前会话事实返回，前端 `currentTaskId` 直接按它恢复。
        current = max(
            (panel for panel in panels if panel.task_id),
            # 用"是否有时间戳"当首关键字：`updated_at` 可缺省，直接比较
            # `None` 与 `datetime` 会抛 TypeError。缺时间戳的会话排在后面。
            key=lambda panel: (panel.updated_at is not None, panel.updated_at),
            default=None,
        )
        return mappers.session_list_view(
            [
                mappers.session_summary_view(
                    panel, lead_agent_name=names.get(panel.lead_agent or "", "")
                )
                for panel in panels
            ],
            current_task_id=current.task_id if current is not None else None,
        )

    async def enter_task(self, user_id: str, body: TaskEnterRequest) -> TaskSessionView:
        entries = await self._registry.list_task_entries()
        entry = next((item for item in entries if item.code == body.task_code), None)
        if entry is None:
            raise LookupError(f"任务入口不存在：{body.task_code}")
        stage = entry.target_stage or LoopStage.COLLECT
        lead_agent = entry.lead_agent
        if lead_agent is None:
            decision = await self._orchestrator.select_lead(
                user_id,
                body.task_code,
                await self._orchestrator.infer_axis_a(user_id, body.task_code),
                stage,
                await self._orchestrator.detect_intent(user_id, entry.label),
            )
            lead_agent = decision.lead_agent
        context = await self._loop.start(
            LoopEntry(
                user_id=user_id,
                task_code=entry.code,
                # 会话显示名 = 入口文案：让 `task/enter` 的返回值与左栏会话列表
                # （含刷新后的列表）说的是同一件事。
                task_name=entry.label,
                stage=stage,
                lead_agent=lead_agent,
                source=EntrySource.FREE_CHAT if entry.target_stage is None else EntrySource.HOME_TASK,
            )
        )
        await self._memories.upsert(
            user_id,
            context.session.id,
            loop_stage=context.stage,
            lead_agent=context.lead_agent,
        )
        descriptor = await self._registry.get_agent(context.lead_agent)
        return mappers.task_session_view(
            context.session,
            task_name=entry.label,
            lead_agent_name=descriptor.name if descriptor else context.lead_agent,
            progress=(list(LoopStage).index(context.stage) + 1) / len(LoopStage),
        )

    async def send_message(
        self, user_id: str, body: MessageRequest
    ) -> ConversationTurnView:
        turn = await self._orchestrator.handle_message(
            TurnRequest(
                user_id=user_id,
                task_id=body.task_id,
                message=body.message,
                client_msg_id=body.client_msg_id,
            )
        )
        return mappers.conversation_turn_view(turn)

    async def read_conversation_history(
        self, user_id: str, task_id: str
    ) -> ConversationHistoryView:
        history = await self._orchestrator.read_history(user_id, task_id)
        # 管线卡要的是"各环节当前产出"，按资产类型各取最新一版：
        # 三类资产独立取，缺哪类就少哪张卡的产出，不因缺一项而整体失败。
        version_lists = await asyncio.gather(
            *(self._assets.list_versions(user_id, asset_type) for asset_type in AssetType)
        )
        latest = [items[-1] for items in version_lists if items]
        # 历史里可能跨过多次交接，气泡要各自显示当时的主理名；
        # 名字只从注册表取，取不到就留空由前端回落 agent_id，不在这里编造。
        agent_ids = {item.agent_id for item in history.messages if item.agent_id}
        if history.session is not None and history.session.lead_agent:
            agent_ids.add(history.session.lead_agent)
        descriptors = await asyncio.gather(
            *(self._registry.get_agent(agent_id) for agent_id in agent_ids)
        )
        agents = {item.id: item for item in descriptors if item is not None}
        return mappers.conversation_history_view(
            history, asset_versions=latest, agents=agents
        )

    # ---------- 工作台 ----------

    async def get_workspace(self, user_id: str) -> WorkspacePageView:
        return mappers.workspace_page_view(await self._workspace.build_view(user_id))

    # ---------- 资产 ----------

    async def list_asset_versions(
        self, user_id: str, asset_type: AssetType
    ) -> list[AssetVersionView]:
        versions = await self._assets.list_versions(user_id, asset_type)
        return [
            mappers.asset_version_view(
                version, previous=versions[index - 1] if index else None
            )
            for index, version in enumerate(versions)
        ]

    async def get_report_full_text(
        self, user_id: str, version: Optional[int] = None
    ) -> ReportFullTextView:
        report = await self._assets.get_report(user_id, version)
        if report is None:
            raise LookupError("尚未生成诊断报告")
        # ③方向方案与④行动计划是同一批"活资产"，报告页要一并展示；
        # 它们各自独立降级：取不到就少一个章节，不因为计划缺失而让整个报告 500。
        plans = await self._assets.list_direction_plans(user_id)
        action_plan = await self._assets.get_action_plan(user_id)
        return mappers.report_full_text_view(
            report, direction_plans=plans, action_plan=action_plan
        )

    async def export_asset(self, user_id: str, body: ExportRequest) -> ExportResultView:
        result = await self._functions.export_asset(
            user_id, body.asset_type.value, body.format
        )
        return mappers.export_result_view(result)

    # ---------- 闭环写操作 ----------

    async def claim_gap(self, user_id: str, body: GapClaimRequest) -> GapClaimView:
        # 先读一次最新报告，才能区分"这次真的认领了"和"重复点同一条"：
        # 重复点击不该在行为时间线上留下第二条记录（成就按首次解锁，不会被污染，
        # 但跟踪时间线会出现一模一样的重复条目）。
        before = await self._assets.get_report(user_id)
        already = before is not None and any(
            claim.gap_id == body.gap_id for claim in before.gap_claims
        )
        report = await self._assets.claim_gap(user_id, body.gap_id)
        if not already:
            await self._log_behavior(
                user_id,
                BehaviorEventType.GAP_CLAIM,
                {
                    "gap_id": body.gap_id,
                    "detail": f"认领差距：{body.gap_id}",
                },
                related_asset_ids=[report.id],
            )
        return mappers.gap_claim_view(report, body.gap_id)

    async def select_direction_plan(
        self, user_id: str, body: DecisionSelectionRequest
    ) -> DecisionSelectionView:
        # 选 vs 重选要分开记：成就里有 `direction_selected` 与 `direction_reselected`
        # 两个独立徽章。同一套方案再点一次不算重选，不写日志。
        plans = await self._assets.list_direction_plans(user_id)
        current = next((plan.id for plan in plans if plan.selected), None)
        plan = await self._assets.select_direction_plan(user_id, body.plan_id)
        if current != body.plan_id:
            await self._log_behavior(
                user_id,
                BehaviorEventType.DECISION_RESELECT
                if current is not None
                else BehaviorEventType.DECISION_SELECT,
                {
                    "plan_id": plan.id,
                    "previous_plan_id": current or "",
                    "detail": f"选定方向：{plan.name}",
                },
            )
        return mappers.decision_selection_view(plan)

    async def mark_task_done(self, user_id: str, body: TaskDoneRequest) -> TaskDoneView:
        # 任务标识的口径（`阶段名:任务文本`）只存在于仓储层，这里不做重复匹配，
        # 改用"已完成数是否增加"判断这次是否真的发生了状态跃迁。
        before = await self._assets.get_action_plan(user_id)
        before_done = (
            sum(1 for phase in before.phases for task in phase.tasks if task.done)
            if before is not None
            else 0
        )
        plan = await self._assets.mark_task_done(user_id, body.task_id)
        view = mappers.task_done_view(plan, body.task_id)
        if view.done_total > before_done:
            await self._log_behavior(
                user_id,
                BehaviorEventType.TASK_DONE,
                {
                    "task_id": body.task_id,
                    "detail": f"完成任务：{view.text}",
                },
                related_asset_ids=[plan.id],
            )
        return view

    async def write_calendar_node(
        self, user_id: str, body: CalendarNodeRequest
    ) -> CalendarNodeView:
        node = CalendarNode(
            # 与 ④ 环节编排器同一套幂等口径：同一提醒重复写入只更新同一条节点，
            # 不再每次 `uuid4` 生成新 id 让日历叠出重复项。
            node_id=calendar_node_id(body.title, body.due_at, body.related_task_text),
            user_id=user_id,
            title=body.title,
            due_at=body.due_at,
            source=body.source,
            related_task_text=body.related_task_text,
        )
        saved = await self._functions.write_calendar_node(user_id, node)
        return mappers.calendar_node_view(saved)

    async def _log_behavior(
        self,
        user_id: str,
        event_type: BehaviorEventType,
        payload: dict,
        *,
        related_asset_ids: Optional[list[str]] = None,
    ) -> None:
        """把一次真实用户动作追加进行为日志。

        只做写入，不改动任何业务状态：成就（`first_gap_claimed` 等）与工作台跟踪
        时间线都在读取时从这份日志投影出来。
        """
        await self._behaviors.log(
            user_id,
            BehaviorEventDraft(
                event_type=event_type,
                payload=payload,
                related_asset_ids=related_asset_ids or [],
            ),
        )

    # ---------- 埋点 ----------

    async def track_event(
        self, user_id: str, body: TrackEventRequest
    ) -> TrackEventAck:
        specs = await self._registry.list_track_events()
        spec = next((item for item in specs if item.code == body.event), None)
        if spec is None or spec.channel != "frontend":
            raise ValueError(f"不接受该前端事件：{body.event}")
        return TrackEventAck(accepted=True, event=body.event)


__all__ = ["DefaultApplicationFacade"]
