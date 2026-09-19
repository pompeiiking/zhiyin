"""依赖装配容器。

本包是**唯一**允许 import 全部层的位置（见 `zhiyin_boot/__init__.py`）。
按能力域拆分，避免单文件同时承担"装配表 + 报告 + 门禁 + 启停"：

    ports.py          有哪些能力位（装配报告的坐标系）
    gateways.py       外部能力用哪套实现（八个替换点都在这里）
    repositories.py   数据访问与动态资源
    services.py       编排原语 / 业务服务 / Worker
    __init__.py       Container 数据结构、装配入口、ASGI 装配
    ../report.py      装配报告与分级门禁（不产生副作用）

替换一个能力（本地模型 → pami、内存 → MySQL）只改本包，业务代码一行不动。
"""

from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass, field
from typing import Any, Optional

from zhiyin_boot.container.gateways import build_gateways
from zhiyin_boot.container.ports import GATEWAY_PORTS, MINIMUM_VIABLE
from zhiyin_boot.container.repositories import (
    build_feature_flags,
    build_repositories,
    build_transactions,
)
from zhiyin_boot.container.services import (
    build_orchestration,
    build_services,
    build_workers,
)
from zhiyin_boot.settings import Settings
from zhiyin_boot.workers import run_until_cancelled

@dataclass
class Container:
    """运行时依赖容器。

    Gateways     —— 外部能力（SDK 定义契约，基础设施层实现）
    Repositories —— 数据访问
    Primitives   —— 编排层语义原语（包装上面的 Gateway）
    Services     —— 业务层服务
    Workers      —— 业务层异步执行者（复用本容器）
    Facade       —— BFF 门面
    """

    settings: Settings

    # ---- Gateways ----
    llm: Any
    embedding: Any
    search: Any
    vector: Any
    cache: Any
    object_store: Any
    event_bus: Any
    scheduler: Any
    notifier: Any
    auth: Any
    security: Any
    rate_limit: Any
    raw_query: Optional[Any] = None

    # ---- Repositories ----
    profiles: Optional[Any] = None
    behaviors: Optional[Any] = None
    memories: Optional[Any] = None
    assets: Optional[Any] = None
    sessions: Optional[Any] = None
    registry: Optional[Any] = None
    users: Optional[Any] = None

    # ---- 事务 ----
    transactions: Optional[Any] = None

    # ---- 动态资源 ----
    feature_flags: Any = None

    # ---- 编排层语义原语（由 boot 绑定到上面的 gateway）----
    event_bus_primitive: Any = None
    scheduler_primitive: Any = None
    notifier_primitive: Any = None
    state_store: Any = None
    agent_engine: Any = None
    workflow_engine: Any = None

    # ---- 业务层服务 ----
    loop: Any = None
    orchestrator: Any = None
    profile_service: Any = None
    behavior_service: Any = None
    memory_service: Any = None
    asset_service: Any = None
    workspace_service: Any = None
    function_service: Any = None
    identity_service: Any = None
    registry_service: Any = None

    # ---- 业务层 Worker（复用本容器的 Port）----
    workers: list[Any] = field(default_factory=list)

    # ---- BFF 门面 ----
    facade: Any = None

    extra: dict[str, Any] = field(default_factory=dict)


def build_container(settings: Optional[Settings] = None) -> Container:
    """构造完整容器：Gateways → Repositories → 编排原语 → 服务 → Worker。"""
    settings = settings or Settings.from_env()
    gateway_values = build_gateways(settings)
    repository_values = build_repositories(settings)
    redis_extras = {
        key: gateway_values.pop(key)
        for key in list(gateway_values)
        if key.startswith("redis_")
    }
    infrastructure_extras = {
        key: gateway_values.pop(key)
        for key in list(gateway_values)
        if key in {"retrieval_authority"}
    }
    database_context = repository_values.pop("_database_context", None)
    container = Container(
        settings=settings,
        transactions=build_transactions(settings),
        feature_flags=build_feature_flags(settings),
        **gateway_values,
        **repository_values,
    )
    container.extra.update(redis_extras)
    container.extra.update(infrastructure_extras)
    if database_context is not None:
        container.extra["database_context"] = database_context
        configure_audit = getattr(container.search, "configure_audit", None)
        if callable(configure_audit):
            from zhiyin_infrastructure.persistence.retrieval_logs import RetrievalLogStore

            retrieval_logs = RetrievalLogStore(database_context)
            container.extra["retrieval_logs"] = retrieval_logs
            configure_audit(
                retrieval_logs,
                org_id=settings.pami_org_id or "default",
            )
    build_orchestration(container)
    build_services(container)
    build_workers(container)

    from zhiyin_api.facade.application import DefaultApplicationFacade

    container.facade = DefaultApplicationFacade(
        identity=container.identity_service,
        registry=container.registry_service,
        loop=container.loop,
        orchestrator=container.orchestrator,
        workspace=container.workspace_service,
        assets=container.asset_service,
        functions=container.function_service,
        memories=container.memory_service,
    )


    return container


