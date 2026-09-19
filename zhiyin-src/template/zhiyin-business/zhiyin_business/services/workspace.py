"""工作台聚合服务实现。

落位：`business/services/workspace.py`；第一期排期实现工位：后端-2（数据访问负责人）。
依赖：读侧聚合（Profile / Asset / Memory / Behavior 的 Port）。

读写路径分离（《目标架构设计》§5.5）的读侧：**本类不写任何状态、不发任何事件**。
允许轻微陈旧，允许 `asyncio.gather` 并发聚合 + 部分失败降级；不得在此做写侧重算。
"""

from __future__ import annotations

import asyncio
from typing import Awaitable, TypeVar

from zhiyin_business.policies.profile import (
    PROFILE_COLLECTION_POLICY,
    calculate_coverage,
    calculate_overall_confidence,
)
from zhiyin_business.ports.blackboard import (
    AssetService,
    BehaviorService,
    ConversationMemoryService,
    ProfileService,
)
from zhiyin_business.ports.function import FunctionService
from zhiyin_business.ports.workspace import (
    DependencyEdge,
    StagePanel,
    WorkspaceService,
    WorkspaceView,
)
from zhiyin_business.services.loop import STAGE_LABELS
from zhiyin_data_sdk.gateways.feature_flag import FeatureFlagGateway
from zhiyin_data_sdk.repositories import RegistryRepository, TaskSessionRepository
from zhiyin_kernel.assets import TrackEvent
from zhiyin_kernel.enums import AssetType, BehaviorEventType, LoopStage

T = TypeVar("T")


