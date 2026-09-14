"""安全与限流的 no-op 实现。

第一期不做加密 / 脱敏 / 审计 / 限流；接口保留，替换时只换实现。
"""

from __future__ import annotations

from typing import Any, Optional

from zhiyin_data_sdk.gateways.security import RateLimitGateway, SecurityGateway


class NoopSecurity(SecurityGateway):
    """不加密、不脱敏、仅打印审计日志。"""

    def encrypt(self, data: bytes) -> bytes:
        return data

    def decrypt(self, data: bytes) -> bytes:
        return data

    def mask(self, value: str, *, kind: str = "generic") -> str:
        return value

    def audit(self, record: dict[str, Any]) -> None:
        # TODO(第一期收尾): 落本地审计表，替代 print
        print(f"[audit] {record}")


class NoopRateLimit(RateLimitGateway):
    """恒放行。"""

    def allow(
        self, key: str, *, limit: Optional[int] = None, window_s: Optional[float] = None
    ) -> bool:
        return True
