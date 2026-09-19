"""身份服务实现（第一波 · 后端-3）。

落位：`business/services/identity.py` —— 后端-3（赵天硕）。
依赖：`AuthGateway`（认证主体）+ `UserRepository`（本地用户记录）。

它是 api 与数据访问契约之间的**唯一通道**：api 只认识
`business/ports/identity.py::IdentityService`，不认识 `AuthGateway`。

实现口径（对着冻结 Port 交付）：
- `AuthGateway.authenticate(request)` 收的是**字典**（不是 FastAPI 的 Request），
  由 api 层负责把 HTTP 细节摊平成字典后传入；本服务不出现任何 HTTP 概念；
- `token` 为空时按"默认通过"口径取本地演示用户（第一期）；
- 认证主体在本地用户表缺失时**必须补齐记录**再返回（首次登录 / 演示用户），
  否则下游（画像 / 行为 / 资产）会写到一个不存在的 user_id 上，且失败是静默的；
- 游客同样走本方法（`role=guest`），不与登录用户分叉；
- 返回类型只能是内核形状 `UserAccount`，不得返回 data_sdk 类型。

TODO(FR-AUTH)（后续波次）：游客会话合并（`GuestSession`）与登录态刷新。
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from zhiyin_business.ports.identity import IdentityService
from zhiyin_data_sdk.gateways.security import AuthGateway
from zhiyin_data_sdk.repositories import UserRepository
from zhiyin_kernel.identity import UserAccount


class DefaultIdentityService(IdentityService):
    """身份服务默认实现：认证主体解析 → 本地用户记录补齐 → 返回 UserAccount。"""

    IMPLEMENTATION_STATUS = "wired"

    def __init__(self, auth: AuthGateway, users: UserRepository) -> None:
        self._auth = auth
        self._users = users

    async def current_user(self, *, token: Optional[str] = None) -> UserAccount:
        # 1) 认证主体解析：token 为空时传空字典，按"默认通过"口径走演示用户。
        request: dict[str, object] = {"token": token} if token else {}
        principal = await self._auth.authenticate(request)

        now = datetime.now(timezone.utc)

        # 2) 本地用户记录补齐：缺失即建号（第一期禁止写真实手机号 / 简历 / 身份证）。
        user = await self._users.get_by_id(principal.user_id)
        if user is None:
            user = await self._users.create(
                UserAccount(
                    id=principal.user_id,
                    phone=None,
                    nickname=principal.display_name,
                    role=principal.role,
                    created_at=now,
                    last_login_at=now,
                )
            )
        else:
            # 3) 已有记录：只刷新最后登录时间，不改用户数据。
            await self._users.touch_last_login(user.id, now)

        return user


__all__ = ["DefaultIdentityService"]
