"""编排原语、业务服务与 Worker 的装配表。

装配顺序（与《第一期技术架构文档》§8 实施顺序 3-5 一致）：

    1. build_gateways        基础设施层：外部能力
    2. build_repositories    数据访问
    3. build_orchestration   编排层：把 Gateway 包装成业务层面向的语义原语
    4. build_services        业务层：服务实现（依赖编排层与 Repository）
    5. build_workers         业务层：异步执行者（依赖服务与 Port）

未实现的业务服务保持 None，由装配报告标为 NOT_WIRED —— 这样 `/healthz` 会显式
暴露缺口，不会出现"看起来装好了其实没实现"的假装配。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from zhiyin_boot.container import Container


def build_orchestration(container: "Container") -> None:
    """构造编排层语义原语。

    这一步是「编排层不再有第二套契约」的落点：编排层的 EventBus / Scheduler /
    Notifier 都是包装 SDK Gateway 的实现，业务层只面向编排层编程。
    """
    from zhiyin_orchestration import (
        ContractAgentEngine,
        GatewayEventBus,
        GatewayNotifier,
        GatewayScheduler,
        MemoryStateStore,
        SequentialWorkflowEngine,
    )

    container.event_bus_primitive = GatewayEventBus(container.event_bus)
    container.scheduler_primitive = GatewayScheduler(
        container.scheduler, container.event_bus_primitive
    )
    container.notifier_primitive = GatewayNotifier(container.notifier)
    container.state_store = MemoryStateStore()
    container.agent_engine = ContractAgentEngine(container.llm)
    container.workflow_engine = SequentialWorkflowEngine(container.agent_engine)


def build_services(container: "Container") -> None:
    """构造业务层服务。

    第一期只提供 LoopCoordinator 的参考实现 —— 它把 business → orchestration 的依赖
    真正建立起来。其余业务服务的落位见 `zhiyin_business/services/__init__.py` 的
    落位表，实现方写完后在这里接上（一行一个），不需要改其它任何地方。

    两个"Facade 硬前置"实现完成后在这里接上（否则 `/app/bootstrap` 无数据可返回）：

        container.identity_service = DefaultIdentityService(container.auth, container.users)
        container.registry_service = DefaultRegistryService(container.registry, container.feature_flags)

    注意 registry_service 的两个依赖都是**动态资源读取**（内容型 Repository +
    配置型 Gateway），不是数据表——它不需要事务，也不写任何状态。
    """
    from zhiyin_business.services import AgentDrivenLoopCoordinator

    if container.agent_engine is None or container.sessions is None:
        return
    container.loop = AgentDrivenLoopCoordinator(
        container.agent_engine,
        container.sessions,
        container.registry,
        # blackboard_loader 由黑板服务实现后注入；未注入时 Loop 用空黑板，
        # 因此"前序资产自动继承"目前不成立（缺失项在 `/healthz` 可见）。
    )


def build_workers(container: "Container") -> None:
    """构造业务层 Worker。

    第一期没有注册者：`impact`（影响面传播）与 `active_event`（停滞干预）的实现
    落在 `zhiyin_business/workers/`，由业务编排负责人在此注册：

        container.workers.append(ImpactPropagationWorker(container.asset_service, ...))

    注册后由 `wire_application` 的 lifespan 统一启停，也可用
    `python -m zhiyin_boot worker <name>` 独立运行，两者复用同一个 container。
    """
    container.workers = []


__all__ = ["build_orchestration", "build_services", "build_workers"]
