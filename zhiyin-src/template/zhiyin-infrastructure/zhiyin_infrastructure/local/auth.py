"""默认通过登录（DefaultPassAuth）。

第一期行为：任何请求都解析为同一个本地演示用户，不做真实凭证校验。
替换为 pami IAM 时，只需换掉本模块的实现并在 boot 里改装配。
"""

from __future__ import annotations

from typing import Any

from zhiyin_kernel.enums import UserRole
from zhiyin_data_sdk.gateways.security import AuthGateway, AuthPrincipal

# 演示用户 id，必须与演示数据（seed）保持一致
DEMO_USER_ID = "demo-user-0001"


class DefaultPassAuth(AuthGateway):
    """默认通过鉴权。"""

    def __init__(self, demo_user_id: str = DEMO_USER_ID) -> None:
        self._demo_user_id = demo_user_id

    async def authenticate(self, request: dict[str, Any]) -> AuthPrincipal:
        """恒返回演示用户。"""
        return AuthPrincipal(
            user_id=self._demo_user_id,
            role=UserRole.STUDENT,
            display_name="演示同学",
            is_guest=False,
            raw_claims={"auth": "default_pass", "demo": "true"},
        )

    async def is_authenticated(self, request: dict[str, Any]) -> bool:
        """第一期恒 True。"""
        return True
