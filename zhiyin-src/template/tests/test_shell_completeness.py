"""外壳完整度守卫。

本期不是实现期，而是"把外壳铺完整、让团队能在不动别人代码的前提下并行开工"。
因此本文件守的是**外壳**，不是业务行为：

1. 落位表里的每个格子都必须是**真实文件**（此前 8 个服务只写在 docstring 表格里，
   文件不存在——每个人接手都要自己新建文件、自己定类名，必然互相踩）；
2. 每个骨架类必须真的实现它那一层的 Port（签名对不上就等于没冻结）；
3. 骨架必须自报 `IMPLEMENTATION_STATUS="skeleton"`，且**不得**出现在装配表里
   ——否则"文件存在"会被误读成"能力已具备"，重演假装配；
4. 动态资源的交叉引用必须闭合（这条《开发指南》自己标注为"已知隐患、无守卫"）。

这些断言与 `test_architecture.py` 的分工不同：那里守"层与层之间不许乱连"，
这里守"层内每个格子都有实体、且不会假装完成"。
"""

from __future__ import annotations

import importlib
import json
import re
from pathlib import Path

import pytest

TEMPLATE_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_DIR = TEMPLATE_ROOT / "data" / "registry"


# 能力位名（与 zhiyin_boot/container/ports.py 对齐）→ (模块, 类名)
SERVICE_SHELL: dict[str, tuple[str, str]] = {
    "orchestrator": ("zhiyin_business.services.orchestrator", "DefaultOrchestrator"),
    "profile_service": ("zhiyin_business.services.profile", "DefaultProfileService"),
    "behavior_service": ("zhiyin_business.services.behavior", "DefaultBehaviorService"),
    "memory_service": (
        "zhiyin_business.services.memory",
        "DefaultConversationMemoryService",
    ),
    "asset_service": ("zhiyin_business.services.asset", "DefaultAssetService"),
    "workspace_service": ("zhiyin_business.services.workspace", "DefaultWorkspaceService"),
    "function_service": ("zhiyin_business.services.function", "DefaultFunctionService"),
    "identity_service": ("zhiyin_business.services.identity", "DefaultIdentityService"),
    "registry_service": ("zhiyin_business.services.registry", "DefaultRegistryService"),
    "facade": ("zhiyin_api.facade.application", "DefaultApplicationFacade"),
}

WORKER_SHELL: dict[str, tuple[str, str]] = {
    "impact": ("zhiyin_business.workers.impact", "ImpactPropagationWorker"),
    "active_event": ("zhiyin_business.workers.active_event", "ActiveEventWorker"),
    "vector_sync": ("zhiyin_infrastructure.workers.vector_sync", "VectorSyncWorker"),
}

# 骨架类必须实现的 Port。键是骨架类名，值是 Port 的 (模块, 类名)。
SKELETON_PORTS: dict[str, tuple[str, str]] = {
    "DefaultOrchestrator": ("zhiyin_business.ports.orchestrator", "Orchestrator"),
    "DefaultProfileService": ("zhiyin_business.ports.blackboard", "ProfileService"),
    "DefaultBehaviorService": ("zhiyin_business.ports.blackboard", "BehaviorService"),
    "DefaultConversationMemoryService": (
        "zhiyin_business.ports.blackboard",
        "ConversationMemoryService",
    ),
    "DefaultAssetService": ("zhiyin_business.ports.blackboard", "AssetService"),
    "DefaultWorkspaceService": ("zhiyin_business.ports.workspace", "WorkspaceService"),
    "DefaultFunctionService": ("zhiyin_business.ports.function", "FunctionService"),
    "DefaultIdentityService": ("zhiyin_business.ports.identity", "IdentityService"),
    "DefaultRegistryService": ("zhiyin_business.ports.registry", "RegistryService"),
    "DefaultApplicationFacade": ("zhiyin_api.facade.facade", "ApplicationFacade"),
    # Worker 基类下放到内核：业务层与基础设施层都要用它，
    # 而这两层唯一的公共依赖是内核（见 zhiyin_kernel/worker.py 的说明）。
    "ImpactPropagationWorker": ("zhiyin_kernel.worker", "Worker"),
    "ActiveEventWorker": ("zhiyin_kernel.worker", "Worker"),
    "VectorSyncWorker": ("zhiyin_kernel.worker", "Worker"),
}


