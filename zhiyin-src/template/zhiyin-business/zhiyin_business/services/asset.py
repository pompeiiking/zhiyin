"""资产服务实现。

落位：`business/services/asset.py`；第一期排期实现工位：后端-2（数据访问负责人）。
依赖：`AssetRepository` + `EventBus` + `policies/impact.py`。

核心口径（R-BIZ-012）：画像字段更新 → 只重算**受影响的**资产片段 → 版本 +1 → 写 diff。
**禁止整篇重新生成。** 重算范围的判定在 `ImpactPolicy`，本类只负责执行与落库；
"哪些字段影响哪些资产"不进本文件。
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Optional, Sequence
from uuid import uuid4

from zhiyin_business.contracts.common import AssetUpdateDraft
from zhiyin_business.events import ASSET_VERSION_CHANGED, AssetVersionChangedPayload
from zhiyin_business.policies.impact import ImpactPolicy
from zhiyin_business.ports.blackboard import AssetService
from zhiyin_data_sdk.repositories import AssetRepository
from zhiyin_kernel.assets import ActionPlan, DirectionPlan, Report
from zhiyin_kernel.blackboard import AssetVersion
from zhiyin_kernel.enums import AssetType
from zhiyin_orchestration import DomainEvent, EventBus


class DefaultAssetService(AssetService):
    """资产服务默认实现。"""

    IMPLEMENTATION_STATUS = "wired"

    def __init__(
        self,
        assets: AssetRepository,
        event_bus: EventBus,
        impact_policy: ImpactPolicy,
    ) -> None:
        self._assets = assets
        self._event_bus = event_bus
        self._impact_policy = impact_policy
        self._locks: dict[tuple[str, AssetType], asyncio.Lock] = {}

    async def list_versions(self, user_id: str, asset_type: AssetType) -> list[AssetVersion]:
        return await self._assets.list_versions(user_id, asset_type)

    async def propagate(
        self, user_id: str, changed_profile_keys: Sequence[str]
    ) -> list[AssetVersion]:
        changed = list(dict.fromkeys(key.strip() for key in changed_profile_keys if key.strip()))
        if not changed:
            return []
        candidates = await self._assets.list_affected_assets(user_id, changed)
        affected = self._impact_policy.select_affected(
            changed_profile_keys=changed,
            candidates=candidates,
        )
        updated: list[AssetVersion] = []
        for current in affected:
            matched = [key for key in changed if key in current.depends_on_profile_keys]
            changed_text = "、".join(matched)
            version = await self._save_propagated_snapshot(
                user_id,
                AssetUpdateDraft(
                    asset_type=current.asset_type,
                    depends_on_profile_keys=current.depends_on_profile_keys,
                    diff_from_previous=f"画像字段更新：{changed_text}；仅重算受影响片段",
                    reason=f"画像字段 {changed_text} 发生变化",
                ),
            )
            updated.append(version)
        return updated

    async def save_version(self, user_id: str, draft: AssetUpdateDraft) -> AssetVersion:
        lock = self._locks.setdefault((user_id, draft.asset_type), asyncio.Lock())
        async with lock:
            latest = await self._assets.get_latest_version(user_id, draft.asset_type)
            saved = await self._assets.save_version(
                self._build_version(user_id, draft, latest)
            )
        await self._publish_version(saved, latest)
        return saved

    def _build_version(
        self,
        user_id: str,
        draft: AssetUpdateDraft,
        latest: Optional[AssetVersion],
    ) -> AssetVersion:
        return AssetVersion(
            id=f"av_{uuid4().hex[:12]}",
            user_id=user_id,
            asset_type=draft.asset_type,
            version=(latest.version if latest is not None else 0) + 1,
            created_at=datetime.now(timezone.utc),
            depends_on_profile_keys=list(dict.fromkeys(draft.depends_on_profile_keys)),
            diff_from_previous=(
                draft.diff_from_previous or draft.reason or "资产内容更新"
                if latest is not None
                else None
            ),
        )

    async def _publish_version(
        self, saved: AssetVersion, latest: Optional[AssetVersion]
    ) -> None:
        payload = AssetVersionChangedPayload(
            user_id=saved.user_id,
            asset_type=saved.asset_type.value,
            asset_id=saved.id,
            from_version=latest.version if latest is not None else None,
            to_version=saved.version,
            diff_from_previous=saved.diff_from_previous,
        )
        await self._event_bus.publish(
            DomainEvent(
                event_id=f"evt_{uuid4().hex}",
                event_type=ASSET_VERSION_CHANGED,
                occurred_at=datetime.now(timezone.utc),
                payload=payload.model_dump(mode="json"),
                idempotency_key=f"asset-version:{saved.id}:{saved.version}",
            )
        )

    async def save_report(
        self,
        user_id: str,
        report: Report,
        *,
        depends_on_profile_keys: Sequence[str] = (),
        reason: str = "",
    ) -> AssetVersion:
        if report.user_id != user_id:
            raise PermissionError("不能为其他用户保存诊断报告")
        return await self._save_snapshot(
            user_id,
            AssetUpdateDraft(
                asset_type=AssetType.REPORT,
                depends_on_profile_keys=list(depends_on_profile_keys),
                reason=reason or "诊断报告更新",
            ),
            report=report,
        )

    async def save_direction_plans(
        self,
        user_id: str,
        plans: list[DirectionPlan],
        *,
        depends_on_profile_keys: Sequence[str] = (),
        reason: str = "",
    ) -> AssetVersion:
        if not plans:
            raise ValueError("方向方案组不能为空")
        return await self._save_snapshot(
            user_id,
            AssetUpdateDraft(
                asset_type=AssetType.DIRECTION_PLAN,
                depends_on_profile_keys=list(depends_on_profile_keys),
                reason=reason or "方向方案更新",
            ),
            direction_plans=plans,
        )

    async def select_direction_plan(self, user_id: str, plan_id: str) -> DirectionPlan:
        return await self._assets.select_direction_plan(user_id, plan_id)

    async def save_action_plan(
        self,
        user_id: str,
        plan: ActionPlan,
        *,
        depends_on_profile_keys: Sequence[str] = (),
        reason: str = "",
    ) -> AssetVersion:
        return await self._save_snapshot(
            user_id,
            AssetUpdateDraft(
                asset_type=AssetType.ACTION_PLAN,
                depends_on_profile_keys=list(depends_on_profile_keys),
                reason=reason or "行动计划更新",
            ),
            action_plan=plan,
        )

    async def mark_task_done(self, user_id: str, task_id: str) -> ActionPlan:
        return await self._assets.mark_task_done(user_id, task_id)

    async def get_report(self, user_id: str, version: Optional[int] = None) -> Optional[Report]:
        return await self._assets.get_report(user_id, version)

    async def list_direction_plans(self, user_id: str) -> list[DirectionPlan]:
        return await self._assets.list_direction_plans(user_id)

    async def get_action_plan(self, user_id: str) -> Optional[ActionPlan]:
        return await self._assets.get_action_plan(user_id)

    async def _save_snapshot(
        self,
        user_id: str,
        draft: AssetUpdateDraft,
        *,
        report: Optional[Report] = None,
        direction_plans: Optional[list[DirectionPlan]] = None,
        action_plan: Optional[ActionPlan] = None,
    ) -> AssetVersion:
        lock = self._locks.setdefault((user_id, draft.asset_type), asyncio.Lock())
        async with lock:
            latest = await self._assets.get_latest_version(user_id, draft.asset_type)
            saved = await self._assets.save_snapshot(
                self._build_version(user_id, draft, latest),
                report=report,
                direction_plans=direction_plans,
                action_plan=action_plan,
            )
        await self._publish_version(saved, latest)
        return saved

    async def _save_propagated_snapshot(
        self, user_id: str, draft: AssetUpdateDraft
    ) -> AssetVersion:
        """把传播产生的版本和当前正文副本作为一个 Repository 操作提交。"""
        report = None
        direction_plans = None
        action_plan = None
        if draft.asset_type is AssetType.REPORT:
            report = await self._assets.get_report(user_id)
        elif draft.asset_type is AssetType.DIRECTION_PLAN:
            direction_plans = await self._assets.list_direction_plans(user_id)
        elif draft.asset_type is AssetType.ACTION_PLAN:
            action_plan = await self._assets.get_action_plan(user_id)
        return await self._save_snapshot(
            user_id,
            draft,
            report=report,
            direction_plans=direction_plans,
            action_plan=action_plan,
        )


__all__ = ["DefaultAssetService"]
