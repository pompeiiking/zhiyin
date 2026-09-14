"""鉴权 / 安全 / 限流 Gateway —— 第一期的"默认通过层"。

第一期约束（《职引技术架构文档-第一期》§7.1）：
- AuthGateway       → DefaultPassAuth：固定演示用户，不校验真实凭证
- SecurityGateway   → NoopSecurity：不加密、不脱敏、不审计
- RateLimitGateway  → NoopRateLimit：恒放行

替换真实实现（pami IAM / JWT / 加密 / 限流）时只替换 Adapter，不改业务代码。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from zhiyin_kernel.enums import UserRole


class AuthPrincipal(BaseModel):
    """已认证主体。"""

    model_config = ConfigDict(extra="forbid")

    user_id: str
    role: UserRole = UserRole.STUDENT
    display_name: str = ""
    is_guest: bool = False
    raw_claims: dict[str, Any] = Field(default_factory=dict)


class AuthGateway(ABC):
    """鉴权 Port。"""

    @abstractmethod
    async def authenticate(self, request: dict[str, Any]) -> AuthPrincipal:
        """从请求中解析身份。第一期返回固定演示用户。"""

    @abstractmethod
    async def is_authenticated(self, request: dict[str, Any]) -> bool:
        """是否已认证。"""


class SecurityGateway(ABC):
    """安全 Port。第一期全部 no-op。"""

    @abstractmethod
    def encrypt(self, data: bytes) -> bytes:
        """加密。第一期原样返回。"""

    @abstractmethod
    def decrypt(self, data: bytes) -> bytes:
        """解密。第一期原样返回。"""

    @abstractmethod
    def mask(self, value: str, *, kind: str = "generic") -> str:
        """脱敏。第一期原样返回。"""

    @abstractmethod
    def audit(self, record: dict[str, Any]) -> None:
        """审计。第一期仅本地日志。"""


class RateLimitGateway(ABC):
    """限流 Port。第一期恒放行。"""

    @abstractmethod
    def allow(
        self, key: str, *, limit: Optional[int] = None, window_s: Optional[float] = None
    ) -> bool:
        """是否放行。第一期恒 True。"""