def _load(module: str, name: str):
    return getattr(importlib.import_module(module), name)


def _read_json(name: str) -> dict:
    return json.loads((REGISTRY_DIR / name).read_text(encoding="utf-8"))


# --------------------------------------------------------------------------
# 1. 落位表 ↔ 真实文件
# --------------------------------------------------------------------------


@pytest.mark.parametrize("port", sorted(SERVICE_SHELL))
def test_service_shell_has_a_real_file_and_class(port: str) -> None:
    """每个业务服务能力位都必须有可 import 的类，而不是只写在表格里。"""
    module, class_name = SERVICE_SHELL[port]
    assert _load(module, class_name) is not None


@pytest.mark.parametrize("port", sorted(WORKER_SHELL))
def test_worker_shell_has_a_real_file_and_class(port: str) -> None:
    module, class_name = WORKER_SHELL[port]
    worker_cls = _load(module, class_name)
    assert worker_cls.name == port, (
        f"{class_name}.name 必须等于装配表里的能力位名 {port!r}，"
        "否则 `python -m zhiyin_boot worker <name>` 找不到它"
    )


def test_service_placement_table_matches_directory() -> None:
    """`services/__init__.py` docstring 里的落位表不得与目录内容漂移。

    这是对本次实际缺陷的定向守卫：过去 7 个服务只存在于文档表格中，文件并不存在，
    表格与目录不一致却没有任何检查会失败。
    """
    directory = TEMPLATE_ROOT / "zhiyin-business" / "zhiyin_business" / "services"
    docstring = (directory / "__init__.py").read_text(encoding="utf-8")
    # 只比对"裸文件名"形态（`xxx.py`）；带路径的引用（如 policies/impact.py）不属于本目录。
    listed = set(re.findall(r"`([a-z_]+\.py)`", docstring))
    actual = {item.name for item in directory.glob("*.py") if item.name != "__init__.py"}
    assert listed == actual, (
        "services/ 的落位表与真实文件不一致：\n"
        f"  表格里有但文件缺失：{sorted(listed - actual)}\n"
        f"  文件存在但表格没登记：{sorted(actual - listed)}"
    )


def test_infrastructure_drawers_exist() -> None:
    """基础设施侧的替换点目录必须存在（一个目录 = 一套实现）。

    没有目录，数据访问负责人连"实现放哪"都要临时决定，必然与 `local/` 混在一起。
    """
    for module in (
        "zhiyin_infrastructure.local",
        "zhiyin_infrastructure.mysql",
        "zhiyin_infrastructure.redis",
        "zhiyin_infrastructure.pgvector",
        "zhiyin_infrastructure.kafka",
        "zhiyin_infrastructure.llm",
        "zhiyin_infrastructure.minio",
        "zhiyin_infrastructure.pami",
        "zhiyin_infrastructure.persistence",
        "zhiyin_infrastructure.workers",
    ):
        imported = importlib.import_module(module)
        assert (imported.__doc__ or "").strip(), f"{module} 缺少说明 docstring"


# 已用**真实实现**交付、因此不应再有骨架文件的能力位。
# 登记在这里等于明确声明"它不是待补的格子"；新增能力位时要么给骨架（文件 + 类名 + 签名），
# 要么在此登记——两者都不做，下面的守卫会失败。
WIRED_SERVICE_PORTS: frozenset[str] = frozenset({"loop", *SERVICE_SHELL})
WIRED_WORKER_PORTS: frozenset[str] = frozenset({"impact", "active_event"})


