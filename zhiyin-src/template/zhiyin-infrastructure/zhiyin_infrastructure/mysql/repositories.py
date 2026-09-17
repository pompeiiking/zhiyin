"""七类 Data SDK Repository 的 SQLAlchemy 异步实现。"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional, TypeVar
from uuid import uuid4

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from zhiyin_data_sdk.errors import ConflictError
from zhiyin_data_sdk.repositories import (
    AssetRepository,
    BehaviorRepository,
    ConversationMemoryRepository,
    ProfileRepository,
    RegistryRepository,
    TaskSessionRepository,
    UserRepository,
)
from zhiyin_infrastructure.persistence.models import (
    AssetContentRow,
    AssetVersionRow,
    AuthSessionRow,
    Base,
    BehaviorLogRow,
    ConversationMemoryRow,
    ProfileRow,
    RegistryResourceRow,
    ReportHistoryRow,
    TaskSessionRow,
    UserAccountRow,
)
from zhiyin_kernel.assets import ActionPlan, DirectionPlan, Report
from zhiyin_kernel.blackboard import (
    AssetVersion,
    BehaviorLog,
    ConversationMemory,
    Profile,
    ProfileField,
    ProfileGap,
    TaskSession,
)
from zhiyin_kernel.dynamic_content import (
    BannerSpec,
    CopySpec,
    FaqSpec,
    MenuSpec,
    RouteSpec,
    TrustBlockSpec,
)
from zhiyin_kernel.enums import AssetType, BehaviorEventType, LoopStage, TaskStatus
from zhiyin_kernel.identity import AuthSession, UserAccount
from zhiyin_kernel.registry import (
    AgentDescriptor,
    OutputContractSpec,
    PolicyParamSet,
    TaskEntrySpec,
    TheoryCard,
    TrackEventSpec,
)

T = TypeVar("T")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:20]}"


def _payload(model: Any) -> dict[str, Any]:
    return model.model_dump(mode="json")


def _async_url(database_url: str) -> str:
    value = database_url.strip()
    if value.startswith("mysql+pymysql://"):
        return "mysql+asyncmy://" + value.removeprefix("mysql+pymysql://")
    if value.startswith("mysql://"):
        return "mysql+asyncmy://" + value.removeprefix("mysql://")
    if value.startswith("sqlite:///"):
        return "sqlite+aiosqlite:///" + value.removeprefix("sqlite:///")
    return value


class DatabaseContext:
    """共享异步 Engine、Session factory 与一次性测试建表。"""

    def __init__(
        self,
        database_url: str,
        *,
        echo: bool = False,
        auto_create: bool = False,
        engine: AsyncEngine | None = None,
    ) -> None:
        url = _async_url(database_url)
        kwargs: dict[str, Any] = {"echo": echo, "pool_pre_ping": True}
        if not url.startswith("sqlite+"):
            kwargs.update(pool_size=10, max_overflow=20, pool_recycle=1800)
        self.engine = engine or create_async_engine(url, **kwargs)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.auto_create = auto_create
        self._ready = False
        self._ready_lock = asyncio.Lock()

    async def ensure_ready(self) -> None:
        if self._ready:
            return
        async with self._ready_lock:
            if self._ready:
                return
            if self.auto_create:
                async with self.engine.begin() as connection:
                    await connection.run_sync(Base.metadata.create_all)
            self._ready = True

    async def close(self) -> None:
        await self.engine.dispose()


class _Repository:
    IMPLEMENTATION_STATUS = "wired"

    def __init__(self, context: DatabaseContext) -> None:
        self._db = context

    async def _ready(self) -> None:
        await self._db.ensure_ready()


class SqlAlchemyProfileRepository(_Repository, ProfileRepository):
    async def get(self, user_id: str) -> Optional[Profile]:
        await self._ready()
        async with self._db.sessions() as session:
            row = await session.get(ProfileRow, user_id)
            return Profile.model_validate(row.payload) if row else None

    async def save(self, profile: Profile) -> Profile:
        await self._ready()
        stored = profile.model_copy(deep=True, update={"updated_at": _now()})
        async with self._db.sessions.begin() as session:
            row = await session.get(ProfileRow, profile.user_id, with_for_update=True)
            if row is None:
                row = ProfileRow(
                    user_id=stored.user_id,
                    profile_id=stored.id,
                    version=stored.version,
                    payload=_payload(stored),
                    created_at=stored.updated_at,
                    updated_at=stored.updated_at,
                )
                session.add(row)
            else:
                row.profile_id = stored.id
                row.version = stored.version
                row.payload = _payload(stored)
                row.updated_at = stored.updated_at
        return stored

    async def _locked_profile(self, session: AsyncSession, user_id: str) -> tuple[ProfileRow, Profile]:
        row = await session.get(ProfileRow, user_id, with_for_update=True)
        if row is not None:
            return row, Profile.model_validate(row.payload)
        now = _now()
        profile = Profile(id=_new_id("prf"), user_id=user_id, updated_at=now)
        row = ProfileRow(
            user_id=user_id,
            profile_id=profile.id,
            version=profile.version,
            payload=_payload(profile),
            created_at=now,
            updated_at=now,
        )
        session.add(row)
        return row, profile

    async def upsert_field(self, user_id: str, field: ProfileField) -> ProfileField:
        await self._ready()
        incoming = field.model_copy(deep=True, update={"updated_at": _now()})
        async with self._db.sessions.begin() as session:
            row, profile = await self._locked_profile(session, user_id)
            for index, current in enumerate(profile.fields):
                if current.key == incoming.key:
                    profile.fields[index] = incoming
                    break
            else:
                profile.fields.append(incoming)
            profile.version += 1
            profile.updated_at = _now()
            row.version = profile.version
            row.payload = _payload(profile)
            row.updated_at = profile.updated_at
        return incoming.model_copy(deep=True)

    async def list_fields(
        self, user_id: str, keys: Optional[Sequence[str]] = None
    ) -> list[ProfileField]:
        profile = await self.get(user_id)
        wanted = set(keys) if keys else None
        return [
            item.model_copy(deep=True)
            for item in (profile.fields if profile else [])
            if wanted is None or item.key in wanted
        ]

    async def list_gaps(self, user_id: str) -> list[ProfileGap]:
        profile = await self.get(user_id)
        return [item.model_copy(deep=True) for item in (profile.gaps if profile else [])]

    async def replace_gaps(self, user_id: str, gaps: list[ProfileGap]) -> None:
        await self._ready()
        async with self._db.sessions.begin() as session:
            row, profile = await self._locked_profile(session, user_id)
            profile.gaps = [item.model_copy(deep=True) for item in gaps]
            profile.version += 1
            profile.updated_at = _now()
            row.version = profile.version
            row.payload = _payload(profile)
            row.updated_at = profile.updated_at


class SqlAlchemyBehaviorRepository(_Repository, BehaviorRepository):
    async def append(self, log: BehaviorLog) -> BehaviorLog:
        await self._ready()
        stored = log.model_copy(deep=True)
        if not stored.id:
            stored.id = _new_id("bhv")
        async with self._db.sessions.begin() as session:
            session.add(
                BehaviorLogRow(
                    id=stored.id,
                    user_id=stored.user_id,
                    event_type=stored.event_type.value,
                    occurred_at=stored.occurred_at,
                    payload=_payload(stored),
                )
            )
        return stored

    async def list_by_user(
        self,
        user_id: str,
        *,
        event_types: Optional[Sequence[BehaviorEventType]] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[BehaviorLog]:
        await self._ready()
        query = select(BehaviorLogRow).where(BehaviorLogRow.user_id == user_id)
        if event_types:
            query = query.where(
                BehaviorLogRow.event_type.in_([item.value for item in event_types])
            )
        if since is not None:
            query = query.where(BehaviorLogRow.occurred_at >= since)
        if until is not None:
            query = query.where(BehaviorLogRow.occurred_at <= until)
        query = query.order_by(
            BehaviorLogRow.occurred_at.desc(), BehaviorLogRow.sequence.desc()
        ).limit(max(limit, 0))
        async with self._db.sessions() as session:
            rows = (await session.scalars(query)).all()
        return [BehaviorLog.model_validate(row.payload) for row in rows]

    async def last_occurred_at(
        self, user_id: str, event_type: BehaviorEventType
    ) -> Optional[datetime]:
        await self._ready()
        query = (
            select(BehaviorLogRow)
            .where(
                BehaviorLogRow.user_id == user_id,
                BehaviorLogRow.event_type == event_type.value,
            )
            .order_by(BehaviorLogRow.occurred_at.desc(), BehaviorLogRow.sequence.desc())
            .limit(1)
        )
        async with self._db.sessions() as session:
            row = await session.scalar(query)
        return BehaviorLog.model_validate(row.payload).occurred_at if row else None


class SqlAlchemyConversationMemoryRepository(_Repository, ConversationMemoryRepository):
    @staticmethod
    def _key(task_id: str | None) -> str:
        return task_id or ""

    async def get(self, user_id: str, task_id: str) -> Optional[ConversationMemory]:
        await self._ready()
        async with self._db.sessions() as session:
            row = await session.get(ConversationMemoryRow, (user_id, self._key(task_id)))
        return ConversationMemory.model_validate(row.payload) if row else None

    async def upsert(self, memory: ConversationMemory) -> ConversationMemory:
        await self._ready()
        async with self._db.sessions.begin() as session:
            return await self._upsert(session, memory)

    async def _upsert(
        self, session: AsyncSession, memory: ConversationMemory
    ) -> ConversationMemory:
        key = (memory.user_id, self._key(memory.task_id))
        row = await session.get(ConversationMemoryRow, key, with_for_update=True)
        stored = memory.model_copy(deep=True)
        if not stored.id:
            stored.id = _new_id("mem")
        now = _now()
        if row is not None:
            previous = ConversationMemory.model_validate(row.payload)
            if now <= previous.last_active_at:
                now = previous.last_active_at + timedelta(microseconds=1)
        stored.last_active_at = now
        if row is None:
            session.add(
                ConversationMemoryRow(
                    user_id=memory.user_id,
                    task_key=self._key(memory.task_id),
                    memory_id=stored.id,
                    last_active_at=now.isoformat(),
                    payload=_payload(stored),
                )
            )
        else:
            row.memory_id = stored.id
            row.last_active_at = now.isoformat()
            row.payload = _payload(stored)
        return stored

    async def compare_and_swap(
        self,
        memory: ConversationMemory,
        *,
        expected_last_active_at: Optional[datetime],
    ) -> Optional[ConversationMemory]:
        await self._ready()
        async with self._db.sessions.begin() as session:
            key = (memory.user_id, self._key(memory.task_id))
            row = await session.get(ConversationMemoryRow, key, with_for_update=True)
            actual = (
                ConversationMemory.model_validate(row.payload).last_active_at
                if row is not None
                else None
            )
            if actual != expected_last_active_at:
                return None
            return await self._upsert(session, memory)

    async def list_by_user(self, user_id: str) -> list[ConversationMemory]:
        await self._ready()
        query = (
            select(ConversationMemoryRow)
            .where(ConversationMemoryRow.user_id == user_id)
            .order_by(ConversationMemoryRow.last_active_at.desc())
        )
        async with self._db.sessions() as session:
            rows = (await session.scalars(query)).all()
        return [ConversationMemory.model_validate(row.payload) for row in rows]

    async def delete(self, user_id: str, task_id: str) -> None:
        await self._ready()
        async with self._db.sessions.begin() as session:
            await session.execute(
                delete(ConversationMemoryRow).where(
                    ConversationMemoryRow.user_id == user_id,
                    ConversationMemoryRow.task_key == self._key(task_id),
                )
            )


class SqlAlchemyAssetRepository(_Repository, AssetRepository):
    async def get_latest_version(
        self, user_id: str, asset_type: AssetType
    ) -> Optional[AssetVersion]:
        await self._ready()
        query = (
            select(AssetVersionRow)
            .where(
                AssetVersionRow.user_id == user_id,
                AssetVersionRow.asset_type == asset_type.value,
            )
            .order_by(AssetVersionRow.version.desc())
            .limit(1)
        )
        async with self._db.sessions() as session:
            row = await session.scalar(query)
        return AssetVersion.model_validate(row.payload) if row else None

    async def list_versions(
        self, user_id: str, asset_type: AssetType
    ) -> list[AssetVersion]:
        await self._ready()
        query = (
            select(AssetVersionRow)
            .where(
                AssetVersionRow.user_id == user_id,
                AssetVersionRow.asset_type == asset_type.value,
            )
            .order_by(AssetVersionRow.version)
        )
        async with self._db.sessions() as session:
            rows = (await session.scalars(query)).all()
        return [AssetVersion.model_validate(row.payload) for row in rows]

    async def _save_version(
        self, session: AsyncSession, version: AssetVersion
    ) -> AssetVersion:
        latest = await session.scalar(
            select(AssetVersionRow)
            .where(
                AssetVersionRow.user_id == version.user_id,
                AssetVersionRow.asset_type == version.asset_type.value,
            )
            .order_by(AssetVersionRow.version.desc())
            .with_for_update()
            .limit(1)
        )
        floor = latest.version if latest else 0
        stored = version.model_copy(
            deep=True,
            update={
                "id": version.id or _new_id("av"),
                "version": max(version.version, floor + 1),
                "created_at": _now(),
            },
        )
        session.add(
            AssetVersionRow(
                id=stored.id,
                user_id=stored.user_id,
                asset_type=stored.asset_type.value,
                version=stored.version,
                created_at=stored.created_at,
                payload=_payload(stored),
            )
        )
        return stored

    async def save_version(self, version: AssetVersion) -> AssetVersion:
        await self._ready()
        try:
            async with self._db.sessions.begin() as session:
                return await self._save_version(session, version)
        except IntegrityError as exc:
            raise ConflictError("资产版本并发冲突", cause=exc) from exc

    async def save_snapshot(
        self,
        version: AssetVersion,
        *,
        report: Optional[Report] = None,
        direction_plans: Optional[list[DirectionPlan]] = None,
        action_plan: Optional[ActionPlan] = None,
    ) -> AssetVersion:
        supplied = sum(item is not None for item in (report, direction_plans, action_plan))
        if supplied > 1:
            raise ValueError("一次只能保存一种资产正文快照")
        expected = {
            AssetType.REPORT: report is not None,
            AssetType.DIRECTION_PLAN: direction_plans is not None,
            AssetType.ACTION_PLAN: action_plan is not None,
        }
        if supplied and not expected[version.asset_type]:
            raise ValueError("正文快照类型与资产版本类型不一致")
        await self._ready()
        async with self._db.sessions.begin() as session:
            stored = await self._save_version(session, version)
            if report is not None:
                if report.user_id != version.user_id:
                    raise PermissionError("报告正文与版本不属于同一用户")
                content = report.model_copy(
                    deep=True,
                    update={"version": stored.version, "generated_at": stored.created_at},
                )
                session.add(
                    ReportHistoryRow(
                        user_id=stored.user_id,
                        version=stored.version,
                        report_id=content.id,
                        payload=_payload(content),
                        created_at=stored.created_at,
                    )
                )
            elif direction_plans is not None:
                await self._put_content(
                    session,
                    stored.user_id,
                    "direction_plans",
                    [_payload(item) for item in direction_plans],
                    stored.version,
                )
            elif action_plan is not None:
                await self._put_content(
                    session,
                    stored.user_id,
                    "action_plan",
                    _payload(action_plan),
                    stored.version,
                )
            return stored

    async def _put_content(
        self,
        session: AsyncSession,
        user_id: str,
        kind: str,
        payload: Any,
        version: int = 0,
    ) -> None:
        row = await session.get(AssetContentRow, (user_id, kind), with_for_update=True)
        if row is None:
            session.add(
                AssetContentRow(
                    user_id=user_id,
                    content_type=kind,
                    version=version,
                    payload=payload,
                    updated_at=_now(),
                )
            )
        else:
            row.version = version
            row.payload = payload
            row.updated_at = _now()

    async def list_affected_assets(
        self, user_id: str, profile_keys: Sequence[str]
    ) -> list[AssetVersion]:
        changed = set(profile_keys)
        results: list[AssetVersion] = []
        for asset_type in AssetType:
            latest = await self.get_latest_version(user_id, asset_type)
            if latest and changed.intersection(latest.depends_on_profile_keys):
                results.append(latest)
        return sorted(results, key=lambda item: (item.asset_type.value, item.version))

    async def get_report(
        self, user_id: str, version: Optional[int] = None
    ) -> Optional[Report]:
        await self._ready()
        query = select(ReportHistoryRow).where(ReportHistoryRow.user_id == user_id)
        if version is not None:
            query = query.where(ReportHistoryRow.version == version)
        else:
            query = query.order_by(ReportHistoryRow.version.desc()).limit(1)
        async with self._db.sessions() as session:
            row = await session.scalar(query)
        return Report.model_validate(row.payload) if row else None

    async def save_report(self, report: Report) -> Report:
        await self._ready()
        async with self._db.sessions.begin() as session:
            latest = await session.scalar(
                select(ReportHistoryRow)
                .where(ReportHistoryRow.user_id == report.user_id)
                .order_by(ReportHistoryRow.version.desc())
                .with_for_update()
                .limit(1)
            )
            version = max(report.version, (latest.version + 1) if latest else 1)
            stored = report.model_copy(
                deep=True,
                update={"id": report.id or _new_id("rpt"), "version": version},
            )
            session.add(
                ReportHistoryRow(
                    user_id=stored.user_id,
                    version=stored.version,
                    report_id=stored.id,
                    payload=_payload(stored),
                    created_at=stored.generated_at,
                )
            )
        return stored

    async def _get_content(self, user_id: str, kind: str) -> Any | None:
        await self._ready()
        async with self._db.sessions() as session:
            row = await session.get(AssetContentRow, (user_id, kind))
        return row.payload if row else None

    async def list_direction_plans(self, user_id: str) -> list[DirectionPlan]:
        payload = await self._get_content(user_id, "direction_plans") or []
        return [DirectionPlan.model_validate(item) for item in payload]

    async def save_direction_plans(
        self, user_id: str, plans: list[DirectionPlan]
    ) -> None:
        stored = []
        for plan in plans:
            item = plan.model_copy(deep=True)
            if not item.id:
                item.id = _new_id("plan")
            stored.append(_payload(item))
        await self._ready()
        async with self._db.sessions.begin() as session:
            await self._put_content(session, user_id, "direction_plans", stored)

    async def select_direction_plan(
        self, user_id: str, plan_id: str
    ) -> DirectionPlan:
        plans = await self.list_direction_plans(user_id)
        target: DirectionPlan | None = None
        for plan in plans:
            if plan.id == plan_id:
                plan.selected = True
                plan.selected_at = _now()
                target = plan
            else:
                plan.selected = False
                plan.selected_at = None
        if target is None:
            raise LookupError(f"方向方案不存在：{plan_id}")
        await self.save_direction_plans(user_id, plans)
        return target

    async def get_action_plan(self, user_id: str) -> Optional[ActionPlan]:
        payload = await self._get_content(user_id, "action_plan")
        return ActionPlan.model_validate(payload) if payload else None

    async def save_action_plan(self, user_id: str, plan: ActionPlan) -> ActionPlan:
        stored = plan.model_copy(deep=True)
        if not stored.id:
            stored.id = _new_id("act")
        await self._ready()
        async with self._db.sessions.begin() as session:
            await self._put_content(session, user_id, "action_plan", _payload(stored))
        return stored

    async def mark_task_done(self, user_id: str, task_id: str) -> ActionPlan:
        plan = await self.get_action_plan(user_id)
        if plan is None:
            raise LookupError(f"行动计划不存在：{user_id}")
        for phase in plan.phases:
            for task in phase.tasks:
                if f"{phase.name}:{task.text}" == task_id or task.text == task_id:
                    if not task.done:
                        task.done = True
                        task.done_at = _now()
                    return await self.save_action_plan(user_id, plan)
        raise LookupError(f"行动任务不存在：{task_id}")


class SqlAlchemyTaskSessionRepository(_Repository, TaskSessionRepository):
    async def get(self, session_id: str) -> Optional[TaskSession]:
        await self._ready()
        async with self._db.sessions() as session:
            row = await session.get(TaskSessionRow, session_id)
        return TaskSession.model_validate(row.payload) if row else None

    async def find_active(
        self, user_id: str, task_code: str
    ) -> Optional[TaskSession]:
        await self._ready()
        query = (
            select(TaskSessionRow)
            .where(
                TaskSessionRow.user_id == user_id,
                TaskSessionRow.task_code == task_code,
                TaskSessionRow.status == TaskStatus.ACTIVE.value,
            )
            .order_by(TaskSessionRow.updated_at.desc())
            .limit(1)
        )
        async with self._db.sessions() as session:
            row = await session.scalar(query)
        return TaskSession.model_validate(row.payload) if row else None

    async def list_by_user(
        self, user_id: str, statuses: Optional[Sequence[TaskStatus]] = None
    ) -> list[TaskSession]:
        await self._ready()
        query = select(TaskSessionRow).where(TaskSessionRow.user_id == user_id)
        if statuses:
            query = query.where(TaskSessionRow.status.in_([item.value for item in statuses]))
        query = query.order_by(TaskSessionRow.updated_at.desc())
        async with self._db.sessions() as session:
            rows = (await session.scalars(query)).all()
        return [TaskSession.model_validate(row.payload) for row in rows]

    async def create(self, task: TaskSession) -> TaskSession:
        await self._ready()
        stored = task.model_copy(deep=True)
        if not stored.id:
            stored.id = _new_id("tsk")
        try:
            async with self._db.sessions.begin() as session:
                session.add(
                    TaskSessionRow(
                        id=stored.id,
                        user_id=stored.user_id,
                        task_code=stored.task_code,
                        status=stored.status.value,
                        updated_at=stored.updated_at,
                        payload=_payload(stored),
                    )
                )
        except IntegrityError as exc:
            raise ConflictError("任务会话已存在", cause=exc) from exc
        return stored

    async def _update(
        self,
        session_id: str,
        *,
        stage: LoopStage | None = None,
        lead_agent: str | None = None,
        status: TaskStatus | None = None,
    ) -> TaskSession:
        await self._ready()
        async with self._db.sessions.begin() as session:
            row = await session.get(TaskSessionRow, session_id, with_for_update=True)
            if row is None:
                raise LookupError(f"任务会话不存在：{session_id}")
            task = TaskSession.model_validate(row.payload)
            if stage is not None:
                task.loop_stage = stage
            if lead_agent is not None:
                task.lead_agent = lead_agent
            if status is not None:
                task.status = status
            task.updated_at = _now()
            row.status = task.status.value
            row.updated_at = task.updated_at
            row.payload = _payload(task)
            return task

    async def update_stage(
        self, session_id: str, stage: LoopStage, lead_agent: str
    ) -> TaskSession:
        return await self._update(session_id, stage=stage, lead_agent=lead_agent)

    async def update_status(
        self, session_id: str, status: TaskStatus
    ) -> TaskSession:
        return await self._update(session_id, status=status)


class SqlAlchemyUserRepository(_Repository, UserRepository):
    async def get_by_id(self, user_id: str) -> Optional[UserAccount]:
        await self._ready()
        async with self._db.sessions() as session:
            row = await session.get(UserAccountRow, user_id)
        return UserAccount.model_validate(row.payload) if row else None

    async def get_by_phone(self, phone: str) -> Optional[UserAccount]:
        await self._ready()
        async with self._db.sessions() as session:
            row = await session.scalar(
                select(UserAccountRow).where(UserAccountRow.phone == phone)
            )
        return UserAccount.model_validate(row.payload) if row else None

    async def create(self, user: UserAccount) -> UserAccount:
        await self._ready()
        stored = user.model_copy(deep=True)
        if not stored.id:
            stored.id = _new_id("usr")
        try:
            async with self._db.sessions.begin() as session:
                session.add(
                    UserAccountRow(
                        id=stored.id,
                        phone=stored.phone,
                        payload=_payload(stored),
                        created_at=stored.created_at,
                        last_login_at=stored.last_login_at,
                    )
                )
        except IntegrityError as exc:
            raise ConflictError("用户或手机号已存在", cause=exc) from exc
        return stored

    async def touch_last_login(self, user_id: str, at: datetime) -> None:
        await self._ready()
        async with self._db.sessions.begin() as session:
            row = await session.get(UserAccountRow, user_id, with_for_update=True)
            if row is None:
                raise LookupError(f"用户不存在：{user_id}")
            user = UserAccount.model_validate(row.payload)
            user.last_login_at = at
            row.last_login_at = at
            row.payload = _payload(user)

    async def save_auth_session(self, auth: AuthSession) -> AuthSession:
        await self._ready()
        async with self._db.sessions.begin() as session:
            row = await session.get(AuthSessionRow, auth.token, with_for_update=True)
            if row is None:
                session.add(
                    AuthSessionRow(
                        token=auth.token,
                        user_id=auth.user_id,
                        expires_at=auth.expires_at,
                        payload=_payload(auth),
                    )
                )
            else:
                row.user_id = auth.user_id
                row.expires_at = auth.expires_at
                row.payload = _payload(auth)
        return auth.model_copy(deep=True)

    async def get_auth_session(self, token: str) -> Optional[AuthSession]:
        await self._ready()
        async with self._db.sessions() as session:
            row = await session.get(AuthSessionRow, token)
        return AuthSession.model_validate(row.payload) if row else None


class SqlAlchemyRegistryRepository(_Repository, RegistryRepository):
    FILES = {
        "agents": "agents.json",
        "theory_cards": "theory_cards.json",
        "output_contracts": "output_contracts.json",
        "task_entries": "task_entries.json",
        "policy_params": "policy_params.json",
        "menus": "menus.json",
        "routes": "routes.json",
        "copies": "copies.json",
        "banners": "banners.json",
        "trust_blocks": "trust_blocks.json",
        "faqs": "faqs.json",
        "track_events": "track_events.json",
    }

    def __init__(self, context: DatabaseContext, seed_dir: str = "data/registry") -> None:
        super().__init__(context)
        self._seed_dir = Path(seed_dir)
        self._seeded = False
        self._seed_lock = asyncio.Lock()

    @staticmethod
    def _resource_key(kind: str, raw: dict[str, Any]) -> str:
        if kind == "output_contracts":
            return f"{raw.get('agent_id', '')}:{raw.get('stage', '')}"
        return str(raw.get("id") or raw.get("code") or raw.get("key") or "")

    async def _ensure_seeded(self) -> None:
        await self._ready()
        if self._seeded:
            return
        async with self._seed_lock:
            if self._seeded:
                return
            async with self._db.sessions.begin() as session:
                count = await session.scalar(select(func.count()).select_from(RegistryResourceRow))
                if not count:
                    now = _now()
                    for kind, filename in self.FILES.items():
                        path = self._seed_dir / filename
                        if not path.is_file():
                            continue
                        raw = json.loads(path.read_text(encoding="utf-8"))
                        items = raw.get("items", []) if isinstance(raw, dict) else raw
                        for item in items:
                            key = self._resource_key(kind, item)
                            if not key:
                                continue
                            session.add(
                                RegistryResourceRow(
                                    kind=kind,
                                    resource_key=key,
                                    status=str(item.get("status", "enabled")),
                                    sort_order=int(item.get("sort_order", 0)),
                                    bundle=str(item.get("bundle", "")),
                                    payload=item,
                                    updated_at=now,
                                )
                            )
            self._seeded = True

    async def _rows(
        self,
        kind: str,
        *,
        enabled_only: bool = False,
        bundle: str | None = None,
    ) -> list[RegistryResourceRow]:
        await self._ensure_seeded()
        query = select(RegistryResourceRow).where(RegistryResourceRow.kind == kind)
        if enabled_only:
            query = query.where(RegistryResourceRow.status == "enabled")
        if bundle is not None:
            query = query.where(RegistryResourceRow.bundle == bundle)
        query = query.order_by(RegistryResourceRow.sort_order, RegistryResourceRow.resource_key)
        async with self._db.sessions() as session:
            return list((await session.scalars(query)).all())

    async def _one(self, kind: str, key: str, model: type[T]) -> T | None:
        await self._ensure_seeded()
        async with self._db.sessions() as session:
            row = await session.get(RegistryResourceRow, (kind, key))
        return model.model_validate(row.payload) if row else None

    async def get_agent(self, agent_id: str) -> Optional[AgentDescriptor]:
        return await self._one("agents", agent_id, AgentDescriptor)

    async def list_agents(self) -> list[AgentDescriptor]:
        return [AgentDescriptor.model_validate(row.payload) for row in await self._rows("agents")]

    async def get_theory_card(self, theory_id: str) -> Optional[TheoryCard]:
        return await self._one("theory_cards", theory_id, TheoryCard)

    async def list_theory_cards(
        self, theory_ids: Optional[list[str]] = None
    ) -> list[TheoryCard]:
        cards = [TheoryCard.model_validate(row.payload) for row in await self._rows("theory_cards")]
        wanted = set(theory_ids) if theory_ids else None
        return cards if wanted is None else [card for card in cards if card.id in wanted]

    async def get_output_contract(
        self, agent_id: str, stage: LoopStage
    ) -> Optional[OutputContractSpec]:
        return await self._one(
            "output_contracts", f"{agent_id}:{stage.value}", OutputContractSpec
        )

    async def list_task_entries(self) -> list[TaskEntrySpec]:
        return [TaskEntrySpec.model_validate(row.payload) for row in await self._rows("task_entries")]

    async def get_policy_params(self, code: str) -> Optional[PolicyParamSet]:
        return await self._one("policy_params", code, PolicyParamSet)

    async def list_menus(self) -> list[MenuSpec]:
        return [MenuSpec.model_validate(row.payload) for row in await self._rows("menus", enabled_only=True)]

    async def list_routes(self) -> list[RouteSpec]:
        return [RouteSpec.model_validate(row.payload) for row in await self._rows("routes", enabled_only=True)]

    async def get_copy_bundle(self, bundle: str = "zh-CN") -> dict[str, str]:
        items = [
            CopySpec.model_validate(row.payload)
            for row in await self._rows("copies", enabled_only=True, bundle=bundle)
        ]
        return {item.code: item.text for item in items}

    async def list_banners(self) -> list[BannerSpec]:
        return [BannerSpec.model_validate(row.payload) for row in await self._rows("banners", enabled_only=True)]

    async def list_trust_blocks(self) -> list[TrustBlockSpec]:
        return [TrustBlockSpec.model_validate(row.payload) for row in await self._rows("trust_blocks", enabled_only=True)]

    async def list_faqs(self) -> list[FaqSpec]:
        return [FaqSpec.model_validate(row.payload) for row in await self._rows("faqs", enabled_only=True)]

    async def list_track_events(self) -> list[TrackEventSpec]:
        return [TrackEventSpec.model_validate(row.payload) for row in await self._rows("track_events")]


def build_repository_set(
    context: DatabaseContext, *, registry_seed_dir: str = "data/registry"
) -> dict[str, Any]:
    return {
        "profiles": SqlAlchemyProfileRepository(context),
        "behaviors": SqlAlchemyBehaviorRepository(context),
        "memories": SqlAlchemyConversationMemoryRepository(context),
        "assets": SqlAlchemyAssetRepository(context),
        "sessions": SqlAlchemyTaskSessionRepository(context),
        "registry": SqlAlchemyRegistryRepository(context, registry_seed_dir),
        "users": SqlAlchemyUserRepository(context),
    }


__all__ = [
    "DatabaseContext",
    "SqlAlchemyAssetRepository",
    "SqlAlchemyBehaviorRepository",
    "SqlAlchemyConversationMemoryRepository",
    "SqlAlchemyProfileRepository",
    "SqlAlchemyRegistryRepository",
    "SqlAlchemyTaskSessionRepository",
    "SqlAlchemyUserRepository",
    "build_repository_set",
]
