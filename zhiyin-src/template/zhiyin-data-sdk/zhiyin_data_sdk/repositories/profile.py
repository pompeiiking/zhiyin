"""画像活状态读写（profile_field / profile_gap）。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Sequence

from zhiyin_kernel.blackboard import (
    Profile,
    ProfileField,
    ProfileGap,
)


class ProfileRepository(ABC):
    """画像 Repository。"""

    @abstractmethod
    async def get(self, user_id: str) -> Optional[Profile]:
        """读取画像（含 fields 与 gaps）。不存在返回 None。"""

    @abstractmethod
    async def save(self, profile: Profile) -> Profile:
        """整体保存画像，返回落库后的对象。"""

    @abstractmethod
    async def upsert_field(self, user_id: str, field: ProfileField) -> ProfileField:
        """写入 / 更新单个画像字段。已存在则覆盖并刷新 updated_at。"""

    @abstractmethod
    async def list_fields(
        self, user_id: str, keys: Optional[Sequence[str]] = None
    ) -> list[ProfileField]:
        """按字段键批量读取画像字段。keys 为空表示全部。"""

    @abstractmethod
    async def list_gaps(self, user_id: str) -> list[ProfileGap]:
        """读取画像缺口清单，用于采集追问与工作台展示。"""

    @abstractmethod
    async def replace_gaps(self, user_id: str, gaps: list[ProfileGap]) -> None:
        """整体替换缺口清单。"""
