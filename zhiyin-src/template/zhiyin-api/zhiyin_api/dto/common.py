"""API 通用 DTO：统一响应与错误码（R-API-006）。

`trace_id` 由 `zhiyin_api.context` 的请求上下文兜底填充：Controller 与 Facade
都不需要传它，也不允许自己生成（生成点只有 `create_app` 挂载的中间件一处）。
这样"契约里有 trace_id、链路上没人生产"这类静默空值不可能再出现。
"""

from __future__ import annotations

from enum import IntEnum
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from zhiyin_api.context import current_trace_id

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
    trace_id: str = Field(
        default_factory=current_trace_id,
        description="链路追踪 id，由 BFF 生成并回写 X-Trace-Id 响应头；日志排查用",
    )
