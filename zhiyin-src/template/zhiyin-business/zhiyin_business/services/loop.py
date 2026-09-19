"""五环节微循环的参考实现：由编排层 AgentEngine 驱动。

对应《分层详细设计》§3.2 的单轮回复骨架与《第一期技术架构文档》§5 的调用链：

    读黑板 → 环节判定 → 选主理 → 理论链产出 → 行为引导收尾

职责边界（与 `ports/loop.py` 的契约一致）：
- 本类只负责「调 AgentEngine 拿产出 → 用本环节契约校验 → 组装 LoopResult」；
- 落库（行为日志 / 画像 / 资产）与事件发布由调用方 Orchestrator 统一完成，
  以保证黑板写入的一致性，避免环节实现各写一半。

IO 边界（全仓统一口径）
-----------------------
只要触碰 Repository / Port，方法一律是 `async`：`start` / `resume` / `advance` /
`run_stage` 都不例外。纯内存的辅助函数（如 `next_stage_after`）保持同步。
这样第一期的心内存实现与第二期的 MySQL / 网络 IO 都是同一套调用形状，
换实现时调用方一行不用改。

为什么这是 reference implementation 而不是最终实现
-------------------------------------------------
《第一期技术架构文档》§4.5.1 把 LoopCoordinator 划给「业务编排负责人」。
本实现的存在意义有两个：一是把 business → orchestration 的依赖真正打通
（此前全仓没有任何代码引用编排层），二是给端到端链路一个可运行的起点。
提示词模板、理论链选择、置信度阈值等业务细节由各业务线在本类基础上扩展，
**不要另起一套 LoopCoordinator**。
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Mapping, Optional, Sequence
from uuid import uuid4

from pydantic import BaseModel

from zhiyin_orchestration import AgentEngine, AgentRequest

from zhiyin_business.contracts import (
    ActOutput,
    CollectOutput,
    DecideOutput,
    DiagnoseOutput,
    ReviewOutput,
)
from zhiyin_business.contracts.common import (
    AgentBadge,
    BehaviorGuide,
    ConversationMessage,
)
from zhiyin_business.ports.blackboard import BlackboardView
from zhiyin_business.ports.loop import (
    EntrySource,
    LoopContext,
    LoopCoordinator,
    LoopEntry,
    LoopResult,
)
from zhiyin_kernel.blackboard import TaskSession
from zhiyin_kernel.enums import LoopStage, TaskStatus
from zhiyin_data_sdk.repositories import RegistryRepository, TaskSessionRepository

STAGE_OUTPUT_CONTRACTS: dict[LoopStage, type[BaseModel]] = {
    LoopStage.COLLECT: CollectOutput,
    LoopStage.DIAGNOSE: DiagnoseOutput,
    LoopStage.DECIDE: DecideOutput,
    LoopStage.ACT: ActOutput,
    LoopStage.REVIEW: ReviewOutput,
}
"""环节 → 产出契约。业务层持有模型、编排层只拿 JSON Schema，这是 R-ORC-001 的落地方式。"""

STAGE_SEQUENCE: tuple[LoopStage, ...] = (
    LoopStage.COLLECT,
    LoopStage.DIAGNOSE,
    LoopStage.DECIDE,
    LoopStage.ACT,
    LoopStage.REVIEW,
)
"""① → ⑤ 的默认推进顺序，用于 next_stage 推断。"""

_CONCLUSION_PATHS: dict[LoopStage, tuple[str, ...]] = {
    LoopStage.DIAGNOSE: ("verdict.summary",),
}
"""「最短结论」的取字段径。