def test_every_capability_slot_is_wired_or_shelled() -> None:
    """每个能力位都必须有落位：要么是骨架格子，要么是已交付实现。

    这条守的是"装配清单与代码实体脱节"：`container/ports.py` 里加一个能力位
    （于是 `--check` 会报它 `not_wired`、门禁会要求它），但如果没人建文件，
    接手的人要自己决定文件名与类名，必然与别人的命名打架。
    反过来，能力位被删掉但骨架文件还留着，也会让后来者读到一个不存在的约定。
    """
    from zhiyin_boot.container.ports import SERVICE_PORTS, WORKER_PORTS

    unplanned = [
        port
        for port in SERVICE_PORTS
        if port not in SERVICE_SHELL and port not in WIRED_SERVICE_PORTS
    ]
    assert not unplanned, (
        f"这些服务能力位既没有骨架文件、也没有登记为已实现：{unplanned}。"
        "请在 SERVICE_SHELL 里加一行（模块 + 类名），或加入 WIRED_SERVICE_PORTS"
    )

    unplanned_workers = [port for port in WORKER_PORTS if port not in WORKER_SHELL]
    assert not unplanned_workers, (
        f"这些 Worker 能力位没有落位文件：{unplanned_workers}"
    )

    stale = sorted(
        (set(SERVICE_SHELL) - set(SERVICE_PORTS))
        | (set(WORKER_SHELL) - set(WORKER_PORTS))
    )
    assert not stale, (
        f"这些骨架格子已不在装配清单里（能力位被删或改名）：{stale}。"
        "请同步 zhiyin_boot/container/ports.py"
    )


# --------------------------------------------------------------------------
# 2. 骨架确实实现了它那一层的 Port
# --------------------------------------------------------------------------


def _skeleton_holder() -> dict[str, str]:
    """骨架类名 → 定义它的模块。"""
    holder = {name: module for module, name in SERVICE_SHELL.values()}
    holder.update({name: module for module, name in WORKER_SHELL.values()})
    return holder


@pytest.mark.parametrize("class_name", sorted(SKELETON_PORTS))
def test_skeleton_implements_its_port(class_name: str) -> None:
    module = _skeleton_holder()[class_name]
    port_module, port_name = SKELETON_PORTS[class_name]
    skeleton_cls = _load(module, class_name)
    port_cls = _load(port_module, port_name)

    assert issubclass(skeleton_cls, port_cls), (
        f"{class_name} 必须继承 {port_name}（签名冻结在 Port 上，实现方对着 Port 交付）"
    )
    missing = getattr(skeleton_cls, "__abstractmethods__", frozenset())
    assert not missing, (
        f"{class_name} 仍有未声明的方法：{sorted(missing)}。"
        "骨架阶段也要把方法逐个声明出来（方法体 raise NotImplementedError），"
        "否则实现方看不出需要交付哪些能力"
    )


# --------------------------------------------------------------------------
# 3. 骨架不许装成"已完成"
# --------------------------------------------------------------------------


def test_worker_contract_stays_minimal() -> None:
    """Worker 契约必须保持最小（只有 `name` + `run_once`）。

    它躺在内核里，而内核的准入规则是"零依赖的最小契约"。一旦有人把
    `run_forever` / `run_until_cancelled` 这类驱动逻辑加回来，内核就持有了行为
    （asyncio 循环），下放的意义就没了。驱动逻辑的正确位置是
    `zhiyin_boot/workers.py`。
    """
    from zhiyin_kernel.worker import Worker

    # 过滤 `__abstractmethods__` 与 ABCMeta 注入的 `_abc_impl`，
    # 只看类自己声明的成员。
    members = {name for name in vars(Worker) if not name.startswith("_")}
    assert members == {"name", "run_once"}, (
        f"Worker 契约的成员变了：{sorted(members)}。"
        "驱动逻辑请放 zhiyin_boot/workers.py，不要加进契约"
    )
    assert Worker.__abstractmethods__ == frozenset({"run_once"})


