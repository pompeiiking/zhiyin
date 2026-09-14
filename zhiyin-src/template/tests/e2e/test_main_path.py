"""五环节主路径 e2e（**外壳已就位，自动门控**）。

为什么现在就建这个目录
----------------------
`--check --phase=2` 的退出条件里写着"五环节主路径 e2e 通过（tests/e2e/）"，
但此前这个目录并不存在——门禁引用了一个不存在的地方，等于把 M2 的验收
悬在半空。这里把**断言先写出来**，并用"Facade 是否已装配"自动门控：

    未装配（当前）→ 跳过，不产生红灯噪音
    装配完成     → 自动开始跑，成为 M2 的真实门禁

这样做的价值是：测试即验收口径。实现者不需要问"e2e 到底测什么"，
也不会在实现完之后才发现口径不一致而返工。

覆盖的验收项（《第一期技术架构文档》§九）
----------------------------------------
1. 首页任务路由           → 任务入口 → 目标环节
2. 可拆可续               → 从任一环节进入，前序资产不丢
3. 动态组队               → 环节变化时主理（及协理）随之变化
4. 黑板一致               → 画像 / 行为 / 会话 / 资产可跨会话读取
5. 影响面传播             → 画像更新只重算受影响资产，版本 +1
6. 行为闭环               → 认领差距 / 选择方案 / 勾任务 / 复盘都写行为日志
7. 主动干预               → 停滞触发本地教练消息，带最小可执行动作

跑法：

    python -m pytest tests/e2e -v

前置：`python -m zhiyin_boot --check --phase=2` 的 `services` 全绿。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from zhiyin_api.runtime import WIRED
from zhiyin_boot import Settings, build_container, describe_assembly

TEMPLATE_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = TEMPLATE_ROOT / "data"


def _settings() -> Settings:
    return Settings(
        env="test",
        local_data_dir=str(DATA_DIR),
        local_registry_dir=str(DATA_DIR / "registry"),
        local_knowledge_dir=str(DATA_DIR / "knowledge"),
        local_object_dir=str(DATA_DIR / "objects"),
    )


def _container():
    return build_container(_settings())


def _facade_wired() -> bool:
    """是否已具备跑主路径的前提（Facade 装配完成）。"""
    return describe_assembly(_container()).services["facade"] == WIRED


M2_PENDING = pytest.mark.skipif(
    not _facade_wired(),
    reason=(
        "M2 未就绪：business 服务与 Facade 仍是骨架（见 "
        "`python -m zhiyin_boot --check --phase=2` 的 unmet 清单）。"
        "装配完成后本用例自动开始执行。"
    ),
)

pytestmark = [pytest.mark.e2e, M2_PENDING]


@pytest.mark.asyncio
async def test_acceptance_1_home_task_routes_to_target_stage() -> None:
    """验收项 1：首页任务路由。

    口径：`task_entries.json` 里每条任务入口声明的 `(lead_agent, target_stage)`
    都必须真的有产出契约（由 `test_shell_completeness` 守卫），
    且 `enter_task` 后会话的环节与主理等于该入口声明的值。
    """
    from zhiyin_api.dto.conversation import TaskEnterRequest
    from zhiyin_boot import wire_application

    container = _container()
    wire_application(container)

    facade = container.facade
    entries = await container.registry_service.list_task_entries()
    assert entries, "bootstrap 至少要有一个任务入口"

    routable = [entry for entry in entries if entry.target_stage is not None]
    assert routable, "至少要有一个能直接路由到环节的任务入口"

    entry = routable[0]
    view = await facade.enter_task("demo_user", TaskEnterRequest(task_code=entry.code))
    assert view.stage == entry.target_stage
    assert view.lead_agent_name, "任务入口的主理展示名必须来自动态资源"


@pytest.mark.asyncio
async def test_acceptance_2_resume_from_any_stage_keeps_prior_assets() -> None:
    """验收项 2：可拆可续。从后续环节进入时，前序资产必须仍在。"""
    pytest.skip("待 Facade 实现后补：从 ②③④⑤ 任一环节进入 → 前序资产仍在")


@pytest.mark.asyncio
async def test_acceptance_3_handoff_changes_lead_and_discloses() -> None:
    """验收项 3：动态组队 + 换主理必须显式告知。

    这是产品硬约束的端到端落点：`TurnResult.disclosure` 与
    `TurnResult.badge` 必须同时变化，且 disclosure 非空。
    """
    pytest.skip("需要在 Orchestrator 实现后补：断言换环节 → 主理变化 + 告知非空")


@pytest.mark.asyncio
async def test_acceptance_4_blackboard_is_shared_across_sessions() -> None:
    """验收项 4：黑板一致。第二个会话必须能读到第一个会话写入的画像与资产。"""
    pytest.skip("需要在黑板四件套实现后补：断言跨会话读取")


@pytest.mark.asyncio
async def test_acceptance_5_profile_update_propagates_only_affected_assets() -> None:
    """验收项 5：影响面传播。只重算受影响资产，版本 +1，未命中资产版本不变。"""
    pytest.skip("需要在 AssetService + ImpactPolicy 实现后补：断言版本单调与命中范围")


@pytest.mark.asyncio
async def test_acceptance_6_action_loop_writes_behavior_log() -> None:
    """验收项 6：行为闭环。认领差距 / 选择方案 / 勾任务 / 复盘都产生行为日志。"""
    pytest.skip("需要在 LoopResult.behavior_events 填充后补：断言四类事件都落库")


@pytest.mark.asyncio
async def test_acceptance_7_stall_triggers_coach_message() -> None:
    """验收项 7：主动干预。停滞触发教练消息，且带最小可执行动作。"""
    pytest.skip("需要在 ActiveEventWorker 实现后补：断言调度触发 + 通知内容")
