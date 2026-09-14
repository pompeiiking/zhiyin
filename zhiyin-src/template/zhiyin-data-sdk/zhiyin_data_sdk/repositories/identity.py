"""用户与登录会话读写（user_account / auth_session）。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from zhiyin_kernel.identity import AuthSession, UserAccount


class UserRepository(ABC):
    """用户 Repository。"""

    @abstractmethod
    async def get_by_id(self, user_id: str) -> Optional[UserAccount]:
        """按 id 读取用户。"""

    @abstractmethod
    async def get_by_phone(self, phone: str) -> Optional[UserAccount]:
        """按手机号读取用户，用于登录时判断是否新用户。"""

    @abstractmethod
    async def create(self, user: UserAccount) -> UserAccount:
        """创建用户。"""

    @abstractmethod
    async def touch_last_login(self, user_id: str, at: datetime) -> None:
        """刷新最后登录时间。"""

    @abstractmethod
    async def save_auth_session(self, session: AuthSession) -> AuthSession:
        """保存登录会话。"""

    @abstractmethod
    async def get_auth_session(self, token: str) -> Optional[AuthSession]:
        """按 token 读取登录会话。"""
