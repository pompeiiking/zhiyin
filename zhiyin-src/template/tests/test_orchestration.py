"""编排层测试：六个原语必须真的能用，而不是只有 ABC。

这组测试的意义：修复前 `zhiyin-orchestration` 全仓 0 处引用、6 个原语只有抽象类，
相当于金字塔上多画的一格。这里逐条锁住它现在具备的行为。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from zhiyin_orchestration import (
    ContractAgentEngine,
    ContractViolationError,
    DomainEvent,
    GatewayEventBus,
    GatewayNotifier,
    GatewayScheduler,
    MemoryStateStore,
    ScheduleSpec,
    SequentialWorkflowEngine,
    StateConflictError,
    WorkflowFailedError,
    WorkflowSpec,
    WorkflowStep,
    validate_schema,
)

from zhiyin_infrastructure.local.messaging import (
    InMemoryEventBus,
    LocalNotify,
    LocalScheduler,
)
from zhiyin_data_sdk.gateways.ai import LLMGateway, LLMMessage, LLMResult


def _now() -> datetime:
    return datetime.now(timezone.utc)


class _StubLLM(LLMGateway):
    """可编程的模型桩：返回固定 structured，或抛错模拟不可用。"""

    def __init__(self, structured: dict | None = None, raises: bool = False) -> None:
        self._structured = structured
        self._raises = raises
        self.calls: list[tuple[list[LLMMessage], dict | None]] = []

    async def chat(self, messages, *, json_schema=None, temperature=0.2, timeout_s=60.0):
        self.calls.append((messages, json_schema))
        if self._raises:
            raise RuntimeError("模型服务不可用")
        return LLMResult(
            text="stub",
            structured=self._structured,
            model="stub",
            degraded=False,
        )


# --------------------------------------------------------------------------
# 事件
# --------------------------------------------------------------------------


async def test_event_bus_delivers_envelope() -> None:
    bus = GatewayEventBus(InMemoryEventBus())
    received: list[DomainEvent] = []

    async def handler(event: DomainEvent) -> None:
        received.append(event)

    bus.subscribe("profile_field_updated", handler)
    await bus.publish(
        DomainEvent(
            event_id="e1",
            event_type="profile_field_updated",
            occurred_at=_now(),
            payload={"field_key": "major"},
        )
    )

    assert len(received) == 1
    # 消费方拿到的是完整信封，不需要回查状态
    assert received[0].payload["field_key"] == "major"
    assert received[0].event_id == "e1"


async def test_event_bus_is_idempotent_by_key() -> None:
    bus = GatewayEventBus(InMemoryEventBus(), dedup_size=4)
    seen: list[str] = []
    bus.subscribe("evt", lambda event: seen.append(event.event_id))

    for _ in range(3):
        await bus.publish(
            DomainEvent(
                event_id="dup",
                event_type="evt",
                occurred_at=_now(),
                idempotency_key="same-key",
            )
        )

    assert seen == ["dup"]


async def test_event_bus_unsubscribe() -> None:
    bus = GatewayEventBus(InMemoryEventBus())
    seen: list[str] = []

    def handler(event: DomainEvent) -> None:
        seen.append(event.event_id)

    bus.subscribe("evt", handler)
    bus.unsubscribe("evt", handler)
    await bus.publish(DomainEvent(event_id="e", event_type="evt", occurred_at=_now()))
    assert seen == []


# --------------------------------------------------------------------------
# 状态
# --------------------------------------------------------------------------


def test_state_store_version_conflict() -> None:
    store = MemoryStateStore()
    first = store.write("k", {"v": 1})
    assert first.version == 1

    second = store.write("k", {"v": 2}, expected_version=1)
    assert second.version == 2

    with pytest.raises(StateConflictError):
        store.write("k", {"v": 3}, expected_version=1)


def test_state_store_read_returns_snapshot() -> None:
    store = MemoryStateStore()
    store.write("k", {"nested": {"v": 1}})
    snapshot = store.read("k")
    assert snapshot is not None
    snapshot.value["nested"]["v"] = 999
    assert store.read("k").value["nested"]["v"] == 1


# --------------------------------------------------------------------------
# 调度
# --------------------------------------------------------------------------


async def _fire(scheduler: GatewayScheduler, gateway: LocalScheduler, at: datetime) -> None:
    await gateway.tick(at)


class _ScheduledBus:
    """一次完整的调度接线：

    - `LocalScheduler` 拿到的是 **SDK Gateway**（InMemoryEventBus），
      因为它投递的是裸 payload，不是编排层的 DomainEvent 信封；
    - `GatewayEventBus` 包装**同一个** InMemoryEventBus，
      因此 LocalScheduler 投出的 tick 能被 GatewayScheduler 订阅到。

    注意：把 GatewayEventBus 直接交给 LocalScheduler 会炸 ——
    两者 publish 签名不同（信封 vs (event_type, payload)）。这是本项目
    真实踩过的接线错误，保留在此作为回归用例。
    """

    def __init__(self) -> None:
        self.underlying = InMemoryEventBus()
        self.bus = GatewayEventBus(self.underlying)
        self.gateway = LocalScheduler(self.underlying)
        self.scheduler = GatewayScheduler(self.gateway, self.bus)


async def test_scheduler_fires_registered_event() -> None:
    wiring = _ScheduledBus()
    fired: list[DomainEvent] = []
    wiring.bus.subscribe("task_stall_detected", lambda event: fired.append(event))

    base = _now()
    wiring.scheduler.register(
        ScheduleSpec(
            task_id="stall-check",
            event_type="task_stall_detected",
            payload={"user_id": "u1"},
            trigger_at=base,
        )
    )
    await _fire(wiring.scheduler, wiring.gateway, base)

    assert len(fired) == 1
    assert fired[0].payload["user_id"] == "u1"


async def test_scheduler_respects_cooldown() -> None:
    wiring = _ScheduledBus()
    fired: list[DomainEvent] = []
    wiring.bus.subscribe("reminder", lambda event: fired.append(event))

    base = _now()
    wiring.scheduler.register(
        ScheduleSpec(
            task_id="r1",
            event_type="reminder",
            payload={"user_id": "u1"},
            trigger_at=base,
            interval_s=1.0,
            cooldown_s=60.0,
        )
    )

    await _fire(wiring.scheduler, wiring.gateway, base)
    await _fire(wiring.scheduler, wiring.gateway, base + timedelta(seconds=2))

    # 两次到点，但冷却期内只实际触发一次（打扰度控制，FR-REVIEW-005）
    assert len(fired) == 1


async def test_scheduler_respects_max_triggers() -> None:
    wiring = _ScheduledBus()
    fired: list[DomainEvent] = []
    wiring.bus.subscribe("ping", lambda event: fired.append(event))

    base = _now()
    wiring.scheduler.register(
        ScheduleSpec(
            task_id="p1",
            event_type="ping",
            payload={},
            trigger_at=base,
            interval_s=1.0,
            max_triggers=2,
        )
    )

    for step in range(4):
        await _fire(wiring.scheduler, wiring.gateway, base + timedelta(seconds=step))

    assert len(fired) == 2


def test_scheduler_cancel() -> None:
    wiring = _ScheduledBus()
    wiring.scheduler.register(ScheduleSpec(task_id="x", event_type="e", payload={}))
    assert [spec.task_id for spec in wiring.scheduler.list_registered()] == ["x"]
    wiring.scheduler.cancel("x")
    assert wiring.scheduler.list_registered() == []


# --------------------------------------------------------------------------
# 通知
# --------------------------------------------------------------------------


async def test_notifier_maps_channel() -> None:
    gateway = LocalNotify()
    notifier = GatewayNotifier(gateway)

    from zhiyin_orchestration import NotifyMessage

    result = await notifier.push(
        NotifyMessage(user_id="u1", title="该复盘了", body="3 天没勾任务", channel="in_app")
    )

    assert result.delivered is True
    assert result.channel == "in_app"
    assert len(gateway.list_messages("u1")) == 1


async def test_notifier_falls_back_on_unknown_channel() -> None:
    notifier = GatewayNotifier(LocalNotify())
    from zhiyin_orchestration import NotifyMessage

    result = await notifier.push(
        NotifyMessage(user_id="u1", title="t", channel="sms-not-configured")
    )
    assert result.channel == "in_app"


# --------------------------------------------------------------------------
# 产出契约校验
# --------------------------------------------------------------------------


def test_validate_schema_basics() -> None:
    schema = {
        "type": "object",
        "required": ["name", "score"],
        "additionalProperties": False,
        "properties": {
            "name": {"type": "string", "minLength": 1},
            "score": {"type": "number", "minimum": 0, "maximum": 1},
            "kind": {"enum": ["a", "b"]},
        },
    }

    assert validate_schema(schema, {"name": "x", "score": 0.5}) == []
    assert validate_schema(schema, {"score": 0.5})
    assert validate_schema(schema, {"name": "x", "score": 2})
    assert validate_schema(schema, {"name": "x", "score": 0.5, "extra": 1})
    assert validate_schema(schema, {"name": "x", "score": 0.5, "kind": "c"})


def test_validate_schema_resolves_ref() -> None:
    schema = {
        "type": "object",
        "properties": {"item": {"$ref": "#/$defs/Item"}},
        "$defs": {
            "Item": {
                "type": "object",
                "required": ["id"],
                "properties": {"id": {"type": "string"}},
            }
        },
    }
    assert validate_schema(schema, {"item": {"id": "x"}}) == []
    assert validate_schema(schema, {"item": {}})


async def test_agent_engine_validates_contract() -> None:
    schema = {
        "type": "object",
        "required": ["text"],
        "properties": {"text": {"type": "string", "minLength": 1}},
    }

    ok = ContractAgentEngine(_StubLLM({"text": "结论"}))
    result = await ok.invoke(_request(schema))
    assert result.valid is True
    assert result.structured == {"text": "结论"}

    bad = ContractAgentEngine(_StubLLM({"text": ""}))
    result = await bad.invoke(_request(schema))
    assert result.valid is False
    assert result.errors


async def test_agent_engine_can_raise_on_violation() -> None:
    schema = {"type": "object", "required": ["text"], "properties": {"text": {"type": "string"}}}
    engine = ContractAgentEngine(_StubLLM({}), raise_on_violation=True)
    with pytest.raises(ContractViolationError):
        await engine.invoke(_request(schema))


async def test_agent_engine_degrades_when_model_unavailable() -> None:
    engine = ContractAgentEngine(_StubLLM(raises=True))
    result = await engine.invoke(_request(None))
    assert result.valid is False
    assert result.degraded is True


async def test_agent_engine_passes_schema_to_llm() -> None:
    schema = {"type": "object", "properties": {}}
    llm = _StubLLM({})
    engine = ContractAgentEngine(llm)
    await engine.invoke(_request(schema))
    assert llm.calls[0][1] == schema


def _request(schema):
    from zhiyin_orchestration import AgentRequest

    return AgentRequest(agent_id="some_agent", output_schema=schema, prompt_vars={"a": 1})


# --------------------------------------------------------------------------
# 工作流
# --------------------------------------------------------------------------


async def test_workflow_runs_in_topological_order() -> None:
    engine = SequentialWorkflowEngine(ContractAgentEngine(_StubLLM({"ok": True})))
    spec = WorkflowSpec(
        workflow_id="wf",
        steps=[
            WorkflowStep(step_id="s2", agent_id="a2", input_map={"x": "out1"}, output_key="out2", depends_on=["s1"]),
            WorkflowStep(step_id="s1", agent_id="a1", output_key="out1"),
        ],
    )

    result = await engine.run(spec, {"seed": 1})

    assert result.status == "succeeded"
    assert result.outputs["out1"] == {"ok": True}
    assert result.outputs["out2"] == {"ok": True}
    assert result.outputs["seed"] == 1


async def test_workflow_pure_step_passes_inputs_through() -> None:
    engine = SequentialWorkflowEngine(ContractAgentEngine(_StubLLM({})))
    spec = WorkflowSpec(
        workflow_id="wf",
        steps=[WorkflowStep(step_id="s1", output_key="copy", input_map={"v": "seed"})],
    )

    result = await engine.run(spec, {"seed": "value"})
    assert result.outputs["copy"] == {"v": "value"}


async def test_workflow_abort_policy_raises() -> None:
    """abort 策略下，步骤失败必须让整条流程失败，而不是静默跳过。"""
    engine = SequentialWorkflowEngine(ContractAgentEngine(_StubLLM(raises=True)))
    spec = WorkflowSpec(
        workflow_id="wf",
        failure_policy="abort",
        steps=[WorkflowStep(step_id="s1", agent_id="a", output_key="o")],
    )
    with pytest.raises(WorkflowFailedError):
        await engine.run(spec)


async def test_workflow_degrade_policy_skips_dependents() -> None:
    """degrade 策略下：失败的智能体步骤不算成功，其下游依赖无法满足也被标记失败，
    但整条流程不抛异常，返回 partially_succeeded 让调用方决定降级动作。"""
    engine = SequentialWorkflowEngine(ContractAgentEngine(_StubLLM(raises=True)))
    spec = WorkflowSpec(
        workflow_id="wf",
        failure_policy="degrade",
        steps=[
            WorkflowStep(step_id="s1", output_key="seed_copy", input_map={"v": "seed"}),
            WorkflowStep(step_id="s2", agent_id="a", output_key="o", depends_on=["s1"]),
            WorkflowStep(
                step_id="s3",
                output_key="copy",
                input_map={"v": "o"},
                depends_on=["s2"],
            ),
        ],
    )
    result = await engine.run(spec, {"seed": "value"})

    assert result.status == "partially_succeeded"
    assert result.failed_steps == ["s2", "s3"]
    # 上游成功的纯计算步骤产出仍然保留
    assert result.outputs["seed_copy"] == {"v": "value"}


async def test_workflow_all_failed_is_reported_as_failed() -> None:
    engine = SequentialWorkflowEngine(ContractAgentEngine(_StubLLM(raises=True)))
    spec = WorkflowSpec(
        workflow_id="wf",
        failure_policy="degrade",
        steps=[WorkflowStep(step_id="s1", agent_id="a", output_key="o")],
    )
    result = await engine.run(spec)
    assert result.status == "failed"
    assert result.failed_steps == ["s1"]


async def test_workflow_detects_unresolvable_dependency() -> None:
    engine = SequentialWorkflowEngine(ContractAgentEngine(_StubLLM({})))
    spec = WorkflowSpec(
        workflow_id="wf",
        failure_policy="abort",
        steps=[
            WorkflowStep(step_id="s2", output_key="o2", depends_on=["missing"]),
        ],
    )
    with pytest.raises(WorkflowFailedError):
        await engine.run(spec)
