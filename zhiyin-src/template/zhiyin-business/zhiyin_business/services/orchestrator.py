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
from zhiyin_business.policies.retrieval import RetrievalPlanningPolicy
from zhiyin_business.ports.blackboard import (
    AssetService,
    BehaviorService,
    BlackboardView,
    ConversationMemoryService,
    ProfileService,
)
from zhiyin_business.ports.loop import LoopCoordinator
from zhiyin_business.ports.orchestrator import (
    HandoffDecision,
    IntentType,
    LeadDecision,
    Orchestrator,
    StageDecision,
    TurnRequest,
    TurnResult,
)
from zhiyin_business.services.loop import STAGE_OUTPUT_CONTRACTS
from zhiyin_data_sdk.gateways.ai import SearchGateway
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
from zhiyin_kernel.retrieval import EvidencePacket, RetrievalEvidence
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


def _theory_card_id(hit: RetrievalEvidence) -> str:
    """取**理论卡 id**，而不是检索证据的地址（D11）。

    `TheoryRef.theory_id` 的契约是"理论卡 id，指向 theory_card"；而 `evidence_id`
    在 D11 之后是 `namespace:id` 形式的**检索地址**。两者不是一回事，早期实现把
    `theory_id=hit.evidence_id` 直接赋值只是巧合能跑——一旦证据 id 统一加上
    namespace 前缀，卡片引用就会变成 `theory:clover` 这种"卡片不认得的 id"。

    因此这里显式取卡片 id：优先用通道回传的原始 `id`（本地/权威通道都会带在
    metadata 里），否则退回去掉 namespace 前缀的证据 id（PAMI 通道没有原始 id，
    此时只能降级，且它的 id 本就不是卡片 id——这一点在 PAMI 适配器里已写明）。
    """
    raw = hit.metadata.get("id")
    if raw:
        return str(raw)
    prefix = f"{hit.namespace.value}:"
    return hit.evidence_id.removeprefix(prefix)


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
        loop: LoopCoordinator,
        search: SearchGateway,
        retrieval_policy: RetrievalPlanningPolicy,
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
        # 环节执行与交接口径归 LoopCoordinator（五环节状态机 Port）；
        # 本类只负责读黑板、调规则、落库与发事件。
        self._loop = loop
        self._search = search
        self._retrieval_policy = retrieval_policy
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
        # 告知文案在这里组装，而不是在策略里：策略只回答"要不要告知、为什么"，
        # 它既拿不到环节中文名也拿不到主理展示名。让它拼文案的后果是
        # 用户会看到「接下来进入 diagnose 环节」这种漏出枚举值的句子。
        # 文案一律从动态资源取（AGENTS.md §8：展示文案不得硬编码）。
        if decision.disclosure is not None:
            decision = decision.model_copy(
                update={
                    "disclosure": decision.disclosure.model_copy(
                        update={"text": await self._handoff_disclosure_text(decision)}
                    )
                }
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

    async def _handoff_disclosure_text(self, decision: HandoffDecision) -> str:
        """换主理 / 换环节的显式告知文案（FR-ORCH-003）。

        产品要求这一行讲清"谁接手、依据什么、为什么"：
        - 主理展示名取自动态资源 `agents.json`；
        - 环节中文名取自文案包 `copies.json` 的 `stage.<code>.label`；
        - 取不到时用不含枚举值的兜底说法，**绝不把 `diagnose` 这类内部取值写给用户**。
        """
        descriptor = await self._registry.get_agent(decision.to_agent)
        to_name = descriptor.name if descriptor is not None else "新的主理"
        label = ""
        try:
            bundle = await self._registry.get_copy_bundle()
            label = str(bundle.get(f"stage.{decision.to_stage.value}.label", ""))
        except NotImplementedError:  # 动态资源不可用时回落到不含环节名的说法
            label = ""
        where = f"进入{label}环节" if label else "进入下一个环节"
        return f"接下来{where}，由「{to_name}」接手继续帮助你：{decision.reason}"

    async def _placeholder_notice(self) -> str:
        """占位模型的应答提示；文案取自动态资源（AGENTS.md §8）。

        取不到时返回空串——宁可少一行提示，也不在这里硬编码一句用户可见的话。
        """
        try:
            bundle = await self._registry.get_copy_bundle()
        except NotImplementedError:
            return ""
        return str(bundle.get("notice.placeholder_output", "")).strip()

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

        # 环节执行者自己通过 blackboard_loader 读同一份黑板，这里不再重复读取。
        evidence_packet = await self._load_retrieval_context(
            message=request.message,
            agent_id=session.lead_agent,
            stage=stage,
            intent=intent.value,
            user_id=request.user_id,
        )
        contract = STAGE_OUTPUT_CONTRACTS[stage]
        # ②③ 的理论依据必须来自真实检索命中，不能采信模型自由生成的名字；
        # 算好后经 scratch 交给环节执行者，由它生成徽章与最短结论。
        evidence_theory_refs = (
            self._theory_refs_from_hits(evidence_packet.evidences, stage)
            if stage in {LoopStage.DIAGNOSE, LoopStage.DECIDE}
            else []
        )
        context = await self._loop.resume(request.user_id, session.id)
        scratch: dict[str, object] = {
            "intent": intent.value,
            "evidence_packet": evidence_packet.model_dump(mode="json"),
        }
        if stage in {LoopStage.DIAGNOSE, LoopStage.DECIDE}:
            # 只有这两环节的理论依据需要"以证据为准、没有命中就必须为空"，
            # 所以只在此时下发该键；①④⑤ 仍用产出里的引用。
            scratch["theory_refs"] = [
                ref.model_dump(mode="json") for ref in evidence_theory_refs
            ]
        context = context.model_copy(update={"scratch": scratch})
        loop_result = await self._loop.run_stage(context, request.message)

        if "degraded" in loop_result.output:
            # 环节产出不合法或模型不可用：不落库、不发资产事件，只回一句兜底引导。
            output = None
            guide = loop_result.guide
            messages = (
                [ConversationMessage(role="agent", text=loop_result.guide.text, agent_id=session.lead_agent)]
                if loop_result.guide.text
                else []
            )
            theory_refs = []
        else:
            output = contract.model_validate(loop_result.output)
            if stage in {LoopStage.DIAGNOSE, LoopStage.DECIDE}:
                theory_refs = evidence_theory_refs
                output = output.model_copy(update={"theory_refs": theory_refs})
            else:
                theory_refs = list(getattr(output, "theory_refs", []))
            guide = loop_result.guide
            messages = list(loop_result.messages)

        if loop_result.model_degraded:
            # 模型自述降级（例如本地占位实现）：产出**通过了契约校验**，所以它既不会
            # 走上面的降级分支、也不会被任何门禁拦下，但它并不是真实模型生成的结论。
            # 此前这个标记在成功路径上被直接丢弃，于是"看起来正常的演示产出"会被当成
            # 诊断结论——这正是待决问题 D1 要堵的坑。现在显式在应答里说明一次。
            notice = await self._placeholder_notice()
            if notice:
                if messages:
                    messages[-1] = messages[-1].model_copy(
                        update={"text": f"{messages[-1].text}\n{notice}"}
                    )
                else:
                    messages = [
                        ConversationMessage(
                            role="agent", text=notice, agent_id=session.lead_agent
                        )
                    ]

        # 交接口径：环节执行者按产出判定"本轮结束时是否需要交接"
        # （① 只有 ready_to_handoff=True 才交接，⑤ 按 next_handoff_stage 再入环）。
        # 交接由编排器统一落库并发 loop_stage_changed，前端据 disclosure 显示告知行。
        # 注意：路由已交接时 handoff 已有值，这里只在产出signal更强时覆盖它。
        if loop_result.next_stage is not None and loop_result.next_stage is not stage:
            handoff = await self.handoff(
                request.user_id,
                session.id,
                loop_result.next_stage,
                loop_result.next_stage_reason or "环节产出判定需要交接",
            )
            refreshed = await self._sessions.get(session.id)
            if refreshed is not None:
                session = refreshed

        created_versions = await self._persist_output(
            request.user_id,
            stage,
            output,
            evidence_packet=evidence_packet,
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
            disclosure=(handoff.disclosure if handoff else getattr(output, "disclosure", None) if output else None),
            guide=guide,
            asset_versions=created_versions,
        )

    async def _load_retrieval_context(
        self,
        *,
        message: str,
        agent_id: str,
        stage: LoopStage,
        intent: str,
        user_id: str,
    ) -> EvidencePacket:
        plan = self._retrieval_policy.plan(
            stage=stage,
            intent=intent,
            message=message,
            user_id=user_id,
        )
        if not plan.required:
            return EvidencePacket(stage=stage, question=message)
        descriptor = await self._registry.get_agent(agent_id)
        theory_cards = (
            await self._registry.list_theory_cards(descriptor.theory_packages)
            if descriptor is not None and descriptor.theory_packages
            else []
        )
        query_parts = [message]
        for card in theory_cards:
            query_parts.extend((card.name, card.summary))
        theory_query = " ".join(part.strip() for part in query_parts if part.strip())
        queries = [
            item.model_copy(update={"query": theory_query})
            if item.namespace.value == "theory" and theory_query
            else item
            for item in plan.queries
        ]
        results = await asyncio.gather(
            *(self._search.search(item) for item in queries),
            return_exceptions=True,
        )
        evidences: list[RetrievalEvidence] = []
        degraded: list[str] = []
        for query, result in zip(queries, results, strict=True):
            if isinstance(result, BaseException):
                degraded.append(query.namespace.value)
                continue
            evidences.extend(result)
        deduplicated: dict[str, RetrievalEvidence] = {}
        for evidence in sorted(
            evidences, key=lambda item: (-item.score, item.evidence_id)
        ):
            deduplicated.setdefault(evidence.evidence_id, evidence)
        selected: list[RetrievalEvidence] = []
        source_counts: dict[str, int] = {}
        for evidence in deduplicated.values():
            source_key = evidence.source_id or evidence.evidence_id
            if source_counts.get(source_key, 0) >= 3:
                continue
            selected.append(evidence)
            source_counts[source_key] = source_counts.get(source_key, 0) + 1
            if len(selected) == 20:
                break
        channels = sorted(
            {
                channel
                for evidence in selected
                for channel in evidence.metadata.get("retrieval", {})
                .get("ranks", {})
                .keys()
            }
        )
        return EvidencePacket(
            stage=stage,
            question=message,
            evidences=selected,
            channels=channels or (["keyword"] if selected else []),
            degraded_channels=degraded,
            model_version=str(
                getattr(getattr(self._search, "_embedding", None), "model_id", "")
            ),
        )

    @staticmethod
    def _theory_refs_from_hits(
        hits: list[RetrievalEvidence], stage: LoopStage
    ) -> list[TheoryRef]:
        return [
            TheoryRef(
                theory_id=_theory_card_id(hit),
                name=hit.title or hit.source_id or hit.evidence_id,
                stage=stage.value,
            )
            for hit in hits
            if hit.namespace.value == "theory"
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
        evidence_packet: EvidencePacket,
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
                sources=self._report_sources(output, evidence_packet.evidences),
                source_versions=self._report_source_versions(evidence_packet.evidences),
                methodologies=list(
                    dict.fromkeys(ref.name or ref.theory_id for ref in output.theory_refs)
                ),
                # 把**生成这一版时的画像**冻结进报告（D2）。报告是版本化只读资产，
                # 而画像是活状态；不冻结的话，报告页要么显示不了画像，要么显示的
                # 是与本版本对不上的当前画像。此处 profile 正是本次诊断所用的那一份。
                profile_snapshot=list(profile.fields) if profile else [],
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
        knowledge_hits: list[RetrievalEvidence],
    ) -> list[str]:
        candidates: list[str] = []
        allowed: set[str] = set()
        for hit in knowledge_hits:
            for source in (
                hit.source_url,
                hit.source_id,
                hit.evidence_id,
                hit.metadata.get("source_url"),
                hit.metadata.get("source"),
            ):
                if source:
                    allowed.add(str(source).strip())
            canonical = hit.source_url or hit.source_id or hit.evidence_id
            if canonical:
                candidates.append(str(canonical))
        # 模型只能引用证据包中真实存在的来源；任意生成的 URL/来源名不会进入资产。
        candidates.extend(
            item.source for item in output.facts if item.source and item.source in allowed
        )
        candidates.extend(
            item.source
            for item in output.evidences
            if item.source and item.source in allowed
        )
        return list(dict.fromkeys(item.strip() for item in candidates if item.strip()))

    @staticmethod
    def _report_source_versions(
        knowledge_hits: list[RetrievalEvidence],
    ) -> dict[str, int]:
        """来源 → 版本号，供最终资产回答"这条结论依据的是哪一版资料"（D7 ⑥）。

        为什么需要它：`Report.sources` 只记来源字符串，而权威文档的唯一键是
        `(namespace, source_id, version)`——没有版本就指不到具体那一版，
        "可追溯"只做到一半。这里把证据里的版本一并记进资产。

        键的取法与 `_report_sources` **完全一致**（`source_url or source_id or evidence_id`），
        否则两个字段对不上，反而更难查。同一来源出现在多版证据里时取**最大版本**：
        报告依据的是它当时看到的最新一版。
        """
        versions: dict[str, int] = {}
        for hit in knowledge_hits:
            canonical = hit.source_url or hit.source_id or hit.evidence_id
            if not canonical:
                continue
            key = str(canonical).strip()
            version = max(int(hit.version or 1), 1)
            versions[key] = max(versions.get(key, 0), version)
        return versions


__all__ = ["DefaultOrchestrator"]
