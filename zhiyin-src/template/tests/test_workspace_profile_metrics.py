"""OPEN-6 回归：工作台覆盖率/整体置信度必须走决策 5 的关键字段口径。

此前 `zhiyin_api/dto/mappers.py::workspace_page_view` 内联了
「字段数 /(字段数+缺口数)」与「全字段等权平均」，与决策 5 的**关键字段**口径
不是一回事，同一口径在两处各写一遍必然漂移。

本文件用一组"两种公式会给出不同结果"的画像把口径钉住：只要有人再把近似公式
写回映射层，这里就会红。
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from zhiyin_api.dto.mappers import workspace_page_view
from zhiyin_business.policies.profile import (
    PROFILE_COLLECTION_POLICY,
    calculate_coverage,
    calculate_overall_confidence,
)
from zhiyin_business.ports.workspace import WorkspaceView
from zhiyin_kernel.blackboard import Profile, ProfileField, ProfileGap
from zhiyin_kernel.enums import ProfileSource
from zhiyin_kernel.registry import PolicyParamSet

KEY_FIELDS = [
    "career_interest",
    "ability_strength",
    "value_anchor",
    "target_direction",
    "decision_window",
    "real_constraint",
]


def _params() -> PolicyParamSet:
    return PolicyParamSet(
        code=PROFILE_COLLECTION_POLICY,
        status="confirmed",
        value={"key_fields": KEY_FIELDS, "coverage_threshold": 0.8,
               "overall_confidence_threshold": 0.7, "gap_confidence_floor": 0.6},
    )


def _field(key: str, confidence: float) -> ProfileField:
    return ProfileField(
        key=key,
        value=f"{key}-值",
        confidence=confidence,
        source=ProfileSource.CONVERSATION,
        updated_at=datetime(2026, 9, 19, tzinfo=timezone.utc),
        evidence=["用户原话"],
    )


def test_coverage_counts_key_fields_not_all_fields() -> None:
    """非关键字段再多也不提升覆盖率——这正是旧内联公式算错的地方。"""
    fields = [_field("software_skills", 1.0), _field("project_experience", 1.0)]
    assert calculate_coverage(fields, _params()) == 0.0
    # 旧的近似公式会给 2/(2+4) = 0.333
    assert calculate_coverage(fields, _params()) != pytest.approx(2 / 6)

    covered = [_field(key, 0.9) for key in KEY_FIELDS[:5]]
    assert calculate_coverage(covered, _params()) == pytest.approx(5 / 6)


def test_overall_confidence_averages_key_fields_only() -> None:
    fields = [_field("software_skills", 1.0), _field("career_interest", 0.4)]
    # 只有 career_interest 是关键字段 → 平均就是 0.4，不被非关键字段的 1.0 抬高
    assert calculate_overall_confidence(fields, _params()) == pytest.approx(0.4)
    assert calculate_overall_confidence([_field("software_skills", 1.0)], _params()) == 0.0


def test_mapper_passes_business_metrics_through_instead_of_recomputing() -> None:
    """映射层只能透传：即使画像里有字段，也不得自行算出非零覆盖率。

    构造：2 个非关键字段 + 4 个缺口。旧公式会给 coverage=2/6≈0.333、
    confidence=1.0；业务层按决策 5 给的是 0.0 / 0.0。
    """
    profile = Profile(
        id="p1",
        user_id="u1",
        updated_at=datetime(2026, 9, 19, tzinfo=timezone.utc),
        fields=[_field("software_skills", 1.0), _field("project_experience", 1.0)],
        gaps=[
            ProfileGap(key=f"gap{i}", reason="未采集", suggested_next_action="追问")
            for i in range(4)
        ],
    )
    view = WorkspaceView(
        user_id="u1",
        profile=profile,
        profile_coverage=0.0,
        profile_overall_confidence=0.0,
    )
    panel = workspace_page_view(view).profile_panel
    assert panel.coverage == 0.0
    assert panel.overall_confidence == 0.0
    # 字段与缺口仍然照常透出，映射层不是把数据丢了
    assert len(panel.fields) == 2
    assert len(panel.gaps) == 4


def test_mapper_reflects_business_values_verbatim() -> None:
    view = WorkspaceView(
        user_id="u1",
        profile=Profile(
            id="p1",
            user_id="u1",
            updated_at=datetime(2026, 9, 19, tzinfo=timezone.utc),
            fields=[_field(key, 0.9) for key in KEY_FIELDS],
        ),
        profile_coverage=1.0,
        profile_overall_confidence=0.9,
    )
    panel = workspace_page_view(view).profile_panel
    assert panel.coverage == 1.0
    assert panel.overall_confidence == 0.9
