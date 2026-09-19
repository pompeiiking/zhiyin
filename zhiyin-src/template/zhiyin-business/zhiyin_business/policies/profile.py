"""画像采集置信度规则。

规则参数来自动态资源 ``profile_collection``。本模块只解释参数并计算结果，
不读取 Repository，也不负责判断采集流程是否结束。

口径收敛记录（OPEN-6 已闭合）：本模块的 ``calculate_coverage`` /
``calculate_overall_confidence`` 是覆盖率与整体置信度的**唯一实现**——
`zhiyin-business/services/workspace.py` 调它们算好后经视图字段传给
`zhiyin-api/dto/mappers.py`，mapper 只做透传、不再内联计算
（守卫：`tests/test_workspace_profile_metrics.py`
`::test_mapper_passes_business_metrics_through_instead_of_recomputing`）。
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


def calculate_coverage(
    fields: Sequence[ProfileField], params: PolicyParamSet
) -> float:
    """计算关键字段覆盖率 = 已覆盖关键字段数 / 关键字段总数。

    与 :func:`calculate_overall_confidence` 共用同一个 ``key_fields``：
    覆盖率与置信度必须来自同一份口径，否则"覆盖够了但置信度按另一套算"
    会给出自相矛盾的采集完成判定。
    """
    key_fields = key_fields_from_params(params)
    present = {field.key for field in fields}
    covered = sum(1 for key in key_fields if key in present)
    return covered / len(key_fields)


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
    "calculate_coverage",
    "calculate_overall_confidence",
    "key_fields_from_params",
]