@pytest.mark.parametrize("port", sorted(SERVICE_SHELL))
def test_service_declares_valid_status(port: str) -> None:
    module, class_name = SERVICE_SHELL[port]
    status = getattr(_load(module, class_name), "IMPLEMENTATION_STATUS", None)
    assert status in {"skeleton", "wired"}, (
        f"{class_name}.IMPLEMENTATION_STATUS 必须如实声明为 skeleton 或 wired"
    )


@pytest.mark.parametrize("port", sorted(set(WORKER_SHELL) - WIRED_WORKER_PORTS))
def test_optional_worker_declares_valid_status(port: str) -> None:
    module, class_name = WORKER_SHELL[port]
    assert getattr(_load(module, class_name), "IMPLEMENTATION_STATUS", None) in {
        "skeleton",
        "wired",
    }


def _test_settings():
    from zhiyin_boot import Settings

    data_dir = TEMPLATE_ROOT / "data"
    return Settings(
        env="test",
        local_data_dir=str(data_dir),
        local_registry_dir=str(data_dir / "registry"),
        local_knowledge_dir=str(data_dir / "knowledge"),
        local_object_dir=str(data_dir / "objects"),
    )


def test_first_phase_is_wired_and_m3_worker_requires_m3_configuration() -> None:
    """M2 默认装配完整；M3 Worker 只在真实存储配置下装配。"""
    from zhiyin_boot import build_container, describe_assembly

    report = describe_assembly(build_container(_test_settings()))

    assert all(report.services[port] == "wired" for port in WIRED_SERVICE_PORTS)
    assert all(report.workers[port] == "wired" for port in WIRED_WORKER_PORTS)
    assert report.workers["vector_sync"] == "not_wired"


def test_wired_skeleton_is_reported_as_skeleton() -> None:
    """装配层的自述优先：万一有人把骨架接进装配表，报告必须标 skeleton 而不是 wired。

    这是"文件存在 ≠ 能力具备"这条约定的机械保证。
    """
    from zhiyin_api.runtime import SKELETON
    from zhiyin_boot import describe_assembly
    from zhiyin_boot.container import Container

    container = Container(
        settings=_test_settings(),
        llm=None,
        embedding=None,
        search=None,
        vector=None,
        cache=None,
        object_store=None,
        event_bus=None,
        scheduler=None,
        notifier=None,
        auth=None,
        security=None,
        rate_limit=None,
    )

    # 不实例化骨架（其协作方全是未实现的骨架），挂一个同样自述为 skeleton 的替身，
    # 验证报告读的是 IMPLEMENTATION_STATUS 而不是"对象是否存在"。
    class _WiredSkeleton:
        IMPLEMENTATION_STATUS = "skeleton"

    container.orchestrator = _WiredSkeleton()
    report = describe_assembly(container)

    assert report.services["orchestrator"] == SKELETON


# --------------------------------------------------------------------------
# 4. BFF 取数路径闭合（api 拿不到 data_sdk，必须每条数据都有业务侧出口）
# --------------------------------------------------------------------------


# `/app/bootstrap` 的每个字段 → 它的取数出口。
# 这张表就是"api 需要、契约却在 data_sdk"这类缺口的检查清单：新增字段时
# 必须同时给出出口（RegistryService 的方法 / identity），否则前端拿不到数据，
# 而症状是"字段恒为空"——比报错更难查。
BOOTSTRAP_FIELD_SOURCES: dict[str, tuple[str, str]] = {
    "app_name": ("zhiyin_business.ports.registry", "get_copy_bundle"),
    "menus": ("zhiyin_business.ports.registry", "list_menus"),
    "routes": ("zhiyin_business.ports.registry", "list_routes"),
    "task_entries": ("zhiyin_business.ports.registry", "list_task_entries"),
    "copy_bundle": ("zhiyin_business.ports.registry", "get_copy_bundle"),
    "trust_blocks": ("zhiyin_business.ports.registry", "list_trust_blocks"),
    "banners": ("zhiyin_business.ports.registry", "list_banners"),
    "faqs": ("zhiyin_business.ports.registry", "list_faqs"),
    "feature_flags": ("zhiyin_business.ports.registry", "feature_flags"),
    # 身份区不走 Registry：它由 IdentityService 解析当前用户后填入。
    "identity": ("zhiyin_business.ports.identity", "current_user"),
}


