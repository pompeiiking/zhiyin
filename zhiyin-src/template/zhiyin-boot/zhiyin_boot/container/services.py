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
    from zhiyin_business.policies import (
        DefaultHandoffPolicy,
        DefaultStagePolicy,
        DependencyImpactPolicy,
        KeywordIntentPolicy,
        RegistryLeadPolicy,
        RuleFirstAxisAInferencePolicy,
        RetrievalPlanningPolicy,
    )
    from zhiyin_business.services import (
        AgentDrivenLoopCoordinator,
        DefaultAssetService,
        DefaultBehaviorService,
        DefaultConversationMemoryService,
        DefaultFunctionService,
        DefaultIdentityService,
        DefaultOrchestrator,
        DefaultProfileService,
        DefaultRegistryService,
        DefaultWorkspaceService,
    )

    if (
        container.profiles is not None
        and container.registry is not None
        and container.event_bus_primitive is not None
    ):
        container.profile_service = DefaultProfileService(
            container.profiles,
            container.registry,
            container.event_bus_primitive,
        )

    if container.behaviors is not None and container.event_bus_primitive is not None:
        container.behavior_service = DefaultBehaviorService(
            container.behaviors,
            container.event_bus_primitive,
        )

    if container.agent_engine is None or container.sessions is None:
        return
    container.memory_service = DefaultConversationMemoryService(container.memories)
    container.asset_service = DefaultAssetService(
        container.assets,
        container.event_bus_primitive,
        DependencyImpactPolicy(),
    )

    container.identity_service = DefaultIdentityService(container.auth, container.users)
    container.registry_service = DefaultRegistryService(
        container.registry, container.feature_flags
    )
    container.workspace_service = DefaultWorkspaceService(
        profiles=container.profile_service,
        assets=container.asset_service,
        memories=container.memory_service,
        behaviors=container.behavior_service,
        registry=container.registry,
        features=container.feature_flags,
        # 左栏会话列表要取会话的 `task_name`（任务名），不能拿环节名顶替
        sessions=container.sessions,
    )
    container.function_service = DefaultFunctionService(
        assets=container.asset_service,
        behaviors=container.behavior_service,
        object_store=container.object_store,
    )
    # 五环节状态机先建：编排器的 `handle_message` 通过它执行环节并拿交接信号，
    # 而它读黑板又要回调编排器，构成一个环。用惰性 lambda 打破——
    # `container.orchestrator` 在本函数返回前就已赋值，真正调用只会发生在请求处理时。
    container.loop = AgentDrivenLoopCoordinator(
        container.agent_engine,
        container.sessions,
        container.registry,
        blackboard_loader=lambda user_id, task_id: container.orchestrator.read_blackboard(
            user_id, task_id
        ),
    )
    container.orchestrator = DefaultOrchestrator(
        profiles=container.profile_service,
        behaviors=container.behavior_service,
        memories=container.memory_service,
        assets=container.asset_service,
        intent_policy=KeywordIntentPolicy(
            params_loader=lambda: container.registry.get_policy_params("routing")
        ),
        stage_policy=DefaultStagePolicy(),
        axis_a_policy=RuleFirstAxisAInferencePolicy(),
        lead_policy=RegistryLeadPolicy(container.registry),
        handoff_policy=DefaultHandoffPolicy(),
        agent_engine=container.agent_engine,
        loop=container.loop,
        search=container.search,
        retrieval_policy=RetrievalPlanningPolicy(),
        state_store=container.state_store,
        sessions=container.sessions,
        registry=container.registry,
        # 每轮对话的既成事实落在这里，刷新 / 切会话时按同一份事实恢复
        messages=container.messages,
        event_bus=container.event_bus_primitive,
    )


def build_workers(container: "Container") -> None:
    """构造业务层 Worker。

    第一期没有注册者：`impact`（影响面传播）与 `active_event`（停滞干预）的实现
    落在 `zhiyin_business/workers/`，由业务编排负责人在此注册：

        container.workers.append(ImpactPropagationWorker(container.asset_service, ...))

    注册后由 `wire_application` 的 lifespan 统一启停，也可用
    `python -m zhiyin_boot worker <name>` 独立运行，两者复用同一个 container。
    """
    from zhiyin_business.policies import ConfiguredInterventionPolicy
    from zhiyin_business.workers import ActiveEventWorker, ImpactPropagationWorker

    container.workers = []
    if container.asset_service is not None and container.event_bus_primitive is not None:
        container.workers.append(
            ImpactPropagationWorker(
                container.asset_service,
                container.event_bus_primitive,
                container.cache,
            )
        )
    if container.behavior_service is not None:
        container.workers.append(
            ActiveEventWorker(
                behaviors=container.behavior_service,
                policy=ConfiguredInterventionPolicy(),
                registry=container.registry,
                scheduler=container.scheduler_primitive,
                notifier=container.notifier_primitive,
            )
        )
    database_context = container.extra.get("database_context")
    if (
        database_context is not None
        and container.settings.use_pgvector
        and container.settings.use_pami_embedding
    ):
        from zhiyin_infrastructure.persistence.embed_tasks import EmbedTaskStore
        from zhiyin_infrastructure.workers.vector_sync import (
            VectorSyncPlanner,
            VectorSyncWorker,
        )

        task_store = EmbedTaskStore(database_context)
        container.extra["embed_tasks"] = task_store
        container.extra["vector_sync_planner"] = VectorSyncPlanner(
            task_store,
            container.vector,
            model=container.embedding.model_id,
        )
        container.workers.append(
            VectorSyncWorker(task_store, container.embedding, container.vector)
        )

    # 文档过期下架：只要权威文档存储装了就能跑（它只读自己的表，不依赖向量链路）。
    # 与 vector_sync 分开装配是刻意的——过期治理不该因为向量链路没开而停摆。
    authority = container.extra.get("retrieval_authority")
    if authority is not None:
        from zhiyin_infrastructure.workers.document_expiry import DocumentExpiryWorker

        container.workers.append(DocumentExpiryWorker(authority))


__all__ = ["build_orchestration", "build_services", "build_workers"]
