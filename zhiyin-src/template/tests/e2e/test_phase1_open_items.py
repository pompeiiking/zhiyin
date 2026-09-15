"""第一期未闭合项的**标记用例**（不是验收用例）。

为什么用 xfail(strict)
----------------------
这些断言写的是**目标行为**，当前一定不成立，因此现在记为 xfail，CI 保持绿灯；
一旦有人把缺口补上，用例会变成 XPASS，`strict=True` 会让 CI **变红**，强制删掉标记
并更新清单。所以"变红"是提醒，不是回归。

    现在：xfail   → 已知未闭合，不制造红灯噪音
    修好后：XPASS  → 请删除本用例与清单中对应条目

清单与归属：`docs/数据全链路/职引-第一期未闭合项与Mock标注清单.md`

跑法：

    python -m pytest tests/e2e/test_phase1_open_items.py -v
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from zhiyin_boot import Settings, build_container

TEMPLATE_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = TEMPLATE_ROOT / "data"

pytestmark = [pytest.mark.e2e, pytest.mark.phase1_open]


def _container(tmp_path: Path):
    return build_container(
        Settings(
            env="test",
            local_data_dir=str(DATA_DIR),
            local_registry_dir=str(DATA_DIR / "registry"),
            local_knowledge_dir=str(DATA_DIR / "knowledge"),
            local_object_dir=str(tmp_path / "objects"),
            redis_url="",
        )
    )


async def _run_diagnose(container, user_id: str):
    """走真实入口进入 ② 诊断并产生一轮产出。"""
    from zhiyin_api.dto.conversation import MessageRequest, TaskEnterRequest

    session = await container.facade.enter_task(
        user_id, TaskEnterRequest(task_code="verify_direction")
    )
    return await container.facade.send_message(
        user_id,
        MessageRequest(
            task_id=session.task_id,
            message="我想验证这个方向适不适合我",
        ),
    )


@pytest.mark.asyncio
@pytest.mark.xfail(
    strict=True,
    reason="OPEN-1（未闭合）：资产正文未落库，报告页 404；实现后删除本标记",
)
async def test_open1_report_body_matches_its_version(tmp_path: Path) -> None:
    """目标行为：② 诊断跑完后，报告"有版本"就必然"有正文"。"""
    from zhiyin_kernel.enums import AssetType

    container = _container(tmp_path)
    user_id = "open1-user"
    await _run_diagnose(container, user_id)

    versions = await container.asset_service.list_versions(user_id, AssetType.REPORT)
    assert versions, "诊断环节应当产生报告版本"
    report = await container.asset_service.get_report(user_id)
    assert report is not None, "有版本却读不到正文，前端会看到「有版本、无内容」"
    assert report.version == versions[-1].version, "正文版本必须与最新版本一致"


@pytest.mark.asyncio
@pytest.mark.xfail(
    strict=True,
    reason="OPEN-2（未闭合）：本地知识检索未接入 ②③ 链路；实现后删除本标记",
)
async def test_open2_diagnose_cites_local_knowledge(tmp_path: Path) -> None:
    """目标行为：②③ 的理论引用来自 `data/knowledge/`，而不是模型占位串。"""
    container = _container(tmp_path)
    turn = await _run_diagnose(container, "open2-user")

    theory_file = json.loads(
        (DATA_DIR / "knowledge" / "theory.json").read_text(encoding="utf-8")
    )
    known_ids = {item["id"] for item in theory_file["items"]}
    cited_ids = {ref.theory_id for ref in turn.badge.theory_refs}
    assert cited_ids & known_ids, (
        "诊断结论必须引用本地知识库中的理论卡；当前引用的是模型占位串"
    )


@pytest.mark.xfail(
    strict=True,
    reason="MOCK-1（未闭合）：后端未透出内容来源标记；实现后删除本标记",
)
def test_mock_content_carries_machine_readable_source() -> None:
    """目标行为：响应里有可机器判定的内容来源标记。

    前端 `MockBadge.vue` 的注释写明"由后端把来源标记为 real，本组件自动不渲染"，
    但它拿不到任何后端字段，只能退化成对占位文案做字符串匹配。

    说明：字段命名以契约评审结论为准；落地后请同步本断言并移除 xfail
    （会同时改动 `contracts/openapi.json` 与前端 `types.ts`）。
    """
    from zhiyin_api.dto.conversation import ConversationTurnView

    fields = set(ConversationTurnView.model_fields)
    assert fields & {"source", "is_mock", "content_source"}, (
        "对话产出缺少内容来源标记，前端无法区分 Mock 与真实模型产出"
    )