class DefaultWorkspaceService(WorkspaceService):
    """工作台聚合默认实现；各读侧独立降级，不产生写副作用。"""

    IMPLEMENTATION_STATUS = "wired"

    def __init__(
        self,
        *,
        profiles: ProfileService,
        assets: AssetService,
        memories: ConversationMemoryService,
        behaviors: BehaviorService,
        registry: RegistryRepository,
        features: FeatureFlagGateway,
        sessions: TaskSessionRepository,
        functions: FunctionService,
    ) -> None:
        self._profiles = profiles
        self._assets = assets
        self._memories = memories
        self._behaviors = behaviors
        # 会话记录用于左栏会话列表取"任务名"（`task_name`），见 `list_sessions_summary`。
        self._sessions = sessions
        # 覆盖率与整体置信度的口径来自动态资源，必须由业务层读取并计算后透传。
        self._registry = registry
        # 「可用功能块」= 功能开关里 enabled 的那些，见 `_available_blocks`。
        self._features = features
        # 关键节点日历（FR-BLOCK-002）的读路径：节点由功能块服务登记，工作台只读转出。
        self._functions = functions

    async def _available_blocks(self) -> list[str]:
        """可用功能块 = `feature_flags` 里 enabled 的条目。

        此前这里是一份**写死在 Python 里的字面量清单**，把 `export` / `mentor`
        （注册表里 `enabled: false`）与 `demo` 一并列成"available"。两个问题：
        一是《AGENTS.md》§8 明确禁止把功能开关硬编码进 Python；二是语义错——
        `available` 应当就是 `enabled`，否则前端按它渲染入口就会放出没开放的功能。
        改为从开关派生后，加一个功能块只需改 `data/registry/feature_flags.json`。
        """
        flags = await self._features.all()
        return sorted(code for code, enabled in flags.items() if enabled)

    async def build_view(self, user_id: str) -> WorkspaceView:
        (
            profile,
            report,
            report_versions,
            direction_versions,
            action_versions,
            plans,
            action_plan,
            behaviors,
            calendar_nodes,
        ) = await asyncio.gather(
            _safe(self._profiles.get(user_id), None),
            _safe(self._assets.get_report(user_id), None),
            _safe(self._assets.list_versions(user_id, AssetType.REPORT), []),
            _safe(self._assets.list_versions(user_id, AssetType.DIRECTION_PLAN), []),
            _safe(self._assets.list_versions(user_id, AssetType.ACTION_PLAN), []),
            _safe(self._assets.list_direction_plans(user_id), []),
            _safe(self._assets.get_action_plan(user_id), None),
            _safe(self._behaviors.recent(user_id, limit=200), []),
            # 日历读不出来不影响其余四层：与上面各读侧一样降级为空列表，
            # 不因为对象存储抖一下就把整个工作台打成错误页。
            _safe(self._functions.list_calendar_nodes(user_id), []),
        )

        versions = [*report_versions, *direction_versions, *action_versions]
        latest_by_type = {}
        for version in versions:
            latest_by_type[version.asset_type] = version

        panels = [
            StagePanel(
                stage=LoopStage.COLLECT,
                title=STAGE_LABELS[LoopStage.COLLECT],
                evaluation=_profile_evaluation(profile),
                updated_at=profile.updated_at if profile is not None else None,
            ),
            StagePanel(
                stage=LoopStage.DIAGNOSE,
                title=STAGE_LABELS[LoopStage.DIAGNOSE],
                evaluation=report.verdict.summary if report is not None else "尚未生成诊断报告",
                **_version_fields(latest_by_type.get(AssetType.REPORT)),
            ),
            StagePanel(
                stage=LoopStage.DECIDE,
                title=STAGE_LABELS[LoopStage.DECIDE],
                evaluation=_plan_evaluation(plans),
                **_version_fields(latest_by_type.get(AssetType.DIRECTION_PLAN)),
            ),
            StagePanel(
                stage=LoopStage.ACT,
                title=STAGE_LABELS[LoopStage.ACT],
                evaluation=_action_evaluation(action_plan),
                **_version_fields(latest_by_type.get(AssetType.ACTION_PLAN)),
            ),
            StagePanel(
                stage=LoopStage.REVIEW,
                title=STAGE_LABELS[LoopStage.REVIEW],
                evaluation=f"已有 {len(behaviors)} 条行为记录" if behaviors else "尚无复盘记录",
                updated_at=behaviors[0].occurred_at if behaviors else None,
            ),
        ]
        dependencies = [
            DependencyEdge(
                from_asset=f"profile.{key}",
                to_asset=version.asset_type.value,
                via_profile_keys=[key],
            )
            for version in latest_by_type.values()
            for key in version.depends_on_profile_keys
        ]
        track_events = [_behavior_to_track(log) for log in behaviors if _is_track_event(log)]
        badge_keys = sorted(
            {
                badge
                for log in behaviors
                for badge in [_badge_for(log.event_type)]
                if badge is not None
            }
        )
        coverage, overall_confidence = await self._profile_metrics(profile)
        return WorkspaceView(
            user_id=user_id,
            profile=profile,
            report=report,
            report_versions=report_versions,
            direction_plans=plans,
            action_plan=action_plan,
            calendar_nodes=calendar_nodes,
            track_events=track_events,
            panels=panels,
            dependencies=dependencies,
            achievement_badge_keys=badge_keys,
            available_blocks=await self._available_blocks(),
            profile_coverage=coverage,
            profile_overall_confidence=overall_confidence,
        )

    async def _profile_metrics(self, profile) -> tuple[float, float]:
        """按 `policy_params.profile_collection` 计算覆盖率与整体置信度。

        没有画像时两者都是 0.0，此时不必读参数（空画像不存在口径问题）。
        有画像但读不到参数时**显式报错**：宁可让配置问题暴露，也不用近似公式
        顶上一个看起来正常的数字——那正是 OPEN-6 要收敛掉的漂移。
        """
        if profile is None:
            return 0.0, 0.0
        params = await self._registry.get_policy_params(PROFILE_COLLECTION_POLICY)
        if params is None:
            raise RuntimeError("缺少动态规则参数：profile_collection")
        return (
            calculate_coverage(profile.fields, params),
            calculate_overall_confidence(profile.fields, params),
        )

    async def list_sessions_summary(self, user_id: str) -> list[StagePanel]:
        """左栏会话摘要。

        `title` 在这里的含义是**该会话的显示名**，取会话记录里的 `task_name`
        （= 动态任务入口文案）；拿不到才回落到环节名。

        为什么要专门说明：`StagePanel.title` 在环节面板那条路上是"环节名"，而会话摘要
        这条路把它当"任务名"用。此前摘要直接写 `STAGE_LABELS[...]`，于是左栏显示的是
        "② 诊断匹配"而不是用户当初选的"想验证某方向行不行"——而且 `task/enter` 返回的是
        入口文案，前端把它 push 进列表后**刷新一次名字就变了**。
        """
        memories = await self._memories.list_by_user(user_id)
        # 一次批量取回该用户的会话，避免按会话逐条查（N+1）
        sessions = {
            session.id: session for session in await self._sessions.list_by_user(user_id)
        }
        # 历史行的 `task_name` 曾直接写 `task_code`（旧口径），读时用动态入口文案兜住，
        # 免得为了显示正确去做一次数据回填——"名字等于 code"就当作"没设置过"。
        labels = {
            entry.code: entry.label for entry in await self._registry.list_task_entries()
        }
        panels: list[StagePanel] = []
        for memory in memories:
            session = sessions.get(memory.task_id or "")
            stored = session.task_name if session else ""
            if session and (not stored or stored == session.task_code):
                stored = labels.get(session.task_code, "")
            panels.append(
                StagePanel(
                    stage=memory.loop_stage,
                    title=stored or STAGE_LABELS[memory.loop_stage],
                    evaluation=memory.summary,
                    updated_at=memory.last_active_at,
                    task_id=memory.task_id,
                    lead_agent=memory.lead_agent,
                )
            )
        return panels


