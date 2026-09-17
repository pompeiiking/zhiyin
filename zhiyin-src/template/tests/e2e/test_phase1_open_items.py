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

import pytest

pytestmark = [pytest.mark.e2e, pytest.mark.phase1_open]


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