def assert_minimum_viable(container: Container) -> None:
    """启动前置校验：缺任何一个最低可用部件都直接失败，别让服务带病启动。

    除"缺部件"外还拦一类**看起来正常的病**：装上了占位模型（`LocalOrMockLLM`）
    却没显式许可。占位实现能通过产出契约校验，产出的是结构合法但内容虚构的结果——
    此前漏配 `ZHIYIN_USE_PAMI_LLM` 的环境会把这种产出当业务结果落库，而门禁、
    装配报告与界面三处都不会报警。现在变成启动即失败（待决问题 D1）。

    为什么不用"env 名字"判断：部署环境的 `ZHIYIN_ENV` 就是 `local`，按环境名放行
    等于没有拦截。所以只有**显式**打开 `ZHIYIN_ALLOW_PLACEHOLDER_LLM` 才允许。
    """
    missing = [name for name in MINIMUM_VIABLE if getattr(container, name, None) is None]
    if missing:
        raise RuntimeError(f"装配不完整，缺少必需部件：{missing}")

    placeholders = [
        name
        for name in GATEWAY_PORTS
        if getattr(type(getattr(container, name, None)), "IS_PLACEHOLDER", False)
    ]
    if placeholders and not container.settings.allow_placeholder_llm:
        raise RuntimeError(
            f"以下能力位装配了**占位实现**：{placeholders}。"
            "占位产出结构合法但内容虚构，不得对外服务。"
            "请配置真实模型（如 ZHIYIN_USE_PAMI_LLM=1），"
            "或在本地/测试环境显式设置 ZHIYIN_ALLOW_PLACEHOLDER_LLM=1 表示知情使用。"
        )


def wire_application(container: Optional[Container] = None) -> Any:
    """把业务服务与 Facade 接上，挂载路由，返回 ASGI 应用。

    顺序固定：
      1. 构造编排原语与服务（已在 build_container 内完成）；
      2. 校验最低可用装配；
      3. 上报装配状态（供 /healthz 与 --check 读取）；
      4. 若 Facade 已实现则装配，否则保持未装配（接口按 DEPENDENCY_UNAVAILABLE 降级）；
      5. 挂载路由，并在 lifespan 中启停调度轮询与 Worker。

    Worker 与调度都在 lifespan 内启动：同进程部署即可用，成长期把同一个 Worker
    用 `python -m zhiyin_boot worker <name>` 独立部署，代码不需要改。
    """
    from zhiyin_api.app import create_app
    from zhiyin_api.facade import configure_facade
    from zhiyin_api.runtime import configure_runtime
    from zhiyin_boot.report import describe_assembly

    container = container or build_container()
    assert_minimum_viable(container)

    report = describe_assembly(container)
    configure_runtime(report)

    if container.facade is not None:
        configure_facade(container.facade)

    @contextlib.asynccontextmanager
    async def _lifespan(_: Any):
        stop = asyncio.Event()
        tasks: list[asyncio.Task[Any]] = []

        scheduler = container.scheduler
        start_polling = getattr(scheduler, "start_polling", None)
        if callable(start_polling):
            start_polling()

        interval = container.settings.worker_interval_s
        for worker in container.workers:
            tasks.append(
                asyncio.create_task(run_until_cancelled(worker, interval, stop))
            )

        try:
            yield
        finally:
            stop.set()
            for task in tasks:
                task.cancel()
            for task in tasks:
                with contextlib.suppress(asyncio.CancelledError, Exception):
                    await task
            stop_polling = getattr(scheduler, "stop_polling", None)
            if callable(stop_polling):
                await stop_polling()
            redis_factory = container.extra.get("redis_factory")
            if redis_factory is not None:
                await redis_factory.close()
            close_vector = getattr(container.vector, "close", None)
            if callable(close_vector):
                await close_vector()
            close_raw_query = getattr(container.raw_query, "close", None)
            if callable(close_raw_query):
                await close_raw_query()
            close_transactions = getattr(container.transactions, "close", None)
            if callable(close_transactions):
                close_transactions()
            retrieval_authority = container.extra.get("retrieval_authority")
            close_authority = getattr(retrieval_authority, "close", None)
            if callable(close_authority):
                close_authority()
            database_context = container.extra.get("database_context")
            close_database = getattr(database_context, "close", None)
            if callable(close_database):
                await close_database()

    return create_app(
        title=f"{container.settings.app_name} API",
        lifespan=_lifespan,
        # 前缀只有一个来源：Settings.api_prefix（默认 /api/v1）。
        # 换版本改配置即可，路由声明与前端都不用动。
        api_prefix=container.settings.api_prefix,
    )


__all__ = [
    "Container",
    "assert_minimum_viable",
    "build_container",
    "wire_application",
]
