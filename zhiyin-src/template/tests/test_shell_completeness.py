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
    "facade": ("zhiyin_api.facade.application", "DefaultApplicationFacade"),
}

WORKER_SHELL: dict[str, tuple[str, str]] = {
    "impact": ("zhiyin_business.workers.impact", "ImpactPropagationWorker"),
    "active_event": ("zhiyin_business.workers.active_event", "ActiveEventWorker"),
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
    "DefaultApplicationFacade": ("zhiyin_api.facade.facade", "ApplicationFacade"),
    "ImpactPropagationWorker": ("zhiyin_business.workers.base", "Worker"),
    "ActiveEventWorker": ("zhiyin_business.workers.base", "Worker"),
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
        "zhiyin_infrastructure.pami",
        "zhiyin_infrastructure.persistence",
        "zhiyin_infrastructure.workers",
    ):
        imported = importlib.import_module(module)
        assert (imported.__doc__ or "").strip(), f"{module} 缺少说明 docstring"


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


@pytest.mark.parametrize("port", sorted(SERVICE_SHELL))
def test_skeleton_declares_its_status(port: str) -> None:
    module, class_name = SERVICE_SHELL[port]
    assert getattr(_load(module, class_name), "IMPLEMENTATION_STATUS", None) == "skeleton"


@pytest.mark.parametrize("port", sorted(WORKER_SHELL))
def test_worker_skeleton_declares_its_status(port: str) -> None:
    module, class_name = WORKER_SHELL[port]
    assert getattr(_load(module, class_name), "IMPLEMENTATION_STATUS", None) == "skeleton"


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


def test_skeletons_are_not_wired_into_the_container() -> None:
    """骨架只铺文件，不进装配表。

    装配表一注册，`--check` 就会把它算成"这个能力位有人了"。本期没有实现，
    所以必须保持 not_wired，让缺口如实可见（`missing` 会列出归属）。
    """
    from zhiyin_boot import build_container, describe_assembly

    report = describe_assembly(build_container(_test_settings()))

    assert report.services["facade"] == "not_wired"
    for port in ("orchestrator", "profile_service", "asset_service", "function_service"):
        assert report.services[port] == "not_wired"
    for port in ("impact", "active_event"):
        assert report.workers[port] == "not_wired"


def test_wired_skeleton_is_reported_as_skeleton() -> None:
    """装配层的自述优先：万一有人把骨架接进装配表，报告必须标 skeleton 而不是 wired。

    这是"文件存在 ≠ 能力具备"这条约定的机械保证。
    """
    from zhiyin_api.runtime import SKELETON
    from zhiyin_boot import describe_assembly
    from zhiyin_boot.container import Container
    from zhiyin_business.services import DefaultOrchestrator

    container = Container(
        settings=_test_settings(),
        llm=None,
        embedding=None,
        knowledge=None,
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
    assert DefaultOrchestrator.IMPLEMENTATION_STATUS == "skeleton"


# --------------------------------------------------------------------------
# 4. 动态资源交叉引用闭合（此前无守卫）
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
