"""Application Facade 实现 —— 交付（第二波 · 后端-3）。

落位：`api/facade/application.py`。依赖：业务层的服务 Port（只调不实现）+
`api/dto/mappers.py`（前端-1 职责）。

为什么它决定前端能否并行开工
----------------------------
前端只需要这一个实现：它把业务模型翻成 `dto/` 的 View，前端就拿到稳定的 JSON 形状。

三条不越界的要求（本实现逐条遵守）：
- 不写业务规则（规则在 `business/policies/`，调用在 `business/services/`）；
- 不直接访问 Repository / Gateway（只经业务服务）；
- 只做"编排调用 + 交给 Mapper"，字段映射全部在 `api/dto/mappers.py`；
  本文件里不应出现 `XxxView(...)` 的直接构造。

实现口径（对着已冻结 ABC 交付）
------------------------------
1. **同步 / 异步桥**：ABC 冻结了 5 个同步读取方法（bootstrap / list_sessions /
   get_workspace / list_asset_versions / get_report_full_text），而业务服务全部是
   async —— 由 `await_sync()` 桥接：无运行中事件循环时直接 `asyncio.run`；
   有（FastAPI 端点）时在独立线程开一次性事件循环，避免与外层 loop 交叉。
   这是 ABC 同步契约带来的第一期妥协；控制器目前同步调用 Facade，属契约内行为。
2. **可选依赖**：ABC 只把 `identity` / `registry` 定为硬前置（bootstrap 的取数
   出口，见 `facade.py` 模块 docstring 的取数通道表）；对话 / 工作台 / 资产能力
   走 `orchestrator` / `workspace` / `assets` / `functions` —— 以**追加的
   keyword-only 可选参数**注入（不改动既有调用），缺失时对应方法抛
   `FacadeNotConfiguredError`，由 `create_app` 统一映射为
   DEPENDENCY_UNAVAILABLE，不静默吞掉。
3. **取数出口**：身份与动态资源只经 `IdentityService` / `RegistryService`
   （api 被禁止 import data_sdk）。bootstrap 数据聚合收口在
   `gather_bootstrap()`（与 `mock.py` 共用，保证 Mock 与真实取数同源）。
4. **续接口径**：第一期没有会话写侧 Port 暴露给 Facade，`task_id` 采用确定性
   规则 `f"{user_id}:{task_code}"`——同一入口重复进入即"续接"同一会话；
   编排器按 task_id 读黑板，前序资产不丢（验收项 2 的落点）。
5. **左栏会话**：`WorkspaceService.list_sessions_summary` 返回的 `StagePanel`
   不携带 task_id / 主理，按 `task_entries` 的"环节 → 入口"索引反推
   （`stage_entry_index()`，与 enter_task 的 task_id 规则一致），不臆造名字；
   主理展示名取不到时按 Port 口径回落 agent_id。
6. **环节回落**：`free_chat` 等未声明环节的入口经编排器判定；判定不确定
   （need_clarify 或 stage 仍空）时回落 ① 采集——与 `policy_params.routing`
   的 `fallback_stage="collect"` 同口径（Facade 读不到 policy_params，落点
   注释标明，待 RegistryService 出口后切换）。

装配：`zhiyin_boot.wire_application()` 在启动时调用
`configure_facade(DefaultApplicationFacade(...))`；未装配时 `get_facade()` 抛
`FacadeNotConfiguredError`。接线示例（能力位名以 `zhiyin_boot/container/ports.py`
为准）::

    DefaultApplicationFacade(
        identity=container.identity_service,
        registry=container.registry_service,
        orchestrator=container.orchestrator,
        workspace=container.workspace_service,
        assets=container.asset_service,
        functions=container.function_service,
    )

集成提示：
- `mappers.py` 属前端-1 的交付；其未实现时本类方法会在映射处抛
  NotImplementedError（编排逻辑本身已可用）；
- 本类交付后 `tests/test_shell_completeness.py` 的 `IMPLEMENTATION_STATUS`
  断言（当前要求 skeleton）需同步更新为 wired。
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Sequence
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import NamedTuple, Optional, TypeVar

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
from zhiyin_api.dto.workspace import WorkspacePageView
from zhiyin_api.dto.track import TrackEventAck, TrackEventRequest
from zhiyin_api.facade.facade import ApplicationFacade, FacadeNotConfiguredError
from zhiyin_business.ports.blackboard import AssetService
from zhiyin_business.ports.function import FunctionService
from zhiyin_business.ports.identity import IdentityService
from zhiyin_business.ports.orchestrator import Orchestrator, TurnRequest
from zhiyin_business.ports.registry import RegistryService
from zhiyin_business.ports.workspace import WorkspaceService
from zhiyin_kernel.blackboard import TaskSession
from zhiyin_kernel.dynamic_content import (
    BannerSpec,
    FaqSpec,
    MenuSpec,
    RouteSpec,
    TrustBlockSpec,
)
from zhiyin_kernel.enums import AssetType, LoopStage, TaskStatus
from zhiyin_kernel.identity import UserAccount
from zhiyin_kernel.registry import AgentDescriptor, TaskEntrySpec

_T = TypeVar("_T")


def await_sync(awaitable: Awaitable[_T]) -> _T:
    """在同步方法里等待一个 awaitable（ABC 同步契约的桥）。

    无运行中事件循环 → `asyncio.run`；有（FastAPI 端点内）→ 在独立线程的
    一次性事件循环里执行，避免与外层 loop 交叉。
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(awaitable)
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, awaitable).result()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _token_from(request: Request) -> Optional[str]:
    """从请求头取 token：`x-auth-token` 优先，其次 `Authorization: Bearer`。"""
    token = request.headers.get("x-auth-token")
    if token:
        return token
    authorization = request.headers.get("authorization", "")
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip() or None
    return None


