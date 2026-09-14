"""装配清单：本系统一共有哪些可替换的"能力位"。

这份清单是**装配报告的坐标系**，也是分级门禁（`data/registry/assembly_gates.json`）
的取值口径。新增一个 Port 时，只需在这里加一个名字：

1. 报告会自动多出一行状态（wired / skeleton / not_wired）；
2. 缺口会自动带上 `ownership.json` 里的归属；
3. 门禁 JSON 里引用的名字若不存在，`tests/test_assembly.py::test_gates_reference_known_ports`
   会直接失败；`tests/test_shell_completeness.py` 另外守住"落位表 ↔ 真实文件"一致。

清单是"能力位"，不是"实现"：同一能力位换实现（local → mysql → pami）不改本文件。
"""

# 外部能力（SDK 定义契约，基础设施实现）
GATEWAY_PORTS: tuple[str, ...] = (
    "llm",
    "embedding",
    "knowledge",
    "search",
    "vector",
    "cache",
    "object_store",
    "event_bus",
    "scheduler",
    "notifier",
    "auth",
    "security",
    "rate_limit",
    "feature_flags",
    "raw_query",
)

# 数据访问（读写契约）
REPOSITORY_PORTS: tuple[str, ...] = (
    "profiles",
    "behaviors",
    "memories",
    "assets",
    "sessions",
    "registry",
    "users",
)

# 事务（开启 MySQL 时才有）
TRANSACTION_PORTS: tuple[str, ...] = ("transaction_manager",)

# 编排层语义原语
ORCHESTRATION_PORTS: tuple[str, ...] = (
    "event_bus_primitive",
    "scheduler_primitive",
    "notifier_primitive",
    "state_store",
    "agent_engine",
    "workflow_engine",
)

# 业务服务（含 BFF 门面）
SERVICE_PORTS: tuple[str, ...] = (
    "loop",
    "orchestrator",
    "profile_service",
    "behavior_service",
    "memory_service",
    "asset_service",
    "workspace_service",
    "function_service",
    "identity_service",
    "registry_service",
    "facade",
)

# 异步执行者：业务规则驱动（business/workers）与纯数据管道（infrastructure/workers）。
# 两者共用同一份 `zhiyin_kernel.worker.Worker` 契约与同一个驱动
# （zhiyin_boot/workers.py），只是规则性质不同。
WORKER_PORTS: tuple[str, ...] = ("impact", "active_event", "vector_sync")

# 启动前必须齐备的能力位：缺任何一个都不许带病启动。
MINIMUM_VIABLE: tuple[str, ...] = (
    "llm",
    "knowledge",
    "search",
    "object_store",
    "event_bus",
    "scheduler",
    "notifier",
    "auth",
    "security",
    "rate_limit",
)

# 全部能力位（供守卫与报告校验使用）
ALL_PORTS: tuple[str, ...] = (
    GATEWAY_PORTS
    + REPOSITORY_PORTS
    + TRANSACTION_PORTS
    + ORCHESTRATION_PORTS
    + SERVICE_PORTS
    + WORKER_PORTS
)

__all__ = [
    "ALL_PORTS",
    "GATEWAY_PORTS",
    "MINIMUM_VIABLE",
    "ORCHESTRATION_PORTS",
    "REPOSITORY_PORTS",
    "SERVICE_PORTS",
    "TRANSACTION_PORTS",
    "WORKER_PORTS",
]
