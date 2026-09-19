"""DTO Mapper：业务形状 → 前端视图。

落位：`api/dto/mappers.py` —— 接口/前端联调负责人。

为什么单独一层
--------------
《分层详细设计》§2.2 规定 BFF 的转换动作由 "DTO Mapper" 承担，而
`api/facade/application.py` 只负责"编排调用 + 交给 Mapper"。这样切开的收益是：

- **前端字段口径只有一个地方**：改字段改 Mapper，不散落在 Facade 的每个方法体里；
- **Facade 与 DTO 可以并行**：前端先拿 `dto/` 的 View 形状开工，
  Mapper 实现完再接通数据；
- **契约可测**：Mapper 是纯函数（无 IO、无状态），可以脱离服务直接单测。

规则
----
- 只做形状翻译：`business 读模型 / Port 返回值 → dto View`；
- **不做取数**（不调服务）、**不写业务规则**（不判断该不该展示、不拼结论）；
- 不解析文案：文案一律来自 `copy_bundle`（动态资源），不要在这里拼中文。

字段来源（照此实现，不要另找数据源）
------------------------------------
- `BootstrapView` ← `RegistryService`（菜单 / 路由 / 任务入口 / 文案 / 横幅 / 信任块 /
  FAQ / 功能开关）+ `IdentityService`（身份区）
- `SessionListView` / `TaskSessionView` ← `WorkspaceService.list_sessions_summary`
  与 `TaskSession`（左栏按"任务/环节"命名，不按 agent 名排布）
- `ConversationTurnView` ← `Orchestrator.handle_message` 的 `TurnResult`
  （最短结论 + 显式告知 + 行为引导 + 管线卡）
- `WorkspacePageView` ← `WorkspaceService.build_view` 的 `WorkspaceView`
- `AssetVersionView` / `ReportFullTextView` / `ExportResultView` ←
  `AssetService` / `FunctionService` 的返回值

注意 `TurnResult.disclosure` 是**可空**的：只有"换主理 / 换理论 / 结论变化"时才填。
Mapper 必须把 None 原样透传成 `None`（前端据此决定是否渲染告知行），
**不要**用空字符串或默认文案顶替——那会让"没有告知"和"告知了但是空的"无法区分。
"""

from __future__ import annotations

from typing import Optional, Sequence

from zhiyin_api.dto.asset import (
    AssetVersionView,
    CalendarNodeView,
    DecisionSelectionView,
    ExportResultView,
    GapClaimView,
    ReportFullTextView,
    TaskDoneView,
)
from zhiyin_api.dto.bootstrap import (
    AgentTheoryView,
    AgentView,
    BannerView,
    BootstrapView,
    FaqView,
    MenuView,
    RouteView,
    TaskEntryView,
    TrustBlockView,
)
from zhiyin_api.dto.conversation import (
    ConversationHistoryView,
    ConversationMessageView,
    ConversationTurnView,
    PipelineCardView,
    SessionListView,
    TaskSessionView,
)
from zhiyin_api.dto.workspace import (
    DependencyEdgeView,
    ProfilePanelView,
    StagePanelView,
    WorkspacePageView,
)
from zhiyin_business.ports.function import ExportResult
from zhiyin_business.ports.loop import LoopResult
from zhiyin_business.ports.orchestrator import ConversationHistory, TurnResult
from zhiyin_business.ports.workspace import StagePanel, WorkspaceView
from zhiyin_business.services.loop import STAGE_LABELS
from zhiyin_kernel.assets import ActionPlan, CalendarNode, DirectionPlan, Report
from zhiyin_kernel.blackboard import AssetVersion, TaskSession
from zhiyin_kernel.dynamic_content import (
    BannerSpec,
    FaqSpec,
    MenuSpec,
    RouteSpec,
    TrustBlockSpec,
)
from zhiyin_kernel.identity import UserAccount
from zhiyin_kernel.registry import AgentCapability, AgentDescriptor, TaskEntrySpec
from zhiyin_kernel.enums import LoopStage, TaskStatus


# ---------------------------------------------------------------------------
# 启动装配（app_controller → /app/bootstrap）
# ---------------------------------------------------------------------------