# ---------------------------------------------------------------------------
# bootstrap 取数聚合（真实 Facade 与 Mock 共用）
# ---------------------------------------------------------------------------


class BootstrapGather(NamedTuple):
    """`gather_bootstrap()` 的返回包。"""

    menus: list[MenuSpec]
    routes: list[RouteSpec]
    task_entries: list[TaskEntrySpec]
    copy_bundle: dict[str, str]
    banners: list[BannerSpec]
    trust_blocks: list[TrustBlockSpec]
    faqs: list[FaqSpec]
    feature_flags: dict[str, bool]
    agents: dict[str, AgentDescriptor]
    identity: Optional[UserAccount]


async def gather_bootstrap(
    registry: RegistryService, identity: IdentityService
) -> BootstrapGather:
    """聚合 `/app/bootstrap` 的全部数据源（R-API-001 的取数出口表）。

    身份区经 `IdentityService.current_user()` 解析；bootstrap 是同步方法、
    拿不到请求 token，按第一期"默认通过"口径调用（token=None）。
    """
    menus = await registry.list_menus()
    routes = await registry.list_routes()
    task_entries = await registry.list_task_entries()
    copy_bundle = await registry.get_copy_bundle()
    banners = await registry.list_banners()
    trust_blocks = await registry.list_trust_blocks()
    faqs = await registry.list_faqs()
    feature_flags = await registry.feature_flags()

    agents: dict[str, AgentDescriptor] = {}
    for entry in task_entries:
        if entry.lead_agent and entry.lead_agent not in agents:
            agent = await registry.get_agent(entry.lead_agent)
            if agent is not None:
                agents[entry.lead_agent] = agent

    user = await identity.current_user()
    return BootstrapGather(
        menus=menus,
        routes=routes,
        task_entries=task_entries,
        copy_bundle=copy_bundle,
        banners=banners,
        trust_blocks=trust_blocks,
        faqs=faqs,
        feature_flags=feature_flags,
        agents=agents,
        identity=user,
    )


def build_bootstrap_view(data: BootstrapGather) -> BootstrapView:
    """聚合包 → BootstrapView（真实 Facade 与 Mock 共用一份字段口径）。"""
    return mappers.bootstrap_view(
        copy_bundle=data.copy_bundle,
        menus=data.menus,
        routes=data.routes,
        task_entries=data.task_entries,
        agents=data.agents,
        trust_blocks=data.trust_blocks,
        banners=data.banners,
        faqs=data.faqs,
        feature_flags=data.feature_flags,
        identity=data.identity,
    )


