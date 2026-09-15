"""编排器实现。

落位：`business/services/orchestrator.py` —— 业务编排负责人。
依赖：黑板四件套 Port + `policies/` 四条规则 + AgentEngine + Registry / 会话 Repository。

已落实的第一期决策
------------------
本实现依据《业务口径决策记录-v1.0》落实以下 4 项口径：
1. 轴 A 阶段判定信号（`policies/teaming.py` 的 `LeadPolicy` 输入）；
2. 意图识别 → 环节判定的兜底规则（`policies/routing.py` 的 `StagePolicy`）；
3. 画像置信度算法与缺口表达（`COLLECT` 的交接判据）；
4. 主动干预参数：停滞阈值 / 冷却期 / 打扰上限（位于
   `data/registry/policy_params.json`，`status=confirmed`）。

本类保持"读黑板 → 调规则 → 落库 → 发事件"的装配式编排，
规则本身写在 `policies/`，**本类不得内联任何业务规则**。

`policies/` 里已有对应 ABC（`IntentPolicy` / `StagePolicy` / `LeadPolicy` /
`HandoffPolicy`），构造参数就是它们——规则实现与编排实现可以两个人并行做，
各自对着 ABC 交付。
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from zhiyin_business.contracts.common import (
    AgentBadge,
    AssetUpdateDraft,
    BehaviorEventDraft,
    BehaviorGuide,
    ConversationMessage,
)
from zhiyin_business.events import LOOP_STAGE_CHANGED, LoopStageChangedPayload
from zhiyin_business.policies.handoff import HandoffPolicy
from zhiyin_business.policies.routing import IntentPolicy, StagePolicy
from zhiyin_business.policies.teaming import LeadPolicy
from zhiyin_business.ports.blackboard import (
    AssetService,
    BehaviorService,
    BlackboardView,
    ConversationMemoryService,
    ProfileService,
)
from zhiyin_business.ports.orchestrator import (
    HandoffDecision,
    IntentType,
    LeadDecision,
    Orchestrator,
    StageDecision,
    TurnRequest,
    TurnResult,
)
from zhiyin_business.services.loop import STAGE_OUTPUT_CONTRACTS, default_conclusion_builder
from zhiyin_data_sdk.repositories import RegistryRepository, TaskSessionRepository
from zhiyin_kernel.blackboard import TaskSession
from zhiyin_kernel.enums import (
    AssetType,
    AxisAStage,
    BehaviorEventType,
    LoopStage,
    TaskStatus,
)
from zhiyin_orchestration import AgentEngine, AgentRequest, DomainEvent, EventBus


class DefaultOrchestrator(Orchestrator):
    """编排器默认实现：只做读黑板、调规则、调用 Agent、落库与发事件。"""

    IMPLEMENTATION_STATUS = "wired"

    def __init__(
        self,
        *,
        profiles: ProfileService,
        behaviors: BehaviorService,
        memories: ConversationMemoryService,
        assets: AssetService,
        intent_policy: IntentPolicy,
        stage_policy: StagePolicy,
        lead_policy: LeadPolicy,
        handoff_policy: HandoffPolicy,
        agent_engine: AgentEngine,
        sessions: TaskSessionRepository,
        registry: RegistryRepository,
        event_bus: EventBus,
    ) -> None:
        self._profiles = profiles
        self._behaviors = behaviors
        self._memories = memories
        self._assets = assets
        self._intent_policy = intent_policy
        self._stage_policy = stage_policy
        self._lead_policy = lead_policy
        self._handoff_policy = handoff_policy
        self._agent_engine = agent_engine
        self._sessions = sessions
        self._registry = registry
        self._event_bus = event_bus

    async def read_blackboard(self, user_id: str, task_id: str) -> BlackboardView:
        profile, behaviors, memories, report, directions, actions = await asyncio.gather(
            self._profiles.get(user_id),
            self._behaviors.recent(user_id, limit=50),
            self._memories.list_by_user(user_id),
            self._assets.list_versions(user_id, AssetType.REPORT),
            self._assets.list_versions(user_id, AssetType.DIRECTION_PLAN),
            self._assets.list_versions(user_id, AssetType.ACTION_PLAN),
        )
        current = next((item for item in memories if item.task_id == task_id), None)
        return BlackboardView(
            user_id=user_id,
            task_id=task_id,
            profile=profile,
            recent_behaviors=behaviors,
            memories=memories,
            asset_versions=[*report, *directions, *actions],
            current_stage=current.loop_stage if current is not None else None,
        )

    async def detect_intent(self, user_id: str, message: str) -> IntentType:
        blackboard = await self.read_blackboard(user_id, "")
        return await self._intent_policy.classify(message=message, blackboard=blackboard)

    async def detect_stage(
        self, user_id: str, task_id: str, intent: IntentType
    ) -> StageDecision:
        blackboard = await self.read_blackboard(user_id, task_id)
        return await self._stage_policy.decide(
            blackboard=blackboard,
            intent=intent,
            message=intent.value,
        )

    async def infer_axis_a(self, user_id: str, task_id: str) -> AxisAStage:
        blackboard = await self.read_blackboard(user_id, task_id)
        event_types = {item.event_type for item in blackboard.recent_behaviors}
        if BehaviorEventType.REVIEW in event_types:
            return AxisAStage.ADAPT
        if BehaviorEventType.TASK_DONE in event_types:
            return AxisAStage.SPRINT_ACTION
        if blackboard.profile is not None and any(
            field.key == "target_direction" for field in blackboard.profile.fields
        ):
            return AxisAStage.VERIFY_DIRECTION
        return AxisAStage.EXPLORE_SELF

    async def select_lead(
        self,
        user_id: str,
        task_id: str,
        axis_a: AxisAStage,
        stage: LoopStage,
        intent: IntentType,
    ) -> LeadDecision:
        return await self._lead_policy.select(
            blackboard=await self.read_blackboard(user_id, task_id),
            axis_a=axis_a,
            stage=stage,
            intent=intent,
        )

    async def handoff(
        self, user_id: str, task_id: str, to_stage: LoopStage, reason: str
    ) -> HandoffDecision:
        session = await self._sessions.get(task_id)
        if session is None or session.user_id != user_id:
            raise LookupError(f"任务会话不存在：{task_id}")
        blackboard = await self.read_blackboard(user_id, task_id)
        lead = await self.select_lead(
            user_id,
            task_id,
            await self.infer_axis_a(user_id, task_id),
            to_stage,
            IntentType.FREE_CHAT,
        )
        decision = self._handoff_policy.decide(
            blackboard=blackboard,
            from_stage=session.loop_stage,
            from_agent=session.lead_agent,
            to_stage=to_stage,
            reason=reason,
            to_agent=lead.lead_agent,
        )
        await self._sessions.update_stage(task_id, to_stage, decision.to_agent)
        await self._memories.upsert(
            user_id,
            task_id,
            loop_stage=to_stage,
            lead_agent=decision.to_agent,
        )
        payload = LoopStageChangedPayload(
            user_id=user_id,
            task_id=task_id,
            from_stage=session.loop_stage.value,
            to_stage=to_stage.value,
            from_agent=session.lead_agent,
            to_agent=decision.to_agent,
            reason=reason,
        )
        await self._event_bus.publish(
            DomainEvent(
                event_id=f"evt_{uuid4().hex}",
                event_type=LOOP_STAGE_CHANGED,
                occurred_at=datetime.now(timezone.utc),
                payload=payload.model_dump(mode="json"),
                idempotency_key=f"handoff:{task_id}:{session.loop_stage.value}:{to_stage.value}",
            )
        )
        return decision

    async def handle_message(self, request: TurnRequest) -> TurnResult:
        intent = await self.detect_intent(request.user_id, request.message)
        decision = await self.detect_stage(request.user_id, request.task_id, intent)
        existing = await self._sessions.get(request.task_id)
        if decision.need_clarify or decision.stage is None:
            if existing is None:
                existing = await self._create_session(
                    request.user_id, request.task_id, LoopStage.COLLECT, intent
                )
            descriptor = await self._registry.get_agent(existing.lead_agent)
            question = decision.clarify_question or "你希望先从哪件事开始？"
            return TurnResult(
                task_id=existing.id,
                session=existing,
                stage=existing.loop_stage,
                badge=AgentBadge(
                    agent_id=existing.lead_agent,
                    name=descriptor.name if descriptor else existing.lead_agent,
                    role_summary=descriptor.role_summary if descriptor else "",
                ),
                messages=[
                    ConversationMessage(
                        role="agent", text=question, agent_id=existing.lead_agent
                    )
                ],
                guide=BehaviorGuide(kind="question", text=question, question=question),
            )

        stage = decision.stage
        lead = await self.select_lead(
            request.user_id,
            request.task_id,
            await self.infer_axis_a(request.user_id, request.task_id),
            stage,
            intent,
        )
        if existing is None:
            session = await self._create_session(
                request.user_id, request.task_id, stage, intent, lead.lead_agent
            )
            handoff = None
        elif existing.user_id != request.user_id:
            raise PermissionError(f"会话 {request.task_id} 不属于用户 {request.user_id}")
        elif existing.loop_stage is not stage or existing.lead_agent != lead.lead_agent:
            handoff = await self.handoff(
                request.user_id, existing.id, stage, lead.reason
            )
            session = await self._sessions.get(existing.id)
        else:
            session = existing
            handoff = None
        if session is None:  # pragma: no cover - Repository 违反契约
            raise RuntimeError("会话创建后无法读取")

        blackboard = await self.read_blackboard(request.user_id, session.id)
        contract = STAGE_OUTPUT_CONTRACTS[stage]
        agent_result = await self._agent_engine.invoke(
            AgentRequest(
                agent_id=session.lead_agent,
                stage=stage.value,
                blackboard=blackboard.model_dump(mode="json"),
                prompt_vars={"user_input": request.message, "intent": intent.value},
                output_schema=contract.model_json_schema(),
            )
        )
        if not agent_result.valid:
            question = "这轮产出暂时不可用，我们换个方式继续。你最想先解决哪一步？"
            output = None
            guide = BehaviorGuide(kind="question", text=question, question=question)
            messages = [
                ConversationMessage(
                    role="agent", text=question, agent_id=session.lead_agent
                )
            ]
            theory_refs = []
        else:
            output = contract.model_validate(agent_result.structured)
            guide = output.guide
            conclusion = default_conclusion_builder(stage, output)
            theory_refs = list(getattr(output, "theory_refs", []))
            messages = [
                ConversationMessage(
                    role="agent",
                    text=conclusion,
                    agent_id=session.lead_agent,
                    theory_refs=theory_refs,
                )
            ] if conclusion else []

        created_versions = await self._persist_output(
            request.user_id, stage, output
        )
        await self._behaviors.log(
            request.user_id,
            BehaviorEventDraft(
                event_type=BehaviorEventType.ANSWER,
                payload={"task_id": session.id, "stage": stage.value},
            ),
        )
        await self._memories.upsert(
            request.user_id,
            session.id,
            loop_stage=stage,
            lead_agent=session.lead_agent,
            summary_delta=request.message[:200],
        )
        descriptor = await self._registry.get_agent(session.lead_agent)
        return TurnResult(
            task_id=session.id,
            session=session,
            stage=stage,
            badge=AgentBadge(
                agent_id=session.lead_agent,
                name=descriptor.name if descriptor else session.lead_agent,
                role_summary=descriptor.role_summary if descriptor else "",
                theory_refs=theory_refs,
            ),
            messages=messages,
            disclosure=(handoff.disclosure if handoff else getattr(output, "disclosure", None)),
            guide=guide,
            asset_versions=created_versions,
        )

    async def _create_session(
        self,
        user_id: str,
        task_id: str,
        stage: LoopStage,
        intent: IntentType,
        lead_agent: str | None = None,
    ) -> TaskSession:
        if lead_agent is None:
            lead_agent = (
                await self.select_lead(
                    user_id,
                    task_id,
                    AxisAStage.EXPLORE_SELF,
                    stage,
                    intent,
                )
            ).lead_agent
        now = datetime.now(timezone.utc)
        return await self._sessions.create(
            TaskSession(
                id=task_id or f"tsk_{uuid4().hex[:12]}",
                user_id=user_id,
                task_code=intent.value,
                task_name=intent.value,
                loop_stage=stage,
                lead_agent=lead_agent,
                status=TaskStatus.ACTIVE,
                created_at=now,
                updated_at=now,
            )
        )

    async def _persist_output(self, user_id: str, stage: LoopStage, output) -> list:
        if output is None:
            return []
        if stage is LoopStage.COLLECT:
            for update in output.field_updates:
                await self._profiles.update_field(
                    user_id,
                    update.key,
                    update.value,
                    confidence=update.confidence,
                    source=update.source.value,
                    evidence=update.evidence,
                )
            await self._profiles.replace_gaps(user_id, output.remaining_gaps)
            return []
        asset_type = {
            LoopStage.DIAGNOSE: AssetType.REPORT,
            LoopStage.DECIDE: AssetType.DIRECTION_PLAN,
            LoopStage.ACT: AssetType.ACTION_PLAN,
        }.get(stage)
        if asset_type is None:
            return []
        profile = await self._profiles.get(user_id)
        dependencies = [field.key for field in profile.fields] if profile else []
        # TODO(第一期未闭合): OPEN-1 —— 这里只落"版本元数据"，把 output 里的正文
        # （DiagnoseOutput.verdict/swot/dimensions、DecideOutput.plans、ActOutput.phases）
        # 丢掉了。因此资产有版本号、但没有正文：报告页 404、工作台 ②③④ 显示"尚未生成…"。
        # 接线点就是下面这次调用：应改为 assets.save_report / save_direction_plans /
        # save_action_plan（这三个 API 已实现且已通过契约测试）。
        # 归属与退出判据：docs/数据全链路/职引-第一期未闭合项与Mock标注清单.md（OPEN-1）。
        return [
            await self._assets.save_version(
                user_id,
                AssetUpdateDraft(
                    asset_type=asset_type,
                    depends_on_profile_keys=dependencies,
                    reason=f"{stage.value} 环节产生新资产",
                ),
            )
        ]


__all__ = ["DefaultOrchestrator"]