def bootstrap_view(
    *,
    copy_bundle: dict[str, str],
    menus: Sequence[MenuSpec],
    routes: Sequence[RouteSpec],
    task_entries: Sequence[TaskEntrySpec],
    agents: dict[str, AgentDescriptor],
    capabilities: Sequence[AgentCapability] = (),
    trust_blocks: Sequence[TrustBlockSpec] = (),
    banners: Sequence[BannerSpec] = (),
    faqs: Sequence[FaqSpec] = (),
    feature_flags: Optional[dict[str, bool]] = None,
    identity: Optional[UserAccount] = None,
) -> BootstrapView:
    """拼首页启动视图。

    口径：
    - `app_name` 取 `copy_bundle["app.name"]`，取不到就留空字符串——**不要回落硬编码**，
      空值会让"文案包缺了"在联调时立刻可见；
    - 任务入口的 `lead_agent_name` 由 `agents[lead_agent].name` 解析，取不到时为 None
      （前端回落显示 agent_id，不静默编名字）；
    - 身份区为 `None`（游客）时 identity 留空 dict；
    - `capabilities`（能力池）由业务层解析好、按注册表顺序给出，mapper 只做形状翻译，
      **不猜任何字段**（环节与理论名都不在这里反推）。
    """
    catalog = [
        AgentView(
            id=item.agent.id,
            name=item.agent.name,
            role_summary=item.agent.role_summary,
            stages=list(item.stages),
            theories=[AgentTheoryView(id=card.id, name=card.name) for card in item.theories],
            tools=list(item.agent.tools),
            not_to_do=list(item.agent.not_to_do),
        )
        for item in capabilities
    ]
    return BootstrapView(
        app_name=copy_bundle.get("app.name", ""),
        menus=[
            MenuView(
                key=item.code,
                label=item.label,
                route=item.route,
                visible=item.visible,
                sort_order=item.sort_order,
            )
            for item in menus
        ],
        routes=[
            RouteView(
                path=item.path,
                page_code=item.page_code,
                require_login=item.require_login,
                sort_order=item.sort_order,
            )
            for item in routes
        ],
        task_entries=[
            TaskEntryView(
                code=item.code,
                label=item.label,
                target_stage=item.target_stage,
                lead_agent_name=(
                    agents[item.lead_agent].name
                    if item.lead_agent and item.lead_agent in agents
                    else None
                ),
                sort_order=item.sort_order,
            )
            for item in task_entries
        ],
        copy_bundle=dict(copy_bundle),
        trust_blocks=[
            TrustBlockView(
                code=item.code,
                title=item.title,
                body=item.body,
                expandable_ref=item.expandable_ref,
            )
            for item in trust_blocks
        ],
        banners=[
            BannerView(
                code=item.code,
                title=item.title,
                body=item.body,
                action_label=item.action_label,
                action_route=item.action_route,
            )
            for item in banners
        ],
        faqs=[
            FaqView(code=item.code, question=item.question, answer=item.answer)
            for item in faqs
        ],
        feature_flags=dict(feature_flags or {}),
        agents=catalog,
        identity=(
            {
                "user_id": identity.id,
                "role": identity.role.value,
                "nickname": identity.nickname,
                "avatar": identity.avatar_url or "",
            }
            if identity is not None
            else {}
        ),
    )


# ---------------------------------------------------------------------------
# 对话页（conversation_controller）
# ---------------------------------------------------------------------------


def task_session_view(
    session: TaskSession,
    *,
    task_name: str,
    lead_agent_name: str = "",
    progress: float = 0.0,
) -> TaskSessionView:
    """左栏会话项。`task_name` 取自动态任务入口文案，不按 agent 名排布。"""
    return TaskSessionView(
        task_id=session.id,
        task_name=task_name,
        stage=session.loop_stage,
        stage_label=STAGE_LABELS[session.loop_stage],
        lead_agent_name=lead_agent_name,
        status=session.status,
        progress=progress,
        last_active_at=session.updated_at,
    )


def session_list_view(
    sessions: Sequence[TaskSessionView], *, current_task_id: Optional[str] = None
) -> SessionListView:
    """左栏会话列表。"""
    return SessionListView(sessions=list(sessions), current_task_id=current_task_id)


def session_summary_view(
    panel: StagePanel, *, lead_agent_name: str = ""
) -> TaskSessionView:
    """把会话记忆摘要转换为左栏会话项。"""
    return TaskSessionView(
        task_id=panel.task_id or "",
        task_name=panel.title,
        stage=panel.stage,
        stage_label=STAGE_LABELS[panel.stage],
        lead_agent_name=lead_agent_name,
        status=TaskStatus.ACTIVE,
        progress=(list(LoopStage).index(panel.stage) + 1) / len(LoopStage),
        last_active_at=panel.updated_at,
    )