def stage_entry_index(
    entries: Sequence[TaskEntrySpec],
) -> dict[str, TaskEntrySpec]:
    """环节值 → 首个声明该环节的任务入口（按 sort_order）。

    真实 Facade（左栏会话反推 task_code）与 Mock（free_chat 回落主理）共用，
    保证"环节 → 入口"的口径只有一份。
    """
    index: dict[str, TaskEntrySpec] = {}
    for entry in sorted(entries, key=lambda item: item.sort_order):
        if entry.target_stage is not None:
            index.setdefault(entry.target_stage.value, entry)
    return index


# ---------------------------------------------------------------------------
# 默认实现
# ---------------------------------------------------------------------------


class DefaultApplicationFacade(ApplicationFacade):
    """BFF 门面默认实现。"""

    IMPLEMENTATION_STATUS = "wired"

    def __init__(
        self,
        *,
        identity: IdentityService,
        registry: RegistryService,
        orchestrator: Optional[Orchestrator] = None,
        workspace: Optional[WorkspaceService] = None,
        assets: Optional[AssetService] = None,
        functions: Optional[FunctionService] = None,
    ) -> None:
        """构造依赖由 boot 注入。

        `identity` / `registry` 是 bootstrap 的硬前置（api 拿不到 `AuthGateway`
        与 `RegistryRepository`，见两个 Port 的模块 docstring）；
        `orchestrator` / `workspace` / `assets` / `functions` 支撑对话 / 工作台 /
        资产能力，未注入时对应方法抛 `FacadeNotConfiguredError`。

        `resolve_user_id` 的职责边界：**只做 HTTP → 业务形状的翻译**
        （从请求里取 token），用户记录的补齐、游客会话、登录合并都在业务侧。
        """
        self._identity = identity
        self._registry = registry
        self._orchestrator = orchestrator
        self._workspace = workspace
        self._assets = assets
        self._functions = functions

    # ---------- 内部 ----------

    def _require(self, attribute: str) -> None:
        if getattr(self, f"_{attribute}") is None:
            raise FacadeNotConfiguredError(
                f"{type(self).__name__} 未装配 {attribute} 依赖，该能力不可用"
            )

    # ---------- 身份 ----------

    async def resolve_user_id(self, request: Request) -> str:
        token = _token_from(request)
        user = await self._identity.current_user(token=token)
        return user.id

    # ---------- 启动 ----------

    def bootstrap(self, user_id: str) -> BootstrapView:
        # 取数全部来自动态资源，与 user_id 无关；身份区由 current_user 解析
        # （签名里的 user_id 是 ABC 冻结参数）。
        data = await_sync(gather_bootstrap(self._registry, self._identity))
        return build_bootstrap_view(data)

    # ---------- 对话 ----------

    def list_sessions(self, user_id: str) -> SessionListView:
        self._require("workspace")
        panels = await_sync(self._workspace.list_sessions_summary(user_id))
        entries = await_sync(self._registry.list_task_entries())
        index = stage_entry_index(entries)

        # 主理展示名集中解析一次（Port 口径：取不到回落 agent_id）。
        leads = {
            entry.lead_agent
            for entry in index.values()
            if entry.lead_agent is not None
        }
        agent_names: dict[str, str] = {}
        for agent_id in leads:
            agent = await_sync(self._registry.get_agent(agent_id))
            if agent is not None:
                agent_names[agent_id] = agent.name

        views: list[TaskSessionView] = []
        for panel in panels:
            entry = index.get(panel.stage.value)
            task_code = entry.code if entry is not None else panel.stage.value
            lead = entry.lead_agent if entry is not None else None
            session = TaskSession(
                id=f"{user_id}:{task_code}",
                user_id=user_id,
                task_code=task_code,
                task_name=panel.title,
                loop_stage=panel.stage,
                lead_agent=lead or "",
                status=TaskStatus.ACTIVE,
                # StagePanel 不携带创建时间；仅用于展示，取面板更新时间兜底。
                created_at=panel.updated_at or _utcnow(),
                updated_at=panel.updated_at or _utcnow(),
            )
            views.append(
                mappers.task_session_view(
                    session,
                    task_name=panel.title,
                    lead_agent_name=agent_names.get(lead or "", lead or ""),
                )
            )
        return mappers.session_list_view(views)

    async def enter_task(self, user_id: str, body: TaskEnterRequest) -> TaskSessionView:
        entries = await self._registry.list_task_entries()
        entry = next((item for item in entries if item.code == body.task_code), None)
        if entry is None:
            raise ValueError(f"未知任务入口：{body.task_code!r}")

        task_id = f"{user_id}:{entry.code}"
        stage, lead = entry.target_stage, entry.lead_agent
        if stage is None or lead is None:
            # 未声明环节的入口（如 free_chat）走编排器判定；
            # 判定不确定时按 routing 口径回落 ① 采集，不硬跳。
            self._require("orchestrator")
            intent = await self._orchestrator.detect_intent(user_id, entry.code)
            decision = await self._orchestrator.detect_stage(user_id, task_id, intent)
            if decision.stage is not None and not decision.need_clarify:
                stage = decision.stage
            else:
                # TODO(动态资源)：RegistryService 尚未出口 policy_params，
                # 回落值暂与 policy_params.routing.fallback_stage="collect" 同口径。
                stage = LoopStage.COLLECT
            axis_a = await self._orchestrator.infer_axis_a(user_id, task_id)
            lead_decision = await self._orchestrator.select_lead(
                user_id, task_id, axis_a, stage, intent
            )
            lead = lead_decision.lead_agent

        session = TaskSession(
            id=task_id,
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
        self._require("orchestrator")
        turn = await self._orchestrator.handle_message(
            TurnRequest(
                user_id=user_id,
                task_id=body.task_id,
                message=body.message,
                client_msg_id=body.client_msg_id,
            )
        )
        view = mappers.conversation_turn_view(turn)
        # 管线卡入参在 turn 之外（Mapper 冻结签名按输入拆分），由门面拼装。
        view.pipeline_cards = mappers.pipeline_cards(turn.session, turn.asset_versions)
        return view

    # ---------- 工作台 ----------

    def get_workspace(self, user_id: str) -> WorkspacePageView:
        self._require("workspace")
        view = await_sync(self._workspace.build_view(user_id))
        return mappers.workspace_page_view(view)

    # ---------- 资产 ----------

    def list_asset_versions(
        self, user_id: str, asset_type: AssetType
    ) -> list[AssetVersionView]:
        self._require("assets")
        versions = await_sync(self._assets.list_versions(user_id, asset_type))
        ordered = sorted(versions, key=lambda item: item.version)
        views: list[AssetVersionView] = []
        for previous, current in zip(ordered, ordered[1:]):
            views.append(mappers.asset_version_view(current, previous=previous))
        if ordered:
            # 首版无 previous，diff 为空。
            views.insert(0, mappers.asset_version_view(ordered[0]))
        return views

    def get_report_full_text(
        self, user_id: str, version: Optional[int] = None
    ) -> ReportFullTextView:
        self._require("assets")
        report = await_sync(self._assets.get_report(user_id, version))
        if report is None:
            raise ValueError(
                f"报告不存在（user_id={user_id!r}, version={version!r}）"
            )
        return mappers.report_full_text_view(report)

    async def export_asset(self, user_id: str, body: ExportRequest) -> ExportResultView:
        self._require("functions")
        result = await self._functions.export_asset(
            user_id, body.asset_type.value, body.format
        )
        return mappers.export_result_view(result)

    # ---------- 埋点 ----------

    async def track_event(
        self, user_id: str, body: TrackEventRequest
    ) -> TrackEventAck:
        # 决策 14：只有 channel=frontend 的纯体验型事件允许入站上报；
        # 后端派生事件从这条通道进来会被拒绝，避免一条事件记两次。
        events = await self._registry.list_track_events()
        accepted = any(
            item.code == body.event and item.channel == "frontend"
            for item in events
        )
        return TrackEventAck(accepted=accepted, event=body.event)


__all__ = [
    "BootstrapGather",
    "DefaultApplicationFacade",
    "await_sync",
    "build_bootstrap_view",
    "gather_bootstrap",
    "stage_entry_index",
]
