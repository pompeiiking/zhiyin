"""画像采集置信度规则。

规则参数来自动态资源 ``profile_collection``。本模块只解释参数并计算结果，
不读取 Repository，也不负责判断采集流程是否结束。

TODO(第一期未闭合): OPEN-6 —— 本规则目前只被 `DefaultProfileService.overall_confidence`
使用，而它在生产路径上没有调用方：工作台面板的覆盖率与整体置信度仍由
`zhiyin-api/zhiyin_api/dto/mappers.py::workspace_page_view` 内联计算（全字段等权），
因此决策 5 的口径在产品上看不到效果，且同一口径存在两处实现。
收敛需要同时改冻结契约（`WorkspaceView` / `ProfileService`）与共享写点 `mappers.py`，
按 `AGENTS.md` §2 / §11.2 先协调再动。
清单：docs/数据全链路/职引-第一期未闭合项与Mock标注清单.md（OPEN-6）。
"""

from __future__ import annotations

from collections.abc import Sequence

from zhiyin_kernel.blackboard import ProfileField
from zhiyin_kernel.registry import PolicyParamSet

PROFILE_COLLECTION_POLICY = "profile_collection"


def key_fields_from_params(params: PolicyParamSet) -> list[str]:
    """校验并返回关键字段清单。

    关键字段的**唯一来源**是动态资源 ``policy_params.profile_collection``：
    覆盖率、整体置信度、缺口判定和采集提示词都必须用同一份清单，
    任何一处另写一份都会随阈值调整而漂移。读不到或形状非法时显式报错，
    不静默回落成默认清单。
    """
    if params.code != PROFILE_COLLECTION_POLICY:
        raise ValueError(
            f"画像置信度参数 code 必须为 {PROFILE_COLLECTION_POLICY!r}，"
            f"实际为 {params.code!r}"
        )
    if params.status != "confirmed":
        raise ValueError("画像置信度参数尚未确认，不能用于业务计算")

    raw_key_fields = params.value.get("key_fields")
    if (
        not isinstance(raw_key_fields, list)
        or not raw_key_fields
        or any(not isinstance(key, str) or not key.strip() for key in raw_key_fields)
        or len(set(raw_key_fields)) != len(raw_key_fields)
    ):
        raise ValueError("画像置信度参数 key_fields 必须是非空且不重复的字符串列表")
    return list(raw_key_fields)


def calculate_overall_confidence(
    fields: Sequence[ProfileField], params: PolicyParamSet
) -> float:
    """计算已采集关键字段的等权平均置信度。

    缺失关键字段不参与平均；覆盖率由采集流程使用同一份 ``key_fields``
    独立判断。没有任何已采集关键字段时返回 ``0.0``。
    """
    raw_key_fields = key_fields_from_params(params)

    confidence_by_key = {field.key: field.confidence for field in fields}
    present = [
        confidence_by_key[key]
        for key in raw_key_fields
        if key in confidence_by_key
    ]
    if not present:
        return 0.0
    return sum(present) / len(present)


__all__ = [
    "PROFILE_COLLECTION_POLICY",
    "calculate_overall_confidence",
    "key_fields_from_params",
]
