"""装配层守卫：清单、报告、门禁三者必须始终对得上。

这三份东西分别是"有哪些能力位"（代码）、"现在装了什么"（报告）、
"到哪个里程碑算过"（动态资源 JSON）。它们一旦漂移，门禁就会失效，
所以用测试把它们钉在一起。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from zhiyin_api.runtime import NOT_WIRED, SKELETON, WIRED, AssemblyReport
from zhiyin_boot import (
    Settings,
    build_container,
    describe_assembly,
    evaluate_gate,
    load_gates,
    load_ownership,
)
from zhiyin_boot.container.ports import (
    ALL_PORTS,
    GATEWAY_PORTS,
    ORCHESTRATION_PORTS,
    REPOSITORY_PORTS,
    SERVICE_PORTS,
    TRANSACTION_PORTS,
    WORKER_PORTS,
)

TEMPLATE_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = TEMPLATE_ROOT / "data"
REGISTRY_DIR = DATA_DIR / "registry"

GROUP_PORTS: dict[str, tuple[str, ...]] = {
    "gateways": GATEWAY_PORTS,
    "repositories": REPOSITORY_PORTS,
    "transactions": TRANSACTION_PORTS,
    "orchestration": ORCHESTRATION_PORTS,
    "services": SERVICE_PORTS,
    "workers": WORKER_PORTS,
}


@pytest.fixture
def settings() -> Settings:
    return Settings(
        env="test",
        local_data_dir=str(DATA_DIR),
        local_registry_dir=str(REGISTRY_DIR),
        local_knowledge_dir=str(DATA_DIR / "knowledge"),
        local_object_dir=str(DATA_DIR / "objects"),
    )


def test_gates_reference_known_ports() -> None:
    """门禁 JSON 里引用的分组与能力位必须真实存在。

    否则门禁会"看起来在卡口、实际上在检查一个不存在的名字"，静默放行。
    """
    gates = load_gates(str(REGISTRY_DIR))
    assert gates, "必须存在门禁定义"

    for gate in gates:
        assert gate.require, f"里程碑 {gate.phase} 没有定义任何退出条件"
        for group, ports in gate.require.items():
            assert group in GROUP_PORTS, f"里程碑 {gate.phase} 引用了未知分组：{group}"
            for port in ports:
                assert port in GROUP_PORTS[group], (
                    f"里程碑 {gate.phase} 引用了未登记的能力位：{group}.{port}"
                )

    assert [gate.phase for gate in gates] == sorted(gate.phase for gate in gates)


def test_ownership_covers_every_port() -> None:
    """归属清单必须覆盖全部能力位：缺口也要有人认领。"""
    owners = load_ownership(str(REGISTRY_DIR))
    missing = [port for port in ALL_PORTS if port not in owners]
    assert not missing, f"以下能力位在 ownership.json 里没有归属：{missing}"


def test_report_covers_every_port(settings: Settings) -> None:
    """装配报告必须逐个能力位给状态，不允许漏报（漏报=看不见的缺口）。"""
    report = describe_assembly(build_container(settings))

    for group, ports in GROUP_PORTS.items():
        actual = getattr(report, group)
        assert set(actual) == set(ports), f"报告分组 {group} 与装配清单不一致"

    # 每个缺口都必须带归属，不能只报"缺了什么"
    assert report.missing
    assert all("待 " in item for item in report.missing)


def test_skeleton_is_reported_not_hidden(settings: Settings) -> None:
    """骨架实现必须显式暴露。

    第一期存在"形状对、能力占位"的实现（哈希伪嵌入）。若它们被报成 wired，
    就会重演"看起来装好了其实没实现"的问题。
    """
    report = describe_assembly(build_container(settings))
    skeleton = [name for name, status in report.gateways.items() if status == SKELETON]
    assert "embedding" in skeleton
    assert report.healthy is False


def test_gate_passes_only_when_requirements_are_wired() -> None:
    gate = load_gates(str(REGISTRY_DIR))[0]

    all_wired = AssemblyReport(env="test")
    for group in gate.require:
        setattr(all_wired, group, {port: WIRED for port in gate.require[group]})
    assert evaluate_gate(all_wired, gate).passed

    missing_one = AssemblyReport(env="test")
    for group in gate.require:
        setattr(missing_one, group, {port: WIRED for port in gate.require[group]})
    first_group = next(iter(gate.require))
    first_port = gate.require[first_group][0]
    getattr(missing_one, first_group)[first_port] = NOT_WIRED

    result = evaluate_gate(missing_one, gate)
    assert not result.passed
    assert any(first_port in item for item in result.unmet)


def test_phase_one_gate_is_currently_satisfied(settings: Settings) -> None:
    """里程碑 1（框架可验证）必须保持通过：它是本期的退出条件。

    里程碑 2/3/4 未达标是预期（业务主干未接），不在本测试里断言，
    避免"实现推进后测试反而失败"。
    """
    report = describe_assembly(build_container(settings))
    gates = {gate.phase: gate for gate in load_gates(str(REGISTRY_DIR))}
    result = evaluate_gate(report, gates[1])
    assert result.passed, result.unmet


def test_cli_check_is_informational_without_phase(capsys) -> None:
    """`--check` 不带 --phase 时是信息输出，不因为骨架存在而失败。"""
    from zhiyin_boot.__main__ import main

    assert main(["--check"]) == 0
    captured = capsys.readouterr()
    assert "missing" in captured.out