def conversation_turn_view(turn: TurnResult) -> ConversationTurnView:
    """一轮回复：最短结论 + 显式告知 + 行为引导 + 管线卡。"""
    return ConversationTurnView(
        task_id=turn.task_id,
        stage=turn.stage,
        badge=turn.badge.model_dump(mode="json"),
        messages=[
            ConversationMessageView(
                **message.model_dump(mode="python"),
                agent_name=(turn.badge.name if message.agent_id == turn.badge.agent_id else None),
            )
            for message in turn.messages
        ],
        disclosure=(turn.disclosure.model_dump(mode="json") if turn.disclosure else None),
        guide=turn.guide.model_dump(mode="json"),
        pipeline_cards=pipeline_cards(turn.session, turn.asset_versions),
        changed_assets=[item.model_dump(mode="json") for item in turn.asset_versions],
    )


def conversation_history_view(
    history: ConversationHistory,
    *,
    asset_versions: Sequence[AssetVersion],
    agents: Optional[dict[str, AgentDescriptor]] = None,
) -> ConversationHistoryView:
    """会话既成事实 → 前端可恢复的对话流与环节进度。

    `agents` 是"agent_id → 注册表描述"的解析结果，由 Facade 取（mapper 不取数）；
    取不到就留空名字，**不编造中文名**，前端回落显示 agent_id。
    """
    session = history.session
    if session is None:  # pragma: no cover - read_history 保证会话存在
        raise ValueError(f"会话历史缺少会话当前态：{history.task_id}")
    catalog = agents or {}
    lead = catalog.get(session.lead_agent or "")
    return ConversationHistoryView(
        task_id=history.task_id,
        stage=session.loop_stage,
        stage_label=STAGE_LABELS[session.loop_stage],
        badge={
            "agent_id": session.lead_agent,
            "name": lead.name if lead else "",
            "role_summary": lead.role_summary if lead else "",
        },
        messages=[
            ConversationMessageView(
                **message.model_dump(mode="python"),
                agent_name=(
                    catalog[message.agent_id].name
                    if message.agent_id in catalog
                    else None
                ),
            )
            for message in history.messages
        ],
        pipeline_cards=pipeline_cards(session, asset_versions),
    )


def pipeline_cards(
    session: TaskSession, asset_versions: Sequence[AssetVersion]
) -> list[PipelineCardView]:
    """右栏 ①-⑤ 管线卡（三态：当前产出 / 理论模型 / 评价状态）。"""
    order = list(LoopStage)
    current_index = order.index(session.loop_stage)
    latest = {item.asset_type.value: item for item in asset_versions}
    stage_assets = {
        LoopStage.DIAGNOSE: "report",
        LoopStage.DECIDE: "direction_plan",
        LoopStage.ACT: "action_plan",
    }
    cards = []
    for index, stage in enumerate(order):
        version = latest.get(stage_assets.get(stage, ""))
        status = "done" if index < current_index else "in_progress" if index == current_index else "empty"
        cards.append(
            PipelineCardView(
                stage=stage,
                title=STAGE_LABELS[stage],
                active=stage is session.loop_stage,
                status=status,
                current_output=(version.model_dump(mode="json") if version else None),
                evaluation={"version": version.version} if version else None,
            )
        )
    return cards


def loop_stage_view(result: LoopResult) -> dict:
    """单个环节的产出摘要（供管线卡与工作台共用，避免两处各写一遍摘要口径）。"""
    return {
        "stage": result.stage.value,
        "messages": [item.model_dump(mode="json") for item in result.messages],
        "guide": result.guide.model_dump(mode="json"),
        "next_stage": result.next_stage.value if result.next_stage else None,
    }


# ---------------------------------------------------------------------------
# 工作台（workspace_controller）
# ---------------------------------------------------------------------------


