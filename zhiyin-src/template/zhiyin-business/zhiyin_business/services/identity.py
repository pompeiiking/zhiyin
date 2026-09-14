"""身份服务实现（**骨架**，方法体未实现）。

落位：`business/services/identity.py` —— 业务编排负责人（与接口联调方对接）。
依赖：`AuthGateway`（认证主体）+ `UserRepository`（本地用户记录）。

它是 api 与数据访问契约之间的**唯一通道**：api 只认识
`business/ports/identity.py::IdentityService`，不认识 `AuthGateway`。

实现要点：
- `AuthGateway.authenticate(request)` 收的是**字典**（不是 FastAPI 的 Request），
  由 api 层负责把 HTTP 细节摊平成字典后传入；
- 认证主体在本地用户表缺失时要建记录（首次登录 / 演示用户），
  否则下游会写到一个不存在的 user_id 上，且失败是静默的。
"""

from __future__ import annotations

from typing import Optional

from zhiyin_business.ports.identity import IdentityService
from zhiyin_data_sdk.gateways.security import AuthGateway
from zhiyin_data_sdk.repositories import UserRepository
from zhiyin_kernel.identity import UserAccount

_TODO = "TODO(骨架): IdentityService 未实现"


class DefaultIdentityService(IdentityService):
    """身份服务默认实现（骨架）。"""

    IMPLEMENTATION_STATUS = "skeleton"

    def __init__(self, auth: AuthGateway, users: UserRepository) -> None:
        self._auth = auth
        self._users = users

    async def current_user(self, *, token: Optional[str] = None) -> UserAccount:
        raise NotImplementedError(
            f"{_TODO}：AuthGateway 解析主体 → 本地用户表补齐记录 → 返回 UserAccount"
        )


__all__ = ["DefaultIdentityService"]
