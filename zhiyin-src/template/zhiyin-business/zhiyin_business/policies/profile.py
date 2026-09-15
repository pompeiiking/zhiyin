"""画像采集置信度规则。

规则参数来自动态资源 ``profile_collection``。本模块只解释参数并计算结果，
不读取 Repository，也不负责判断采集流程是否结束。
"""

from __future__ import annotations

from collections.abc import Sequence

from zhiyin_kernel.blackboard import ProfileField
from zhiyin_kernel.registry import PolicyParamSet

PROFILE_COLLECTION_POLICY = "profile_collection"


def calculate_overall_confidence(
    fields: Sequence[ProfileField], params: PolicyParamSet
) -> float:
    """计算已采集关键字段的等权平均置信度。

    缺失关键字段不参与平均；覆盖率由采集流程使用同一份 ``key_fields``
    独立判断。没有任何已采集关键字段时返回 ``0.0``。
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

    confidence_by_key = {field.key: field.confidence for field in fields}
    present = [
        confidence_by_key[key]
        for key in raw_key_fields
        if key in confidence_by_key
    ]
    if not present:
        return 0.0
    return sum(present) / len(present)


__all__ = ["PROFILE_COLLECTION_POLICY", "calculate_overall_confidence"]