def workspace_page_view(view: WorkspaceView) -> WorkspacePageView:
    """工作台 ①-⑤ 聚合视图。

    覆盖率与整体置信度**直接取业务层算好的值**，本函数不再自行计算：
    此前这里内联了「字段数 /(字段数+缺口数)」与「全字段等权平均」，
    与决策 5（关键字段口径）不是一回事，同一口径在两处各写一遍必然漂移
    （OPEN-6）。映射层只做形状转换。
    """
    profile = view.profile
    profile_panel = ProfilePanelView(
        coverage=view.profile_coverage,
        overall_confidence=view.profile_overall_confidence,
        fields=[item.model_dump(mode="json") for item in profile.fields] if profile else [],
        gaps=[item.model_dump(mode="json") for item in profile.gaps] if profile else [],
        updated_at=profile.updated_at if profile else None,
    )
    by_stage = {panel.stage: _stage_panel_view(panel) for panel in view.panels}
    return WorkspacePageView(
        profile_panel=profile_panel,
        report_panel=by_stage.get(LoopStage.DIAGNOSE),
        plan_panel=by_stage.get(LoopStage.DECIDE),
        action_panel=by_stage.get(LoopStage.ACT),
        calendar_nodes=[item.model_dump(mode="json") for item in view.calendar_nodes],
        review_panel=by_stage.get(LoopStage.REVIEW),
        coach_messages=[
            item.model_dump(mode="json")
            for item in view.track_events
            if item.type == "coach_message"
        ],
        dependencies=[
            DependencyEdgeView(**item.model_dump(mode="python"))
            for item in view.dependencies
        ],
        blocks={
            "available": view.available_blocks,
            "achievement_badge_keys": view.achievement_badge_keys,
        },
    )


# ---------------------------------------------------------------------------
# 资产（asset_controller）
# ---------------------------------------------------------------------------


def asset_version_view(
    version: AssetVersion, *, previous: Optional[AssetVersion] = None
) -> AssetVersionView:
    """资产版本视图。`diff_from_previous` 由两版内容差异生成，不整篇重排。"""
    return AssetVersionView(
        asset_type=version.asset_type,
        asset_id=version.id,
        version=version.version,
        created_at=version.created_at,
        depends_on_profile_keys=version.depends_on_profile_keys,
        diff_from_previous=version.diff_from_previous,
    )


def report_full_text_view(
    report: Report,
    *,
    direction_plans: Sequence[DirectionPlan] = (),
    action_plan: Optional[ActionPlan] = None,
) -> ReportFullTextView:
    """完整报告页正文（只读资产版本，不重新生成）。

    报告页要展示的**不只是②诊断**：③方向方案与④行动计划同样是"活资产"，必须一并
    下发，否则页面只能显示空态。此前这两个能力已经在业务层聚合
    （`WorkspaceView.direction_plans` / `action_plan`），但 API 层从未引用过它们，
    mapper 把它们丢掉了——所以前端拿不到真实方案，只能用编造内容顶替。

    报告正文还要含「个人画像」（《前端页面设计》§4.4 第 243 行），但用的是
    **报告里的画像快照**（`Report.profile_snapshot`），不是当前活画像：本页是
    "只读资产版本"，实时画像会让报告 v1 里显示今天的画像、与工作台对不上。
    旧报告没有快照（字段为空）→ 不生成该章节。

    没有数据的区块**不生成**：目录与正文保持一致，不在报告里放空章节。
    差距清单（`report.gaps`）同样只在有明细时生成，并把 `gap_claims` 折叠成
    `claimed` 布尔，让前端能直接渲染"已认领"状态（FR-DIAG-003/004）。
    """
    toc = [
        {"id": "verdict", "title": "综合结论"},
        {"id": "swot", "title": "SWOT"},
        *[
            {"id": f"dimension-{index}", "title": group.group}
            for index, group in enumerate(report.dimensions, start=1)
        ],
    ]
    sections = [
        {"id": "verdict", "title": report.verdict.title, "content": report.verdict.model_dump(mode="json")},
        {"id": "swot", "title": "SWOT", "content": report.swot.model_dump(mode="json")},
        *[
            {
                "id": f"dimension-{index}",
                "title": group.group,
                "content": group.model_dump(mode="json"),
            }
            for index, group in enumerate(report.dimensions, start=1)
        ],
    ]

    if report.gaps:
        # 差距清单是②诊断的产出，也是「认领差距」的唯一依据：前端在这里渲染每条
        # 差距的要求/现状/建议，并用 `claimed` 决定按钮是"认领"还是"已认领"。
        # 旧报告没有 gaps → 不生成该区块（目录与正文保持一致）。
        claimed = {claim.gap_id for claim in report.gap_claims}
        toc.append({"id": "gaps", "title": "差距清单"})
        sections.append(
            {
                "id": "gaps",
                "title": "差距清单",
                "content": {
                    "items": [
                        {**gap.model_dump(mode="json"), "claimed": gap.gap_id in claimed}
                        for gap in report.gaps
                    ],
                },
            }
        )
    if direction_plans:
        toc.append({"id": "directions", "title": "方向方案"})
        sections.append(
            {
                "id": "directions",
                "title": "方向方案",
                "content": {
                    "plans": [plan.model_dump(mode="json") for plan in direction_plans],
                },
            }
        )
    if action_plan is not None:
        toc.append({"id": "action", "title": "行动计划"})
        sections.append(
            {
                "id": "action",
                "title": "行动计划",
                "content": action_plan.model_dump(mode="json"),
            }
        )
    # 个人画像放最后，与《前端页面设计》§4.4 的枚举顺序一致
    # （"含 15 维全景、方案、行动计划、个人画像"）。
    if report.profile_snapshot:
        toc.append({"id": "profile", "title": "个人画像"})
        sections.append(
            {
                "id": "profile",
                "title": "个人画像",
                "content": {
                    "snapshot_of": report.generated_at.isoformat(),
                    "fields": [
                        field.model_dump(mode="json") for field in report.profile_snapshot
                    ],
                },
            }
        )

    return ReportFullTextView(
        report_id=report.id,
        version=report.version,
        generated_at=report.generated_at,
        toc=toc,
        sections=sections,
    )