async def _safe(awaitable: Awaitable[T], default: T) -> T:
    try:
        return await awaitable
    except Exception:
        return default


def _version_fields(version) -> dict:
    if version is None:
        return {}
    return {
        "version": version.version,
        "diff_from_previous": version.diff_from_previous,
        "updated_at": version.created_at,
    }


def _profile_evaluation(profile) -> str:
    if profile is None:
        return "尚未建立画像"
    return f"已确认 {len(profile.fields)} 个画像字段，仍有 {len(profile.gaps)} 个缺口"


def _plan_evaluation(plans) -> str:
    selected = next((plan for plan in plans if plan.selected), None)
    if selected is not None:
        return f"当前选择：{selected.name}"
    return f"已有 {len(plans)} 套方向方案" if plans else "尚未生成方向方案"


def _action_evaluation(plan) -> str:
    if plan is None:
        return "尚未生成行动计划"
    tasks = [task for phase in plan.phases for task in phase.tasks]
    done = sum(task.done for task in tasks)
    return f"已完成 {done}/{len(tasks)} 个行动任务"


def _is_track_event(log) -> bool:
    return log.event_type in {
        BehaviorEventType.TASK_DONE,
        BehaviorEventType.TASK_STALL,
        BehaviorEventType.REVIEW,
    }


def _behavior_to_track(log) -> TrackEvent:
    if log.event_type is BehaviorEventType.TASK_DONE:
        event_type, title = "milestone_done", "完成行动任务"
    elif log.event_type is BehaviorEventType.TASK_STALL:
        event_type, title = "warning", "行动任务出现停滞"
    else:
        event_type, title = "semester_review", "完成一次复盘"
    return TrackEvent(
        id=f"track_{log.id}",
        user_id=log.user_id,
        type=event_type,
        title=title,
        detail=str(log.payload.get("detail", "")),
        occurred_at=log.occurred_at,
        related_task_id=str(log.payload.get("task_id") or "") or None,
        related_stage=str(log.payload.get("stage") or "") or None,
    )


def _badge_for(event_type: BehaviorEventType) -> str | None:
    return {
        BehaviorEventType.GAP_CLAIM: "first_gap_claimed",
        BehaviorEventType.DECISION_SELECT: "direction_selected",
        BehaviorEventType.DECISION_RESELECT: "direction_reselected",
        BehaviorEventType.TASK_DONE: "first_task_done",
        BehaviorEventType.REVIEW: "first_review_completed",
    }.get(event_type)


__all__ = ["DefaultWorkspaceService"]
