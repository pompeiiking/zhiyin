"""SDK 统一异常。

约束（对应《职引技术架构-分层详细设计》R-SDK-007）：
业务层不感知 MySQL / Redis / ES 等具体错误，只感知本模块定义的异常。
"""

from __future__ import annotations

from typing import Any, Optional


class SdkError(Exception):
    """SDK 异常基类。"""

    code: str = "SDK_ERROR"
    retryable: bool = False

    def __init__(
        self,
        message: str,
        *,
        detail: Optional[dict[str, Any]] = None,
        cause: Optional[BaseException] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail or {}
        self.cause = cause

    def __str__(self) -> str:  # pragma: no cover - 便于日志排查
        return f"[{self.code}] {self.message}"


class NotFoundError(SdkError):
    """目标资源不存在。"""

    code = "NOT_FOUND"


class ConflictError(SdkError):
    """版本冲突 / 唯一约束冲突。"""

    code = "CONFLICT"
    retryable = True


class ValidationError(SdkError):
    """数据不满足契约约束。"""

    code = "VALIDATION"


class UnavailableError(SdkError):
    """外部依赖不可用。

    第一期用于 pami / 向量检索 / 对象存储不可用时的显式降级信号。
    """

    code = "UNAVAILABLE"
    retryable = True
