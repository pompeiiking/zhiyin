"""接口层测试：应用能起来、统一信封生效、第一期 Facade 返回真实数据。"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

import pytest
from fastapi.testclient import TestClient

from zhiyin_api.app import API_PREFIX, create_app
from zhiyin_boot import Settings, build_container, wire_application
from zhiyin_kernel.assets import (
    ActionPhase,
    ActionPlan,
    ActionTask,
    DirectionPlan,
    Report,
    ReportGap,
    Swot,
    Verdict,
)
from zhiyin_kernel.enums import PlanRole

# 本地鉴权恒返回演示用户（`infrastructure/local/auth.py`），HTTP 层的写操作
# 只能落在这个 user_id 上，预置数据也必须用它。
DEMO_USER_ID = "demo-user-0001"


@pytest.fixture
def settings() -> Settings:
    data_dir = Path(__file__).resolve().parents[1] / "data"
    return Settings(
        env="test",
        # 刻意用本地占位模型（D1），故显式许可；否则启动前置校验拒绝装配。
        allow_placeholder_llm=True,
        local_registry_dir=str(data_dir / "registry"),
        local_knowledge_dir=str(data_dir / "knowledge"),
        local_object_dir=str(data_dir / "objects"),
    )


@pytest.fixture
def client(settings: Settings) -> TestClient:
    app = wire_application(build_container(settings))
    with TestClient(app) as test_client:
        yield test_client


def test_healthz_reports_assembly(client: TestClient) -> None:
    response = client.get("/healthz")
    assert response.status_code == 200

    body = response.json()
    assert body["status"] in {"ok", "degraded"}
    assembly = body["assembly"]
    # 已实现的部件必须如实报 wired
    assert assembly["orchestration"]["agent_engine"] == "wired"
    assert assembly["services"]["loop"] == "wired"
    assert assembly["services"]["facade"] == "wired"
    assert assembly["missing"]


def test_openapi_is_served(client: TestClient) -> None:
    """有 app 工厂的直接收益：/docs 与 openapi.json 可用，前端能生成类型。"""
    response = client.get(f"{API_PREFIX}/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    # 业务接口一律在版本前缀下（见 tests/test_api_prefix.py 的守卫）
    assert f"{API_PREFIX}/app/bootstrap" in paths
    assert f"{API_PREFIX}/app/task/enter" in paths
    assert "/healthz" in paths


def test_bootstrap_returns_first_phase_data(client: TestClient) -> None:
    """第一期 Facade 已实现：首页一次取得动态任务入口与文案资源。"""
    response = client.get(f"{API_PREFIX}/app/bootstrap")
    assert response.status_code == 200

    body = response.json()
    assert body["code"] == 0
    assert body["data"]["app_name"]
    assert body["data"]["task_entries"]
    assert set(body) >= {"code", "message", "data", "trace_id"}


def test_healthz_works_without_assembly() -> None:
    """裸 create_app（未走 boot）时 healthz 仍可用，返回空装配报告。"""
    from zhiyin_api.runtime import reset_runtime

    reset_runtime()
    with TestClient(create_app()) as bare:
        response = bare.get("/healthz")
        assert response.status_code == 200
        assert response.json()["assembly"]["gateways"] == {}


# ---------------------------------------------------------------------------
# 闭环写操作（FR-DIAG-004 / FR-DECIDE-003 / FR-ACT-004 / FR-BLOCK-002）
# ---------------------------------------------------------------------------


async def _preset_assets(container: Any) -> None:
    """预置②③④三类资产。

    这四条写端点的前置条件是"报告里已经有产出"，而第一期没有任何 HTTP 入口能
    凭空造出报告与计划（它们是①-⑤主链路跑出来的）。因此这里只走容器公开
    Service 预置，**不直接操作 Repository**——与 `tests/e2e/test_data_chain.py`
    的范式一致；被验证的是 HTTP 端点本身的行为。
    """
    await container.asset_service.save_report(
        DEMO_USER_ID,
        Report(
            id="report-api-loop",
            user_id=DEMO_USER_ID,
            version=0,
            generated_at=datetime.now(timezone.utc),
            verdict=Verdict(title="方向诊断", summary="优先验证数据分析方向"),
            swot=Swot(strength=["编程基础"], weakness=["项目证据不足"]),
            gaps=[
                ReportGap(
                    gap_id="gap-01",
                    requirement="掌握 Python 与数据分析库",
                    current_state="仅课程作业使用过",
                    suggestion="完成一个端到端分析小项目",
                    theory_refs=["theory-career-anchor"],
                )
            ],
        ),
        depends_on_profile_keys=["skills"],
    )
    await container.asset_service.save_direction_plans(
        DEMO_USER_ID,
        [
            DirectionPlan(
                id="plan-main",
                role=PlanRole.MAIN,
                name="主攻：数据分析",
                target_desc="进入数据分析岗位",
                match_score=0.65,
                fit_reason="编程基础可迁移",
                main_risk="项目证据不足",
            ),
            DirectionPlan(
                id="plan-fallback",
                role=PlanRole.FALLBACK,
                name="保底：考研",
                target_desc="升学缓冲一年",
                match_score=0.5,
                fit_reason="学业成绩稳定",
                main_risk="挤占实习时间",
            ),
        ],
        depends_on_profile_keys=["skills"],
    )
    await container.asset_service.save_action_plan(
        DEMO_USER_ID,
        ActionPlan(
            id="act-api-loop",
            phases=[
                ActionPhase(
                    name="基础夯实期",
                    date_range="2026-09-20至2026-10-18",
                    tag="工具与核心概念",
                    tasks=[
                        ActionTask(text="安装 Python 与 Anaconda"),
                        ActionTask(text="完成一个端到端分析小项目"),
                    ],
                )
            ],
        ),
        depends_on_profile_keys=["skills"],
    )


@pytest.fixture
def loop_client(settings: Settings, tmp_path: Path) -> Iterator[tuple[Any, TestClient]]:
    """同时给出容器与 HTTP 客户端：写端点必须能先预置资产，再走真实 HTTP。

    与 `client` fixture 的区别有两点：不丢弃 container；把对象存储指向 `tmp_path`
    ——日历节点直接落对象存储，用仓库里的 `data/objects` 会污染本地演示数据。

    预置走 `test_client.portal.call(...)`，即**在应用自己的事件循环里**执行，
    免得容器里的异步原语被两个 loop 交替使用。
    """
    container = build_container(
        replace(settings, local_object_dir=str(tmp_path / "objects"))
    )
    with TestClient(wire_application(container)) as test_client:
        test_client.portal.call(_preset_assets, container)
        yield container, test_client


def _section(body: dict, section_id: str) -> dict:
    """从报告全文响应里取出指定区块的正文（`sections[].content`）。"""
    sections = body["data"]["sections"]
    match = next((item for item in sections if item["id"] == section_id), None)
    assert match is not None, f"报告缺少区块：{section_id}"
    return match["content"]


def _gap_items(client: TestClient) -> list[dict]:
    body = client.get(f"{API_PREFIX}/app/report/full-text").json()
    return _section(body, "gaps")["items"]


def _direction_plans(client: TestClient) -> dict[str, dict]:
    body = client.get(f"{API_PREFIX}/app/report/full-text").json()
    return {plan["id"]: plan for plan in _section(body, "directions")["plans"]}


def _action_tasks(client: TestClient) -> list[dict]:
    body = client.get(f"{API_PREFIX}/app/report/full-text").json()
    return [task for phase in _section(body, "action")["phases"] for task in phase["tasks"]]


def _workspace(client: TestClient) -> dict:
    response = client.get(f"{API_PREFIX}/app/workspace")
    assert response.status_code == 200
    return response.json()["data"]


def _behavior_count(client: TestClient) -> int:
    """⑤ 复盘层当前行为记录数。

    工作台没有"行为条数"这个独立字段，它写在⑤环节面板的评价文案里
    （`services/workspace.py`：`已有 N 条行为记录` / `尚无复盘记录`）。
    """
    evaluation = str(_workspace(client)["review_panel"]["evaluation"])
    digits = "".join(ch for ch in evaluation if ch.isdigit())
    return int(digits) if digits else 0


def test_closed_loop_write_endpoints_change_real_business_state(
    loop_client: tuple[Any, TestClient],
) -> None:
    """四条写端点走真实 HTTP，并**复读**资产与工作台确认业务状态真的变了。

    只断言"接口返回 200"是不够的：这几个端点的价值在于把用户的动作落到资产与
    行为日志上。所以每一步都回读报告全文 / 工作台，核对同一个业务事实。
    """
    _container, client = loop_client

    # 预置已生效：②诊断有差距清单，③决策有方案，④行动有计划
    assert [item["gap_id"] for item in _gap_items(client)] == ["gap-01"]
    assert _gap_items(client)[0]["claimed"] is False
    plans = _direction_plans(client)
    assert plans["plan-main"]["selected"] is False
    assert len(_action_tasks(client)) == 2
    assert _behavior_count(client) == 0
    assert _workspace(client)["calendar_nodes"] == []

    # ① 认领差距：幂等标注，不产生新版本
    response = client.post(
        f"{API_PREFIX}/app/assets/gap-claims", json={"gap_id": "gap-01"}
    )
    assert response.status_code == 200
    claim = response.json()["data"]
    assert claim["gap_id"] == "gap-01"
    assert claim["claimed_gap_ids"] == ["gap-01"]
    assert _gap_items(client)[0]["claimed"] is True
    # 重复点击不重复记录行为（成就按首次解锁，时间线不该出现第二条相同记录）
    client.post(f"{API_PREFIX}/app/assets/gap-claims", json={"gap_id": "gap-01"})
    assert _behavior_count(client) == 1

    # ② 选定方向：互斥，未选中的方案必须自动取消
    response = client.post(
        f"{API_PREFIX}/app/assets/decision-selection", json={"plan_id": "plan-main"}
    )
    assert response.status_code == 200
    selection = response.json()["data"]
    assert selection["plan_id"] == "plan-main"
    assert selection["role"] == "main"
    plans = _direction_plans(client)
    assert plans["plan-main"]["selected"] is True
    assert plans["plan-fallback"]["selected"] is False

    # ③ 勾掉任务：任务标识口径是 `阶段名:任务文本`
    task_id = "基础夯实期:安装 Python 与 Anaconda"
    response = client.post(f"{API_PREFIX}/app/tasks/done", json={"task_id": task_id})
    assert response.status_code == 200
    done = response.json()["data"]
    assert done["task_id"] == task_id
    assert done["phase"] == "基础夯实期"
    assert done["done"] is True
    assert (done["done_total"], done["task_total"]) == (1, 2)
    assert [task["done"] for task in _action_tasks(client)] == [True, False]

    # ④ 日历：写进去之后工作台必须读得到（此前只有写端点、没有读路径）
    response = client.post(
        f"{API_PREFIX}/app/calendar/nodes",
        json={
            "title": "投递第一份实习简历",
            "due_at": "2026-10-15T09:00:00+08:00",
            "source": "planner",
            "related_task_text": "安装 Python 与 Anaconda",
        },
    )
    assert response.status_code == 200
    node = response.json()["data"]
    assert node["node_id"].startswith("cal_")
    nodes = _workspace(client)["calendar_nodes"]
    assert len(nodes) == 1
    assert nodes[0]["title"] == "投递第一份实习简历"
    assert nodes[0]["source"] == "planner"

    # ⑤ 行为闭环：三次真实动作 → 三条行为记录 → 三个成就徽章
    assert _behavior_count(client) == 3
    badges = set(_workspace(client)["blocks"]["achievement_badge_keys"])
    assert {"first_gap_claimed", "direction_selected", "first_task_done"} <= badges
