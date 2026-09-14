"""Workflow 原语：多步骤流程的串行 / 并行与失败降级。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class WorkflowStep(BaseModel):
    """一个流程步骤。"""

    model_config = ConfigDict(extra="forbid")

    step_id: str
    agent_id: Optional[str] = Field(
        default=None, description="该步骤调用的智能体；为空表示纯计算步骤"
    )
    input_map: dict[str, str] = Field(
        default_factory=dict, description="入参映射：本步骤参数名 → 上游输出键"
    )
    output_key: str = Field(description="本步骤结果写入的输出键")
    depends_on: list[str] = Field(default_factory=list, description="依赖的前置 step_id")
    optional: bool = Field(default=False, description="失败时是否允许跳过")


class WorkflowSpec(BaseModel):
    """流程定义。"""

    model_config = ConfigDict(extra="forbid")

    workflow_id: str
    steps: list[WorkflowStep] = Field(default_factory=list)
    failure_policy: Literal["abort", "continue", "degrade"] = "degrade"


class WorkflowResult(BaseModel):
    """流程执行结果。"""

    model_config = ConfigDict(extra="forbid")

    workflow_id: str
    status: Literal["succeeded", "partially_succeeded", "failed"]
    outputs: dict[str, Any] = Field(default_factory=dict)
    failed_steps: list[str] = Field(default_factory=list)


class WorkflowEngine(ABC):
    """流程引擎 Port。"""

    @abstractmethod
    async def run(
        self, spec: WorkflowSpec, inputs: Optional[dict[str, Any]] = None
    ) -> WorkflowResult:
        """执行流程。按 depends_on 拓扑执行，遵守 failure_policy。"""