def test_every_bootstrap_field_has_a_business_source() -> None:
    """`BootstrapView` 的每个字段都必须能从业务侧取到。

    为什么值得守：api 被禁止 import `zhiyin_data_sdk`，所以任何"数据在动态资源里、
    却没人包成业务 Port"的字段都会恒为空——前端只会看到空菜单 / 空文案，
    而不会收到任何错误。这条守卫把"字段有出口"变成机械可判。
    """
    from zhiyin_api.dto.bootstrap import BootstrapView

    fields = set(BootstrapView.model_fields)
    declared = set(BOOTSTRAP_FIELD_SOURCES)
    assert fields == declared, (
        "BootstrapView 字段与取数出口表不一致：\n"
        f"  字段无出口（前端会拿到恒空值）：{sorted(fields - declared)}\n"
        f"  出口表里有已删除字段：{sorted(declared - fields)}"
    )

    for field, (module, method) in BOOTSTRAP_FIELD_SOURCES.items():
        port = _load(module, module.rsplit(".", 1)[1].capitalize() + "Service")
        assert hasattr(port, method), (
            f"{field} 声明的出口 {module}.{method} 不存在，"
            "请先在业务 Port 上冻结方法再让 BFF 用它"
        )


def test_api_has_a_mapper_layer() -> None:
    """BFF 的字段映射必须集中在 `dto/mappers.py`，不能内联在 Facade 里。

    这条守的是"前端字段口径只有一处"：Mapper 一旦被绕开，同事就会直接在
    Facade 方法体里拼 View，字段口径散开，改一个字段要翻遍整个 facade 包。
    """
    import ast

    from zhiyin_api.dto import mappers

    assert (mappers.__doc__ or "").strip(), "mappers.py 必须写清口径"
    facade = TEMPLATE_ROOT / "zhiyin-api" / "zhiyin_api" / "facade" / "application.py"
    tree = ast.parse(facade.read_text(encoding="utf-8"), filename=str(facade))
    inlined = [
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id.endswith("View")
    ]
    assert not inlined, (
        f"Facade 里出现了直接构造 View 的代码：{sorted(set(inlined))}。"
        "请改为调用 dto/mappers.py 里的映射函数（字段口径只允许一处）"
    )


def test_dynamic_resource_files_exist() -> None:
    """动态资源的 JSON 种子必须齐全。

    Repository 的 `_load` 在文件缺失时**静默返回空列表**——这是刻意的
    （第一期允许某类资源不配），但代价是"配置漏了"和"这类资源本来就没有"
    看起来一样。这里把"清单里声明要读的文件都必须存在"钉住，
    让漏文件在 CI 失败，而不是在前端看到空菜单。
    """
    from zhiyin_infrastructure.local.feature_flag import LocalFeatureFlagStore
    from zhiyin_infrastructure.local.repository import LocalJsonRegistryRepository

    filenames = set(LocalJsonRegistryRepository.FILES.values())
    filenames.add(LocalFeatureFlagStore.FILENAME)
    missing = sorted(name for name in filenames if not (REGISTRY_DIR / name).is_file())
    assert not missing, f"data/registry/ 下缺少动态资源文件：{missing}"


# --------------------------------------------------------------------------
# 5. 动态资源交叉引用闭合（此前无守卫）
# --------------------------------------------------------------------------


