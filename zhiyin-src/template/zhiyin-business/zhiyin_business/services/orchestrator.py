"""编排器实现。

落位：`business/services/orchestrator.py` —— 业务编排负责人。
依赖：黑板四件套 Port + `policies/` 规则 + AgentEngine + Registry / 会话 Repository。

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

`policies/` 里已有对应 ABC（含独立的 `AxisAInferencePolicy`），构造参数就是
它们——规则实现与编排实现可以并行交付，各自对着 ABC 验收。
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, ConfigDict

from zhiyin_business.contracts.act import ActOutput
from zhiyin_business.contracts.common import (
    AgentBadge,
    BehaviorEventDraft,
    BehaviorGuide,
    ConversationMessage,
    TheoryRef,
)
from zhiyin_business.contracts.decide import DecideOutput
from zhiyin_business.contracts.diagnose import DiagnoseOutput
from zhiyin_business.events import LOOP_STAGE_CHANGED, LoopStageChangedPayload
from zhiyin_business.policies.axis_a import AxisAInferencePolicy
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
from zhiyin_data_sdk.gateways.ai import KnowledgeGateway, KnowledgeHit
from zhiyin_data_sdk.repositories import RegistryRepository, TaskSessionRepository
from zhiyin_kernel.assets import ActionPlan, DirectionPlan, PlanGap, Report
from zhiyin_kernel.blackboard import AssetVersion, TaskSession
from zhiyin_kernel.enums import (
    AssetType,
    AxisAStage,
    BehaviorEventType,
    LoopStage,
    PathFocus,
    TaskStatus,
)
from zhiyin_orchestration import (
    AgentEngine,
    AgentRequest,
    DomainEvent,
    EventBus,
    StateStore,
)


class _AxisAInferenceResult(BaseModel):
    """模型兜底的最小结构化产出，不属于公开业务契约。"""

    model_config = ConfigDict(extra="forbid")

    stage: AxisAStage
    reason: str = ""


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
        axis_a_policy: AxisAInferencePolicy,
        lead_policy: LeadPolicy,
        handoff_policy: HandoffPolicy,
        agent_engine: AgentEngine,
        knowledge: KnowledgeGateway,
        state_store: StateStore,
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
        self._axis_a_policy = axis_a_policy
        self._lead_policy = lead_policy
        self._handoff_policy = handoff_policy
        self._agent_engine = agent_engine
        self._knowledge = knowledge
        self._state_store = state_store
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

    async def detect_stage(self, user_id: str, task_id: str, intent: IntentType) -> StageDecision:
        blackboard = await self.read_blackboard(user_id, task_id)
        return await self._stage_policy.decide(
            blackboard=blackboard,
            intent=intent,
            message=intent.value,
        )

    async def _detect_stage_for_message(
        self,
        *,
        user_id: str,
        task_id: str,
        intent: IntentType,
        message: str,
    ) -> StageDecision:
        decision = await self._stage_policy.decide(
            blackboard=await self.read_blackboard(user_id, task_id),
            intent=intent,
            message=message,
        )
        return await self._apply_routing_fallback(user_id, task_id, decision)

    async def _apply_routing_fallback(
        self,
        user_id: str,
        task_id: str,
        decision: StageDecision,
    ) -> StageDecision:
        state_key = f"orchestrator:routing-clarify:{user_id}:{task_id or '_'}"
        if not decision.need_clarify and decision.stage is not None:
            self._state_store.delete(state_key)
            return decision

        params = await self._registry.get_policy_params("routing")
        if params is None or params.status != "confirmed":
            raise RuntimeError("routing 规则参数缺失或尚未确认")
        attempts = params.value.get("clarify_attempts")
        fallback_value = params.value.get("fallback_stage")
        if isinstance(attempts, bool) or not isinstance(attempts, int) or attempts < 0:
            raise RuntimeError("routing.clarify_attempts 必须是非负整数")
        try:
            fallback_stage = LoopStage(str(fallback_value))
        except ValueError as exc:
            raise RuntimeError("routing.fallback_stage 不是有效环节") from exc

        current = self._state_store.read(state_key)
        current_attempts = 0
        if current is not None and isinstance(current.value, dict):
            stored_attempts = current.value.get("attempts", 0)
            if isinstance(stored_attempts, int) and not isinstance(stored_attempts, bool):
                current_attempts = max(stored_attempts, 0)
        if current_attempts < attempts:
            self._state_store.write(
                state_key,
                {"attempts": current_attempts + 1},
                expected_version=current.version if current is not None else 0,
            )
            return decision.model_copy(update={"stage": None, "need_clarify": True})

        self._state_store.delete(state_key)
        return StageDecision(
            stage=fallback_stage,
            confidence=0.0,
            need_clarify=False,
            clarify_question=None,
        )

    async def infer_axis_a(self, user_id: str, task_id: str) -> AxisAStage:
        blackboard = await self.read_blackboard(user_id, task_id)
        session = await self._sessions.get(task_id) if task_id else None
        path_focus = (
            session.path_focus if session is not None and session.user_id == user_id else None
        )
        inferred = self._axis_a_policy.infer(
            blackboard=blackboard,
            path_focus=path_focus,
        )
        if inferred is not None:
            return inferred
        return await self._infer_axis_a_with_model(blackboard, path_focus)

    async def _infer_axis_a_with_model(
        self,
        blackboard: BlackboardView,
        path_focus: PathFocus | None,
    ) -> AxisAStage:
        agents = await self._registry.list_agents()
        inference_agent = next(
            (agent for agent in agents if "super_life_stage" in agent.theory_packages),
            None,
        )
        if inference_agent is None:
            return AxisAStage.EXPLORE_SELF
        theory_cards = await self._registry.list_theory_cards(inference_agent.theory_packages)
        result = await self._agent_engine.invoke(
            AgentRequest(
                agent_id=inference_agent.id,
                stage="axis_a_inference",
                blackboard=blackboard.model_dump(mode="json"),
                prompt_vars={
                    "path_focus": path_focus.value if path_focus is not None else None,
                    "theory_context": [card.model_dump(mode="json") for card in theory_cards],
                },
                output_schema=_AxisAInferenceResult.model_json_schema(),
            )
        )
        if not result.valid:
            return AxisAStage.EXPLORE_SELF
        try:
            return _AxisAInferenceResult.model_validate(result.structured).stage
        except ValueError:
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
        lead = await self.select_lead(
            user_id,
            task_id,
            await self.infer_axis_a(user_id, task_id),
            to_stage,
            IntentType.FREE_CHAT,
        )
        return await self._perform_handoff(
            user_id=user_id,
            session=session,
            to_stage=to_stage,
            reason=reason,
            to_agent=lead.lead_agent,
        )

    async def _perform_handoff(
        self,
        *,
        user_id: str,
        session: TaskSession,
        to_stage: LoopStage,
        reason: str,
        to_agent: str,
    ) -> HandoffDecision:
        decision = self._handoff_policy.decide(
            blackboard=await self.read_blackboard(user_id, session.id),
            from_stage=session.loop_stage,
            from_agent=session.lead_agent,
            to_stage=to_stage,
            reason=reason,
            to_agent=to_agent,
        )
        await self._sessions.update_stage(session.id, to_stage, decision.to_agent)
        await self._memories.upsert(
            user_id,
            session.id,
            loop_stage=to_stage,
            lead_agent=decision.to_agent,
        )
        payload = LoopStageChangedPayload(
            user_id=user_id,
            task_id=session.id,
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
                idempotency_key=(
                    f"handoff:{session.id}:{session.loop_stage.value}:{to_stage.value}:"
                    f"{session.lead_agent}:{decision.to_agent}"
                ),
            )
        )
        return decision

    async def handle_message(self, request: TurnRequest) -> TurnResult:
        existing = await self._sessions.get(request.task_id)
        if existing is not None and existing.user_id != request.user_id:
            raise PermissionError(f"会话 {request.task_id} 不属于用户 {request.user_id}")
        intent = await self.detect_intent(request.user_id, request.message)
        decision = await self._detect_stage_for_message(
            user_id=request.user_id,
            task_id=request.task_id,
            intent=intent,
            message=request.message,
        )
        if decision.need_clarify or decision.stage is None:
            if existing is None:
                existing = await self._create_session(
                    request.user_id, request.task_id, LoopStage.COLLECT, intent
                )
            descriptor = await self._registry.get_agent(existing.lead_agent)
            question = decision.clarify_question
            if not question:
                raise RuntimeError("路由策略要求澄清，但未提供澄清文案")
            await self._record_turn(
                user_id=request.user_id,
                session=existing,
                message=request.message,
            )
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
                    ConversationMessage(role="agent", text=question, agent_id=existing.lead_agent)
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
        elif existing.loop_stage is not stage or existing.lead_agent != lead.lead_agent:
            handoff = await self._perform_handoff(
                user_id=request.user_id,
                session=existing,
                to_stage=stage,
                reason=lead.reason,
                to_agent=lead.lead_agent,
            )
            session = await self._sessions.get(existing.id)
        else:
            session = existing
            handoff = None
        if session is None:  # pragma: no cover - Repository 违反契约
            raise RuntimeError("会话创建后无法读取")

        blackboard = await self.read_blackboard(request.user_id, session.id)
        knowledge_hits = await self._load_knowledge_context(
            message=request.message,
            agent_id=session.lead_agent,
            stage=stage,
        )
        contract = STAGE_OUTPUT_CONTRACTS[stage]
        agent_result = await self._agent_engine.invoke(
            AgentRequest(
                agent_id=session.lead_agent,
                stage=stage.value,
                blackboard=blackboard.model_dump(mode="json"),
                prompt_vars={
                    "user_input": request.message,
                    "intent": intent.value,
                    "knowledge_hits": [hit.model_dump(mode="json") for hit in knowledge_hits],
                },
                output_schema=contract.model_json_schema(),
            )
        )
        if not agent_result.valid:
            question = "这轮产出暂时不可用，我们换个方式继续。你最想先解决哪一步？"
            output = None
            guide = BehaviorGuide(kind="question", text=question, question=question)
            messages = [
                ConversationMessage(role="agent", text=question, agent_id=session.lead_agent)
            ]
            theory_refs = []
        else:
            output = contract.model_validate(agent_result.structured)
            if stage in {LoopStage.DIAGNOSE, LoopStage.DECIDE}:
                theory_refs = self._theory_refs_from_hits(knowledge_hits, stage)
                output = output.model_copy(update={"theory_refs": theory_refs})
            else:
                theory_refs = list(getattr(output, "theory_refs", []))
            guide = output.guide
            conclusion = default_conclusion_builder(stage, output)
            messages = (
                [
                    ConversationMessage(
                        role="agent",
                        text=conclusion,
                        agent_id=session.lead_agent,
                        theory_refs=theory_refs,
                    )
                ]
                if conclusion
                else []
            )

        created_versions = await self._persist_output(
            request.user_id,
            stage,
            output,
            knowledge_hits=knowledge_hits,
        )
        await self._record_turn(
            user_id=request.user_id,
            session=session,
            message=request.message,
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

    async def _load_knowledge_context(
        self,
        *,
        message: str,
        agent_id: str,
        stage: LoopStage,
    ) -> list[KnowledgeHit]:
        if stage not in {LoopStage.DIAGNOSE, LoopStage.DECIDE}:
            return []
        descriptor = await self._registry.get_agent(agent_id)
        theory_cards = (
            await self._registry.list_theory_cards(descriptor.theory_packages)
            if descriptor is not None and descriptor.theory_packages
            else []
        )
        query_parts = [message]
        for card in theory_cards:
            query_parts.extend((card.name, card.summary))
        query = " ".join(part.strip() for part in query_parts if part.strip())
        if not query:
            return []
        return await self._knowledge.search(query, top_k=5, namespace="theory")

    @staticmethod
    def _theory_refs_from_hits(hits: list[KnowledgeHit], stage: LoopStage) -> list[TheoryRef]:
        return [
            TheoryRef(
                theory_id=hit.doc_id,
                name=hit.title or hit.doc_id,
                stage=stage.value,
            )
            for hit in hits
        ]

    async def _record_turn(
        self,
        *,
        user_id: str,
        session: TaskSession,
        message: str,
    ) -> None:
        await self._behaviors.log(
            user_id,
            BehaviorEventDraft(
                event_type=BehaviorEventType.ANSWER,
                payload={"task_id": session.id, "stage": session.loop_stage.value},
            ),
        )
        await self._memories.upsert(
            user_id,
            session.id,
            loop_stage=session.loop_stage,
            lead_agent=session.lead_agent,
            summary_delta=message[:200],
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
                    await self.infer_axis_a(user_id, task_id),
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

    async def _persist_output(
        self,
        user_id: str,
        stage: LoopStage,
        output,
        *,
        knowledge_hits: list[KnowledgeHit],
    ) -> list[AssetVersion]:
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
        profile = await self._profiles.get(user_id)
        dependencies = list(dict.fromkeys(field.key for field in profile.fields)) if profile else []

        if stage is LoopStage.DIAGNOSE:
            if not isinstance(output, DiagnoseOutput):
                raise TypeError("诊断环节产出类型不正确")
            report = Report(
                id=f"rpt_{uuid4().hex[:12]}",
                user_id=user_id,
                version=1,
                generated_at=datetime.now(timezone.utc),
                verdict=output.verdict,
                swot=output.swot,
                dimensions=output.dimensions,
                gap_claims=[],
                sources=self._report_sources(output, knowledge_hits),
                methodologies=list(
                    dict.fromkeys(ref.name or ref.theory_id for ref in output.theory_refs)
                ),
            )
            return [
                await self._assets.save_report(
                    user_id,
                    report,
                    depends_on_profile_keys=dependencies,
                    reason=f"{stage.value} 环节产生新资产",
                )
            ]

        if stage is LoopStage.DECIDE:
            if not isinstance(output, DecideOutput):
                raise TypeError("决策环节产出类型不正确")
            report = await self._assets.get_report(user_id)
            plans = [
                DirectionPlan(
                    id=option.option_id,
                    report_id=report.id if report is not None else None,
                    role=option.role,
                    name=option.name,
                    target_desc=option.target_desc,
                    match_score=option.match_score,
                    gaps=[
                        PlanGap(
                            requirement=gap,
                            current_state="",
                            suggestion="",
                        )
                        for gap in option.gaps
                    ],
                    fit_reason=option.fit_reason,
                    main_risk=option.main_risk,
                )
                for option in output.plans
            ]
            return [
                await self._assets.save_direction_plans(
                    user_id,
                    plans,
                    depends_on_profile_keys=dependencies,
                    reason=f"{stage.value} 环节产生新资产",
                )
            ]

        if stage is LoopStage.ACT:
            if not isinstance(output, ActOutput):
                raise TypeError("行动环节产出类型不正确")
            directions = await self._assets.list_direction_plans(user_id)
            selected = next((item for item in directions if item.selected), None)
            plan = ActionPlan(
                id=f"act_{uuid4().hex[:12]}",
                plan_id=selected.id if selected is not None else None,
                phases=output.phases,
                reminders_synced=(
                    bool(output.reminders)
                    and all(item.calendar_synced for item in output.reminders)
                ),
            )
            return [
                await self._assets.save_action_plan(
                    user_id,
                    plan,
                    depends_on_profile_keys=dependencies,
                    reason=f"{stage.value} 环节产生新资产",
                )
            ]
        return []

    @staticmethod
    def _report_sources(
        output: DiagnoseOutput,
        knowledge_hits: list[KnowledgeHit],
    ) -> list[str]:
        candidates: list[str] = []
        for hit in knowledge_hits:
            source = hit.metadata.get("source_url") or hit.metadata.get("source")
            if source:
                candidates.append(str(source))
        candidates.extend(item.source for item in output.facts if item.source)
        candidates.extend(item.source for item in output.evidences if item.source)
        return list(dict.fromkeys(item.strip() for item in candidates if item.strip()))


__all__ = ["DefaultOrchestrator"]