其余环节的结论文案由各环节提示词模板产出，第一期回落到行为引导文案；
业务线可通过 `conclusion_builder` 覆盖，不需要改本类。
"""


def _dig(obj: Any, path: str) -> Any:
    current = obj
    for part in path.split("."):
        current = getattr(current, part, None)
        if current is None:
            return None
    return current


def default_conclusion_builder(stage: LoopStage, output: BaseModel) -> str:
    """第一期参考口径：优先取结论字段，取不到就用行为引导文案。"""
    for path in _CONCLUSION_PATHS.get(stage, ()):
        value = _dig(output, path)
        if isinstance(value, str) and value:
            return value
    guide = getattr(output, "guide", None)
    text = getattr(guide, "text", "")
    return text if isinstance(text, str) else ""


def next_stage_after(stage: LoopStage) -> Optional[LoopStage]:
    """默认下一环节；⑤ 复盘回到环首由业务规则决定，这里返回 None。"""
    try:
        index = STAGE_SEQUENCE.index(stage)
    except ValueError:
        return None
    if index + 1 >= len(STAGE_SEQUENCE):
        return None
    return STAGE_SEQUENCE[index + 1]


STAGE_LABELS: dict[LoopStage, str] = {
    LoopStage.COLLECT: "① 采集建模",
    LoopStage.DIAGNOSE: "② 诊断匹配",
    LoopStage.DECIDE: "③ 决策",
    LoopStage.ACT: "④ 行动",
    LoopStage.REVIEW: "⑤ 复盘校准",
}
"""环节中文标签，仅用于模型指令中的环节自述，不作为前端展示文案。"""

_STAGE_DUTIES: dict[LoopStage, str] = {
    LoopStage.COLLECT: (
        "从用户本轮表述中抽取**已经明确表达**的画像信息，只补事实、不下判断；"
        "guide 一次只问一个最关键的缺口问题。"
    ),
    LoopStage.DIAGNOSE: (
        "基于画像字段与检索证据给出诊断结论。"
        "每条结论都要能对应到画像字段或检索证据；没有证据就写明缺少依据，不得编造外部事实。"
    ),
    LoopStage.DECIDE: (
        "基于诊断结论给出可撤回的方向方案候选（主攻 / 平行 / 保底各一档）。"
        "不得替用户选定方向——一旦把某个候选标成已选，用户就被系统代做了决定。"
    ),
    LoopStage.ACT: (
        "把已选方向拆成带时间点的行动计划与可勾选任务。"
        "只做拆解，不评判方向对错。"
    ),
    LoopStage.REVIEW: (
        "基于真实行为日志与已完成资产做复盘归因，给出下一步校准建议。"
        "纯浏览、登录或页面停留不算有效行动。"
    ),
}


def build_stage_instruction(
    stage: LoopStage,
    *,
    agent_name: str = "",
    role_summary: str = "",
    not_to_do: Sequence[str] = (),
    key_fields: Sequence[str] = (),
    coverage_threshold: Optional[float] = None,
    confidence_threshold: Optional[float] = None,
    gap_confidence_floor: Optional[float] = None,
) -> str:
    """组装某一环节发给模型的**任务指令**。

    存在理由：`ContractAgentEngine` 只把 `prompt_vars` 与黑板序列化成 JSON 交给模型，
    本身不含任何任务语义（R-ORC-001）。如果业务层不给出指令，模型只拿到一堆裸 JSON
    和一份输出 Schema，只能自行猜测该抽什么，实测会产出自由命名的画像字段，
    使六个关键字段永远覆盖不到、采集环节无法收口。

    - 环节职责取自本模块 `_STAGE_DUTIES`（第一期参考口径）；
    - 关键字段清单与阈值**必须**由调用方从 `policy_params.profile_collection` 传入，
      本函数不内建任何字段名或阈值，避免与决策 5 口径漂移。
    """
    if stage not in _STAGE_DUTIES:
        raise ValueError(f"未知环节：{stage!r}")

    lines: list[str] = []
    label = STAGE_LABELS[stage]
    if agent_name:
        lines.append(f"你是本环节（{label}）的主理：{agent_name}。")
    else:
        lines.append(f"你是本环节（{label}）的主理。")
    if role_summary:
        lines.append(f"你的职责：{role_summary}")
    if not_to_do:
        lines.append("你明确不做：" + "；".join(str(item) for item in not_to_do) + "。")

    lines.append("")
    lines.append("【本轮任务】")
    lines.append(_STAGE_DUTIES[stage])

    if stage is LoopStage.COLLECT:
        lines.append("")
        lines.append("【画像字段口径】")
        if key_fields:
            lines.append(
                "field_updates[].key 必须从下列关键字段中取值，不要自造字段名："
                + "、".join(key_fields)
                + "。"
            )
            lines.append(
                "每个关键字段：用户已经明确表达 → 写进 field_updates（confidence 反映把握程度，"
                "evidence 放用户原话）；用户没有表达 → 写进 remaining_gaps，不要凭空填值。"
            )
        if coverage_threshold is not None and confidence_threshold is not None:
            lines.append(
                f"只有关键字段覆盖率达到 {coverage_threshold} 且整体置信度不低于 "
                f"{confidence_threshold} 时，才把 ready_to_handoff 置为 true；"
                "否则保持 false 并继续追问。"
            )
        if gap_confidence_floor is not None:
            lines.append(
                f"置信度低于 {gap_confidence_floor} 的关键字段视为缺口，应出现在 remaining_gaps 中。"
            )
        lines.append("confidence_overall 反映当前整体画像置信度，必须如实填写。")

    lines.append("")
    lines.append(
        "【输出要求】只输出一个符合给定 JSON Schema 的 JSON 对象；"
        "不要输出 Markdown 代码块、解释或多余文字。"
        "所有文本使用简体中文。没有依据的内容不要编造。"
    )
    return "\n".join(lines)


class AgentDrivenLoopCoordinator(LoopCoordinator):
    """由 AgentEngine 驱动的五环节状态机。

    构造参数：
    - `agent_engine`：编排层智能体引擎（契约校验在引擎内完成）。
    - `sessions`：任务会话 Repository，可拆可续的持久化载体。
    - `registry`：动态资源 Repository，用于读主理展示名与产出契约。
    - `blackboard_loader`：黑板读取回调（异步），由黑板服务提供；不注入时使用
      空黑板，便于本类独立测试。接黑板服务后，"前序资产自动继承"才真正成立。
    - `conclusion_builder`：环节结论文案构造器，见 `default_conclusion_builder`。
    - `degraded_guide_text`：产出不合法时的兜底引导文案。第一期默认空串，
      接入动态资源后应从 `app_copy` / `notify_template` 读取，禁止在代码里写死文案。
    """

    def __init__(
        self,
        agent_engine: AgentEngine,
        sessions: TaskSessionRepository,
        registry: RegistryRepository,
        *,
        blackboard_loader: Optional[
            Callable[[str, Optional[str]], Awaitable[BlackboardView]]
        ] = None,
        conclusion_builder: Callable[[LoopStage, BaseModel], str] = default_conclusion_builder,
        contracts: Optional[Mapping[LoopStage, type[BaseModel]]] = None,
        degraded_guide_text: str = "",
    ) -> None:
        self._agent = agent_engine
        self._sessions = sessions
        self._registry = registry
        self._blackboard_loader = blackboard_loader
        self._conclusion_builder = conclusion_builder
        self._contracts: dict[LoopStage, type[BaseModel]] = dict(
            contracts or STAGE_OUTPUT_CONTRACTS
        )
        self._degraded_guide_text = degraded_guide_text

    # ------------------------------------------------------------------
    # LoopCoordinator
    # ------------------------------------------------------------------

    async def start(self, entry: LoopEntry) -> LoopContext:
        """从任意环节开始一次微循环，前序资产自动继承（R-BIZ-004 / R-BIZ-005）。"""
        session = await self._sessions.find_active(entry.user_id, entry.task_code)
        if session is None:
            session = await self._sessions.create(
                TaskSession(
                    id=f"tsk_{uuid4().hex[:12]}",
                    user_id=entry.user_id,
                    task_code=entry.task_code,
                    task_name=entry.task_code,
                    loop_stage=entry.stage,
                    lead_agent=entry.lead_agent,
                    status=TaskStatus.ACTIVE,
                    created_at=_utcnow(),
                    updated_at=_utcnow(),
                )
            )
        elif session.loop_stage != entry.stage or session.lead_agent != entry.lead_agent:
            # 用户显式指定了入口环节 / 主理，以本次进入为准（可拆可续不重跑前序）。
            session = await self._sessions.update_stage(
                session.id, entry.stage, entry.lead_agent
            )
        return await self._build_context(session, entry.source)

    async def resume(self, user_id: str, task_id: str) -> LoopContext:
        """续接历史会话，沿用持久化的环节进度（FR-ORCH-005）。"""
        session = await self._sessions.get(task_id)
        if session is None:
            raise LookupError(f"任务会话不存在：{task_id}")
        if session.user_id != user_id:
            raise PermissionError(f"会话 {task_id} 不属于用户 {user_id}")
        return await self._build_context(session, EntrySource.RESUME)

    async def run_stage(self, context: LoopContext, user_input: str) -> LoopResult:
        """执行当前环节的一轮。"""
        contract = self._contracts[context.stage]
        result = await self._agent.invoke(
            AgentRequest(
                agent_id=context.lead_agent,
                stage=context.stage.value,
                blackboard=context.blackboard.model_dump(mode="json"),
                prompt_vars={
                    "user_input": user_input,
                    "task_code": context.session.task_code,
                    "turn_index": context.turn_index,
                    "inherited_assets": [
                        asset.model_dump(mode="json") for asset in context.inherited_assets
                    ],
                    "scratch": context.scratch,
                },
                output_schema=await self._output_schema(context),
            )
        )

        if not result.valid:
            return await self._degraded_result(context, result.errors, result.degraded)

        try:
            output = contract.model_validate(result.structured)
        except Exception as exc:  # 结构合法但类型不匹配
            return await self._degraded_result(context, [str(exc)], result.degraded)

        return await self._to_loop_result(context, output)

    async def advance(
        self,
        context: LoopContext,
        to_stage: LoopStage,
        *,
        lead_agent: Optional[str] = None,
    ) -> LoopContext:
        """推进到下一环节，保留已继承的资产（R-BIZ-005）。

        `lead_agent` 由调用方（Orchestrator）按 `policies/teaming.py` 的规则决定；
        不传时才回落到"任务入口默认主理"的本类兜底逻辑。这样"交接换主理"的
        决策权在规则层，本类只负责落库与上下文推进。
        """
        lead = lead_agent or await self._resolve_lead(context, to_stage)
        session = await self._sessions.update_stage(context.session.id, to_stage, lead)
        return context.model_copy(
            update={"session": session, "stage": to_stage, "lead_agent": lead}
        )

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------

    async def _build_context(
        self, session: TaskSession, source: EntrySource
    ) -> LoopContext:
        blackboard = (
            await self._blackboard_loader(session.user_id, session.id)
            if self._blackboard_loader is not None
            else BlackboardView(user_id=session.user_id, task_id=session.id)
        )
        return LoopContext(
            session=session,
            stage=session.loop_stage,
            lead_agent=session.lead_agent,
            blackboard=blackboard,
            inherited_assets=list(blackboard.asset_versions),
            # 进入来源决定是否需要补跑前序环节（PRD §3.2），先放暂存区，
            # 不落库；需要持久化时由 Orchestrator 写入会话元数据。
            scratch={"entry_source": source.value},
        )

    async def _output_schema(self, context: LoopContext) -> dict[str, Any]:
        """产出契约的 JSON Schema。

        优先用动态资源 output_contract（可在不发版的情况下调整契约），
        取不到时回落到业务层 Pydantic 模型生成的 Schema —— 业务层模型是
        唯一事实来源，因此这条兜底路径不会与契约漂移。

        查找键是 `(主理 agent_id, 当前环节)`，不是契约 id，也不是"该智能体唯一的
        契约"。原因：一个智能体可以承担多个环节（职业顾问同时负责 ②诊断 与 ③决策），
        按智能体查会取到另一环节的契约——填了 JSON Schema 之后就会拿错契约去校验。
        """
        try:
            spec = await self._registry.get_output_contract(
                context.lead_agent, context.stage
            )
            if spec is not None and spec.json_schema:
                return spec.json_schema
        except NotImplementedError:
            # Registry 临时不可用时回落到业务模型生成的 Schema。
            pass
        return self._contracts[context.stage].model_json_schema()

    async def _badge(self, context: LoopContext, theory_refs: list[Any]) -> AgentBadge:
        name = context.lead_agent
        role_summary = ""
        try:
            descriptor = await self._registry.get_agent(context.lead_agent)
            if descriptor is not None:
                name = descriptor.name
                role_summary = descriptor.role_summary
        except NotImplementedError:
            pass
        return AgentBadge(
            agent_id=context.lead_agent,
            name=name,
            role_summary=role_summary,
            theory_refs=list(theory_refs or []),
        )

    async def _to_loop_result(self, context: LoopContext, output: BaseModel) -> LoopResult:
        badge = await self._badge(context, list(getattr(output, "theory_refs", []) or []))
        guide = getattr(output, "guide", None)
        if not isinstance(guide, BehaviorGuide):
            # 契约里 guide 是必填项；走到这里说明契约被改坏了，走降级而不是抛错。
            return await self._degraded_result(
                context, ["环节产出缺少行为引导 guide"], False
            )

        conclusion = self._conclusion_builder(context.stage, output)
        messages: list[ConversationMessage] = []
        if conclusion:
            messages.append(
                ConversationMessage(
                    role="agent",
                    text=conclusion,
                    agent_id=context.lead_agent,
                    theory_refs=badge.theory_refs,
                )
            )

        next_stage = next_stage_after(context.stage)
        if context.stage is LoopStage.REVIEW:
            next_stage = getattr(output, "next_handoff_stage", None)

        return LoopResult(
            stage=context.stage,
            output=output.model_dump(mode="json"),
            badge=badge,
            messages=messages,
            disclosure=getattr(output, "disclosure", None),
            guide=guide,
            next_stage=next_stage,
            next_stage_reason="按 ①→⑤ 顺序推进" if next_stage else "",
        )

    async def _degraded_result(
        self, context: LoopContext, errors: list[str], degraded: bool
    ) -> LoopResult:
        """产出不合法或模型不可用时的兜底（R-SDK-008：不中断核心调用链）。

        调用方据 output["degraded"] 判断是否提示用户重试。
        """
        return LoopResult(
            stage=context.stage,
            output={
                "degraded": True,
                "model_degraded": degraded,
                "errors": list(errors),
            },
            badge=await self._badge(context, []),
            guide=BehaviorGuide(kind="question", text=self._degraded_guide_text),
        )

    async def _resolve_lead(self, context: LoopContext, to_stage: LoopStage) -> str:
        """交接后的主理。

        正式的主理判定（轴 A × 轴 B × 意图）属于
        `policies/teaming.py::LeadPolicy`，由 Orchestrator 在调用 `advance` 时传入；
        本类只做「按任务入口配置取默认主理」的兜底，保证不传 lead_agent 时
        `advance` 仍然可用（注意：该兜底与目标环节无关，不是正确的组队口径）。
        """
        try:
            for entry in await self._registry.list_task_entries():
                if entry.code == context.session.task_code and entry.lead_agent:
                    return entry.lead_agent
        except NotImplementedError:
            pass
        return context.lead_agent


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


__all__ = [
    "AgentDrivenLoopCoordinator",
    "STAGE_LABELS",
    "STAGE_OUTPUT_CONTRACTS",
    "STAGE_SEQUENCE",
    "build_stage_instruction",
    "default_conclusion_builder",
    "next_stage_after",
]
