"""编排层异常。"""

from __future__ import annotations

from typing import Any, Optional


class OrchestrationError(Exception):
    """编排层异常基类。"""

    code = "ORCHESTRATION_ERROR"

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


class ContractViolationError(OrchestrationError):
    """产出不符合契约（R-ORC-002）。非法结构不允许进入业务层。"""

    code = "CONTRACT_VIOLATION"


class WorkflowFailedError(OrchestrationError):
    """流程执行失败。"""

    code = "WORKFLOW_FAILED"


class StateConflictError(OrchestrationError):
    """共享状态版本冲突（R-ORC-005）。"""

    code = "STATE_CONFLICT"
