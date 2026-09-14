"""智能体引擎实现：调用 LLM，返回前完成产出契约校验。"""

from __future__ import annotations

from zhiyin_data_sdk.gateways.ai import LLMGateway, LLMMessage
from zhiyin_orchestration.agent import AgentEngine, AgentRequest, AgentResult
from zhiyin_orchestration.errors import ContractViolationError
from zhiyin_orchestration.impl._shared import _render_prompt
from zhiyin_orchestration.impl.schema import validate_schema


class ContractAgentEngine(AgentEngine):
    """智能体引擎：调用 LLMGateway，返回前完成产出契约校验（R-ORC-002）。

    非法结构以 valid=False + errors 返回，由调用方决定降级或重试；
    调用方要求强一致时把 raise_on_violation 置为 True 会抛
    ContractViolationError，保证非法结构不进入业务层。
    """

    def __init__(
        self,
        llm: LLMGateway,
        *,
        temperature: float = 0.2,
        timeout_s: float = 60.0,
        raise_on_violation: bool = False,
        system_prompt: str = "",
    ) -> None:
        self._llm = llm
        self._temperature = temperature
        self._timeout_s = timeout_s
        self._raise_on_violation = raise_on_violation
        self._system_prompt = system_prompt

    async def invoke(self, request: AgentRequest) -> AgentResult:
        messages = self._build_messages(request)
        try:
            completion = await self._llm.chat(
                messages,
                json_schema=request.output_schema,
                temperature=self._temperature,
                timeout_s=self._timeout_s,
            )
        except Exception as exc:  # 模型不可用不阻断核心链路（R-SDK-008）
            return AgentResult(
                agent_id=request.agent_id,
                valid=False,
                degraded=True,
                errors=[f"模型调用失败：{exc}"],
            )

        if completion.structured is None:
            return AgentResult(
                agent_id=request.agent_id,
                raw_text=completion.text,
                model=completion.model,
                valid=False,
                degraded=completion.degraded,
                errors=["模型未返回结构化产出"],
            )

        errors: list[str] = []
        if request.output_schema:
            errors = validate_schema(request.output_schema, completion.structured)
        if errors and self._raise_on_violation:
            raise ContractViolationError(
                f"智能体 {request.agent_id} 产出不符合契约",
                detail={"errors": errors, "trace_id": request.trace_id},
            )

        return AgentResult(
            agent_id=request.agent_id,
            structured=completion.structured,
            raw_text=completion.text,
            model=completion.model,
            valid=not errors,
            errors=errors,
            degraded=completion.degraded,
        )

    def _build_messages(self, request: AgentRequest) -> list[LLMMessage]:
        messages: list[LLMMessage] = []
        if self._system_prompt:
            messages.append(LLMMessage(role="system", content=self._system_prompt))
        if request.prompt_vars or request.blackboard:
            messages.append(
                LLMMessage(
                    role="user",
                    content=_render_prompt(request.prompt_vars, request.blackboard),
                )
            )
        if not messages:
            messages.append(LLMMessage(role="user", content=""))
        return messages


__all__ = ["ContractAgentEngine"]
