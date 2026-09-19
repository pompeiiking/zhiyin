"""业务编排负责人第二波收口测试。"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from zhiyin_boot import Settings, build_container
from zhiyin_business.policies.axis_a import RuleFirstAxisAInferencePolicy
from zhiyin_business.ports.blackboard import BlackboardView
from zhiyin_business.ports.orchestrator import (
    IntentType,
    LeadDecision,
    StageDecision,
)
from zhiyin_kernel.blackboard import BehaviorLog, Profile, ProfileField, TaskSession
from zhiyin_kernel.enums import (
    AxisAStage,
    BehaviorEventType,
    LoopStage,
    PathFocus,
    ProfileSource,
    TaskStatus,
)
from zhiyin_orchestration import AgentRequest, AgentResult


DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def _container():
    return build_container(
        Settings(
            env="test",
            local_data_dir=str(DATA_DIR),
            local_registry_dir=str(DATA_DIR / "registry"),
            local_knowledge_dir=str(DATA_DIR / "knowledge"),
            local_object_dir=str(DATA_DIR / "objects"),
            redis_url="",
        )
    )


def _behavior(event_type: BehaviorEventType) -> BehaviorLog:
    return BehaviorLog(
        id=f"bhv_{event_type.value}",
        user_id="u1",
        event_type=event_type,
        occurred_at=datetime.now(timezone.utc),
    )


@pytest.mark.parametrize(
    ("event_type", "expected"),
    [
        (BehaviorEventType.TASK_STALL, AxisAStage.REPOSITION),
        (BehaviorEventType.DECISION_RESELECT, AxisAStage.REPOSITION),
        (BehaviorEventType.REVIEW, AxisAStage.ADAPT),
        (BehaviorEventType.TASK_DONE, AxisAStage.SPRINT_ACTION),
    ],
)
def test_axis_a_policy_prioritizes_latest_key_behavior(
    event_type: BehaviorEventType,
    expected: AxisAStage,
) -> None:
    policy = RuleFirstAxisAInferencePolicy()
    board = BlackboardView(user_id="u1", recent_behaviors=[_behavior(event_type)])

    assert policy.infer(blackboard=board, path_focus=None) is expected


def test_axis_a_policy_uses_profile_and_leaves_ambiguous_state_to_model() -> None:
    policy = RuleFirstAxisAInferencePolicy()
    now = datetime.now(timezone.utc)
    target_profile = Profile(
        id="profile-1",
        user_id="u1",
        updated_at=now,
        fields=[
            ProfileField(
                key="target_direction",
                value="数据工程",
                confidence=0.8,
                source=ProfileSource.CONVERSATION,
                updated_at=now,
            )
        ],
    )
    ambiguous_profile = target_profile.model_copy(
        update={
            "fields": [
                target_profile.fields[0].model_copy(update={"key": "major", "value": "计算机"})
            ]
        }
    )

    assert (
        policy.infer(
            blackboard=BlackboardView(user_id="u1", profile=target_profile),
            path_focus=None,
        )
        is AxisAStage.VERIFY_DIRECTION
    )
    assert (
        policy.infer(blackboard=BlackboardView(user_id="u1"), path_focus=None)
        is AxisAStage.EXPLORE_SELF
    )
    assert (
        policy.infer(
            blackboard=BlackboardView(user_id="u1", profile=ambiguous_profile),
            path_focus=PathFocus.EMPLOYMENT,
        )
        is None
    )


class _AxisEngine:
    def __init__(self, result: AgentResult) -> None:
        self.result = result
        self.requests: list[AgentRequest] = []

    async def invoke(self, request: AgentRequest) -> AgentResult:
        self.requests.append(request)
        return self.result


@pytest.mark.asyncio
async def test_axis_a_model_fallback_receives_path_focus_and_dynamic_agent() -> None:
    container = _container()
    user_id = "axis-model-user"
    task_id = "axis-model-task"
    await container.profile_service.update_field(
        user_id,
        "major",
        "计算机",
        confidence=0.9,
        source="conversation",
    )
    now = datetime.now(timezone.utc)
    await container.sessions.create(
        TaskSession(
            id=task_id,
            user_id=user_id,
            task_code="confused",
            task_name="阶段推断测试",
            loop_stage=LoopStage.COLLECT,
            lead_agent="profile_analyst",
            path_focus=PathFocus.EMPLOYMENT,
            status=TaskStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
    )
    engine = _AxisEngine(
        AgentResult(
            agent_id="dynamic",
            structured={"stage": AxisAStage.ADAPT.value, "reason": "test"},
            valid=True,
        )
    )
    container.orchestrator._agent_engine = engine

    assert await container.orchestrator.infer_axis_a(user_id, task_id) is AxisAStage.ADAPT
    assert engine.requests
    assert engine.requests[0].agent_id == "profile_analyst"
    assert engine.requests[0].prompt_vars["path_focus"] == PathFocus.EMPLOYMENT.value


@pytest.mark.asyncio
async def test_free_chat_clarifies_once_then_falls_back_and_records_both_turns() -> None:
    from zhiyin_api.dto.conversation import MessageRequest, TaskEnterRequest

    container = _container()
    user_id = "routing-user"
    session = await container.facade.enter_task(user_id, TaskEnterRequest(task_code="free_chat"))

    first = await container.facade.send_message(
        user_id,
        MessageRequest(task_id=session.task_id, message="先随便聊聊"),
    )
    assert first.guide["kind"] == "question"

    second = await container.facade.send_message(
        user_id,
        MessageRequest(task_id=session.task_id, message="还是不知道从哪开始"),
    )
    assert second.stage is LoopStage.COLLECT
    logs = await container.behavior_service.recent(user_id, event_types=[BehaviorEventType.ANSWER])
    assert len(logs) == 2
    memory = await container.memory_service.get(user_id, session.task_id)
    assert memory is not None
    assert "先随便聊聊" in memory.summary
    assert "还是不知道从哪开始" in memory.summary


@pytest.mark.asyncio
async def test_successful_route_clears_previous_clarification_count() -> None:
    from zhiyin_api.dto.conversation import MessageRequest, TaskEnterRequest

    container = _container()
    user_id = "routing-reset-user"
    session = await container.facade.enter_task(user_id, TaskEnterRequest(task_code="free_chat"))
    await container.facade.send_message(
        user_id,
        MessageRequest(task_id=session.task_id, message="先随便聊聊"),
    )
    routed = await container.facade.send_message(
        user_id,
        MessageRequest(task_id=session.task_id, message="方向定了但不知道怎么行动"),
    )
    assert routed.stage is LoopStage.ACT

    clarified_again = await container.facade.send_message(
        user_id,
        MessageRequest(task_id=session.task_id, message="再随便聊聊"),
    )
    assert clarified_again.guide["kind"] == "question"


class _CapturingStagePolicy:
    def __init__(self) -> None:
        self.messages: list[str] = []

    async def decide(self, *, blackboard, intent, message):
        self.messages.append(message)
        return StageDecision(stage=LoopStage.ACT, confidence=1.0)


class _CountingLeadPolicy:
    def __init__(self) -> None:
        self.calls: list[tuple[AxisAStage, LoopStage, IntentType]] = []

    async def select(self, *, blackboard, axis_a, stage, intent):
        self.calls.append((axis_a, stage, intent))
        return LeadDecision(
            lead_agent="path_planner",
            reason="按本轮真实意图切换主理",
        )


@pytest.mark.asyncio
async def test_handle_message_passes_original_text_and_reuses_preselected_lead() -> None:
    from zhiyin_api.dto.conversation import MessageRequest, TaskEnterRequest

    container = _container()
    stage_policy = _CapturingStagePolicy()
    lead_policy = _CountingLeadPolicy()
    container.orchestrator._stage_policy = stage_policy
    container.orchestrator._lead_policy = lead_policy
    session = await container.facade.enter_task(
        "handoff-user", TaskEnterRequest(task_code="confused")
    )
    message = "这是必须原样传给环节策略的用户输入"

    turn = await container.facade.send_message(
        "handoff-user",
        MessageRequest(task_id=session.task_id, message=message),
    )

    assert stage_policy.messages == [message]
    assert len(lead_policy.calls) == 1
    assert lead_policy.calls[0][2] is IntentType.FREE_CHAT
    assert turn.badge["agent_id"] == "path_planner"
    assert turn.disclosure is not None


class _RegistryWithoutRouting:
    def __init__(self, delegate) -> None:
        self._delegate = delegate

    def __getattr__(self, name):
        return getattr(self._delegate, name)

    async def get_policy_params(self, code: str):
        return None


class _RegistryWithInvalidRouting(_RegistryWithoutRouting):
    async def get_policy_params(self, code: str):
        from zhiyin_kernel.registry import PolicyParamSet

        return PolicyParamSet(
            code="routing",
            status="confirmed",
            value={"clarify_attempts": True, "fallback_stage": "collect"},
        )


@pytest.mark.asyncio
async def test_missing_routing_params_fail_explicitly() -> None:
    container = _container()
    container.orchestrator._registry = _RegistryWithoutRouting(container.registry)

    with pytest.raises(RuntimeError, match="routing 规则参数缺失"):
        await container.orchestrator._apply_routing_fallback(
            "u1",
            "task1",
            StageDecision(stage=None, need_clarify=True, clarify_question="请澄清"),
        )

    container.orchestrator._registry = _RegistryWithInvalidRouting(container.registry)
    with pytest.raises(RuntimeError, match="clarify_attempts"):
        await container.orchestrator._apply_routing_fallback(
            "u1",
            "task1",
            StageDecision(stage=None, need_clarify=True, clarify_question="请澄清"),
        )


class _InvalidEngine:
    async def invoke(self, request: AgentRequest) -> AgentResult:
        return AgentResult(
            agent_id=request.agent_id,
            valid=False,
            degraded=True,
            errors=["invalid"],
        )


@pytest.mark.asyncio
async def test_invalid_agent_output_does_not_persist_asset_but_records_turn() -> None:
    from zhiyin_api.dto.conversation import MessageRequest, TaskEnterRequest
    from zhiyin_kernel.enums import AssetType

    container = _container()
    container.orchestrator._agent_engine = _InvalidEngine()
    user_id = "invalid-output-user"
    session = await container.facade.enter_task(
        user_id, TaskEnterRequest(task_code="verify_direction")
    )
    turn = await container.facade.send_message(
        user_id,
        MessageRequest(
            task_id=session.task_id,
            message="我想验证这个方向适不适合我",
        ),
    )

    assert turn.guide["kind"] == "question"
    assert not await container.asset_service.list_versions(user_id, AssetType.REPORT)
    logs = await container.behavior_service.recent(user_id, event_types=[BehaviorEventType.ANSWER])
    assert len(logs) == 1


class _EmptySearch:
    async def search(self, request):
        return []


@pytest.mark.asyncio
async def test_no_knowledge_hit_exposes_no_unverified_theory_reference() -> None:
    from zhiyin_api.dto.conversation import MessageRequest, TaskEnterRequest

    container = _container()
    container.orchestrator._search = _EmptySearch()
    user_id = "no-knowledge-user"
    session = await container.facade.enter_task(
        user_id, TaskEnterRequest(task_code="verify_direction")
    )
    turn = await container.facade.send_message(
        user_id,
        MessageRequest(
            task_id=session.task_id,
            message="我想验证这个方向适不适合我",
        ),
    )

    assert turn.badge["theory_refs"] == []
    assert all(message.theory_refs == [] for message in turn.messages)


@pytest.mark.asyncio
async def test_handle_message_rejects_another_users_session_before_reading_it() -> None:
    from zhiyin_api.dto.conversation import MessageRequest, TaskEnterRequest

    container = _container()
    session = await container.facade.enter_task(
        "owner-user", TaskEnterRequest(task_code="confused")
    )

    with pytest.raises(PermissionError, match="不属于用户"):
        await container.facade.send_message(
            "other-user",
            MessageRequest(task_id=session.task_id, message="查看别人的会话"),
        )