def export_result_view(result: ExportResult) -> ExportResultView:
    """导出结果。第一期 `available` 恒 False（占位）。"""
    return ExportResultView(
        available=result.available,
        message=result.message,
        object_key=result.object_key,
    )


def gap_claim_view(report: Report, gap_id: str) -> GapClaimView:
    """认领结果。`claimed_gap_ids` 是全量清单，前端无需再拉一次报告。"""
    claim = next((item for item in report.gap_claims if item.gap_id == gap_id), None)
    if claim is None:
        raise LookupError(f"报告未记录该差距的认领：{gap_id}")
    return GapClaimView(
        gap_id=gap_id,
        claimed_at=claim.claimed_at,
        claimed_gap_ids=[item.gap_id for item in report.gap_claims],
    )


def decision_selection_view(plan: DirectionPlan) -> DecisionSelectionView:
    """选择结果：前端据此高亮选中的方案并允许撤回。"""
    return DecisionSelectionView(
        plan_id=plan.id,
        role=plan.role,
        name=plan.name,
        match_score=plan.match_score,
        selected_at=plan.selected_at,
    )


def task_done_view(plan: ActionPlan, task_id: str) -> TaskDoneView:
    """勾选结果：定位命中的那条任务，并带上整体完成进度。"""
    tasks = [task for phase in plan.phases for task in phase.tasks]
    for phase in plan.phases:
        for task in phase.tasks:
            if _task_identity(phase.name, task.text) == task_id or task.text == task_id:
                return TaskDoneView(
                    plan_id=plan.id,
                    task_id=task_id,
                    phase=phase.name,
                    text=task.text,
                    done=task.done,
                    done_at=task.done_at,
                    done_total=sum(1 for item in tasks if item.done),
                    task_total=len(tasks),
                )
    # Repository 已在 `mark_task_done` 命中后才返回，走不到这里；真走到说明两边
    # 的任务标识口径已经不一致，显式失败好过返回一条对不上的"成功"。
    raise LookupError(f"行动任务不存在：{task_id}")


def calendar_node_view(node: CalendarNode) -> CalendarNodeView:
    """日历节点视图。"""
    return CalendarNodeView(
        node_id=node.node_id,
        title=node.title,
        due_at=node.due_at,
        source=node.source,
        related_task_text=node.related_task_text,
    )


def _task_identity(phase_name: str, text: str) -> str:
    """行动任务的复合标识 `阶段名:任务文本`。

    本函数是**只读定位**用的，口径必须与 Repository 的 `mark_task_done`
    （`InMemory` / `SqlAlchemy` 两处）保持一致；三处任一处改了任务标识规则，
    勾选结果的阶段与文本就会错位。
    """
    return f"{phase_name}:{text}"


def _stage_panel_view(panel: StagePanel) -> StagePanelView:
    return StagePanelView(
        stage=panel.stage,
        title=panel.title,
        evaluation=panel.evaluation,
        theory_models=[item.model_dump(mode="json") for item in panel.theory_refs],
        version=panel.version,
        diff=panel.diff_from_previous,
        updated_at=panel.updated_at,
    )


__all__ = [
    "asset_version_view",
    "bootstrap_view",
    "calendar_node_view",
    "conversation_turn_view",
    "decision_selection_view",
    "export_result_view",
    "gap_claim_view",
    "loop_stage_view",
    "pipeline_cards",
    "report_full_text_view",
    "session_list_view",
    "session_summary_view",
    "task_done_view",
    "task_session_view",
    "workspace_page_view",
]
