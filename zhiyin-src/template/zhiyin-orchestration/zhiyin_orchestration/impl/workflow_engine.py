"""流程引擎实现：按依赖拓扑执行多步骤流程。"""

from __future__ import annotations

from typing import Any, Literal, Optional

from zhiyin_orchestration.agent import AgentRequest
from zhiyin_orchestration.errors import WorkflowFailedError
from zhiyin_orchestration.workflow import (
    WorkflowEngine,
    WorkflowResult,
    WorkflowSpec,
    WorkflowStep,
)


class SequentialWorkflowEngine(WorkflowEngine):
    """按 depends_on 拓扑执行的流程引擎（R-ORC-007）。"""

    def __init__(self, agent_engine) -> None:
        self._agent = agent_engine

    async def run(
        self, spec: WorkflowSpec, inputs: Optional[dict[str, Any]] = None
    ) -> WorkflowResult:
        outputs: dict[str, Any] = dict(inputs or {})
        pending = {step.step_id: step for step in spec.steps}
        done: set[str] = set()
        failed: list[str] = []

        while pending:
            ready = [
                step
                for step in pending.values()
                if all(dep in done for dep in step.depends_on)
            ]
            if not ready:
                unresolved = sorted(pending)
                if spec.failure_policy == "abort":
                    raise WorkflowFailedError(
                        f"流程 {spec.workflow_id} 存在无法满足的依赖：{unresolved}",
                        detail={"workflow_id": spec.workflow_id, "steps": unresolved},
                    )
                failed.extend(unresolved)
                for step_id in unresolved:
                    pending.pop(step_id, None)
                break

            for step in ready:
                pending.pop(step.step_id, None)
                try:
                    outputs[step.output_key] = await self._run_step(step, outputs)
                    done.add(step.step_id)
                except Exception as exc:
                    if not step.optional and spec.failure_policy == "abort":
                        raise WorkflowFailedError(
                            f"流程 {spec.workflow_id} 步骤 {step.step_id} 失败：{exc}",
                            detail={"workflow_id": spec.workflow_id, "step_id": step.step_id},
                            cause=exc,
                        ) from exc
                    failed.append(step.step_id)

        # 状态口径：没有任何失败 = succeeded；全部没跑成 = failed；
        # 有成功也有失败/跳过 = partially_succeeded。
        # 注意"被跳过"也算失败：依赖没满足的步骤不应被算作成功。
        if not failed:
            status: Literal["succeeded", "partially_succeeded", "failed"] = "succeeded"
        elif not done:
            status = "failed"
        else:
            status = "partially_succeeded"
        return WorkflowResult(
            workflow_id=spec.workflow_id,
            status=status,
            outputs=outputs,
            failed_steps=failed,
        )

    async def _run_step(self, step: WorkflowStep, outputs: dict[str, Any]) -> Any:
        mapped = {name: outputs.get(key) for name, key in step.input_map.items()}
        if step.agent_id is None:
            return mapped
        result = await self._agent.invoke(
            AgentRequest(agent_id=step.agent_id, prompt_vars=mapped)
        )
        if not result.valid:
            raise WorkflowFailedError(
                f"步骤 {step.step_id} 产出不合法：{result.errors}",
                detail={"step_id": step.step_id, "errors": result.errors},
            )
        return result.structured


__all__ = ["SequentialWorkflowEngine"]
