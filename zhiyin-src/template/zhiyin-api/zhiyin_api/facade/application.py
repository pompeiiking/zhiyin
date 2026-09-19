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
from typing import Optional

from fastapi import Request

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
from zhiyin_api.dto.workspace import WorkspacePageView
from zhiyin_api.dto.track import TrackEventAck, TrackEventRequest
from zhiyin_api.facade.facade import ApplicationFacade
from zhiyin_api.dto import mappers
from zhiyin_business.ports.blackboard import (
    AssetService,
    ConversationMemoryService,
)
from zhiyin_business.ports.function import FunctionService
from zhiyin_business.ports.identity import IdentityService
from zhiyin_business.ports.loop import EntrySource, LoopCoordinator, LoopEntry
from zhiyin_business.ports.orchestrator import Orchestrator, TurnRequest
from zhiyin_business.ports.registry import RegistryService
from zhiyin_business.ports.workspace import WorkspaceService
from zhiyin_kernel.enums import AssetType, LoopStage


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
        """
        self._identity = identity
        self._registry = registry
        self._loop = loop
        self._orchestrator = orchestrator
        self._workspace = workspace
        self._assets = assets
        self._functions = functions
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
        return mappers.session_list_view(
            [
                mappers.session_summary_view(
                    panel, lead_agent_name=names.get(panel.lead_agent or "", "")
                )
                for panel in panels
            ]
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