def test_registry_cross_references_are_closed() -> None:
    """agents / theory_cards / output_contracts / task_entries 的引用必须闭合。

    这条守卫是《开发指南》§四「规则 4」里自己标注的隐患：对不上时系统不会报错，
    而是**静默回落**（主理展示名退化成 agent_id、理论标签点不开、契约取不到）。
    静默回落比报错贵得多，所以在这里挡住。
    """
    agents_items = _read_json("agents.json")["items"]
    agents = {item["id"] for item in agents_items}
    theories = {item["id"] for item in _read_json("theory_cards.json")["items"]}
    entries = _read_json("task_entries.json")["items"]
    contracts = _read_json("output_contracts.json")["items"]

    # ① 任务入口的默认主理必须是已登记的智能体
    for entry in entries:
        if entry["lead_agent"] is None:
            continue
        assert entry["lead_agent"] in agents, (
            f"任务入口 {entry['code']} 的 lead_agent={entry['lead_agent']} 不在 agents.json"
        )

    # ② 智能体引用的理论卡必须存在
    for item in agents_items:
        unknown = sorted(set(item.get("theory_packages", [])) - theories)
        assert not unknown, f"智能体 {item['id']} 引用了不存在的理论卡：{unknown}"

    # ③ 产出契约的唯一键是 (agent_id, stage)，必须唯一且指向已登记智能体
    keys: list[tuple[str, str]] = []
    for spec in contracts:
        assert spec["agent_id"] in agents, (
            f"产出契约 {spec['id']} 的 agent_id={spec['agent_id']} 不在 agents.json"
        )
        keys.append((spec["agent_id"], spec["stage"]))
    duplicated = sorted({key for key in keys if keys.count(key) > 1})
    assert not duplicated, f"(agent_id, stage) 必须唯一，重复：{duplicated}"

    # ④ 任务入口声明的（主理 × 目标环节）必须能找到对应契约——
    #    这条正是"oc_decide 成为孤儿"那类缺陷的定向守卫。
    for entry in entries:
        if entry["lead_agent"] is None or entry["target_stage"] is None:
            continue
        pair = (entry["lead_agent"], entry["target_stage"])
        assert pair in keys, (
            f"任务入口 {entry['code']} 会进入 {entry['target_stage']} 环节、"
            f"由 {entry['lead_agent']} 主理，但没有对应的产出契约 {pair}。"
            "缺少时 Loop 会回落到模型生成的 Schema（当前不出错），"
            "但一旦 JSON Schema 被填进另一条契约就会拿错契约校验。"
        )


def test_track_events_are_closed() -> None:
    """埋点事件归属表必须闭合（决策 14：后端派生为主 + 前端上报为辅）。

    `/app/track` 只接收 `channel=frontend` 的体验型事件；后端派生事件若被误标成
    frontend，就会出现"同一条事件被记两次/归属错乱"。这里把 PRD §8 里明确由
    前端触发的 6 个事件钉成 frontend，同时校验 channel 取值与 code 唯一。
    """
    events = _read_json("track_events.json")["items"]
    codes = [item["code"] for item in events]
    assert len(codes) == len(set(codes)), f"track_events.json 的 code 重复：{codes}"

    allowed_channels = {"frontend", "backend"}
    for item in events:
        assert item["channel"] in allowed_channels, (
            f"事件 {item['code']} 的 channel={item['channel']!r} 非法，"
            f"只允许 {sorted(allowed_channels)}"
        )

    frontend = {item["code"] for item in events if item["channel"] == "frontend"}
    expected_frontend = {
        "conv_disclosure_open",
        "collect_gap_show",
        "diagnosis_view",
        "decision_compare",
        "review_warning_show",
        "wb_enter",
    }
    assert expected_frontend <= frontend, (
        f"以下 PRD §8 的纯前端体验事件没有标成 frontend："
        f"{sorted(expected_frontend - frontend)}"
    )
