"""API 通用 DTO：统一响应与错误码（R-API-006）。"""

from __future__ import annotations

from enum import IntEnum
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ErrorCode(IntEnum):
    """统一错误码。前端据此提示，不解析后端文案。"""

    OK = 0
    INVALID_PARAM = 1001          # 参数校验失败
    NOT_FOUND = 1002              # 资源不存在
    CONFLICT = 1003               # 版本冲突 / 重复提交
    UNAUTHORIZED = 1004           # 未登录，需触发登录拦截
    GUEST_LIMIT = 1005            # 游客采集超过 2 问
    STAGE_UNCERTAIN = 1006        # 环节判定不确定，已回落澄清追问
    DEPENDENCY_UNAVAILABLE = 1007 # 模型 / 知识库不可用（已降级）
    INTERNAL = 1999


class ApiResponse(BaseModel, Generic[T]):
    """统一响应信封。

    对应 Wanwu 平台的 code == 0 成功口径，便于前端统一拦截。
    """

    model_config = ConfigDict(extra="forbid")

    code: ErrorCode = ErrorCode.OK
    message: str = "ok"
    data: Optional[T] = None
    trace_id: str = Field(default="", description="链路追踪 id，日志排查用")
