"""本地 / Mock 模型调用（LocalOrMockLLM）。

行为约定：
- 设置了 ZHIYIN_LLM_PROVIDER / KEY 时走真实模型（TODO，见 §十替换点）；
- 否则**按传入的 json_schema 合成一份结构合法的固定结果**，保证五环节链路
  能端到端跑通、产出契约校验能通过。

这是"Mock 先行"的落点：链路上所有下游在模型未接入时也能开发与联调。
合成器刻意做成**schema 驱动**而不是按环节返回硬编码 JSON —— 后者会在产出契约
变更时静默失效，前者永远跟契约同步。

⚠️ 部署环境不装配本类：`ZHIYIN_USE_PAMI_LLM=1` 时 `build_gateways` 会用
   `PamiLLMGateway` 覆盖它。本类保留为**本地/测试实现**。

⚠️ 未收口的风险：本类没有声明 `IMPLEMENTATION_STATUS`，装配报告会按兜底逻辑把它
   报成 `wired`；它只在 `LLMResult.degraded=True` 里自述降级，而该标记目前没有
   消费方。也就是说**漏配 `ZHIYIN_USE_PAMI_LLM` 的环境，占位产出不会被门禁、
   装配报告或界面任何一处拦住**。改法与取舍见
   docs/数据全链路/04-实施与验收/职引-待决问题与改法选项-v1.0.md（D1）——
   在拍板前不要自行改状态或加标注。
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Optional

from zhiyin_data_sdk.gateways.ai import LLMGateway, LLMMessage, LLMResult

_PLACEHOLDER_TEXT = "（第一期 Mock 产出，未接真实模型）"
"""占位串单点定义。仅由本地合成实现产出；部署环境走 PAMI 真实模型，不会生成它。"""


def synthesize_from_schema(schema: Optional[dict[str, Any]]) -> Any:
    """按 JSON Schema 合成一份满足必填与类型要求的占位数据。

    支持：$ref/$defs、anyOf（优先非 null 分支）、type、enum、required、
    properties、items、minimum/maximum、minLength。
    不可识别的结构返回 None，由调用方兜底。
    """
    if not isinstance(schema, dict):
        return None

    defs = schema.get("$defs") or {}

    def build(node: Any) -> Any:
        if not isinstance(node, dict):
            return None

        reference = node.get("$ref")
        if isinstance(reference, str):
            return build(defs.get(reference.rsplit("/", 1)[-1]))

        branches = node.get("anyOf") or node.get("oneOf")
        if isinstance(branches, list) and branches:
            non_null = [
                item
                for item in branches
                if not (isinstance(item, dict) and item.get("type") == "null")
            ]
            return build(non_null[0] if non_null else branches[0])

        if "enum" in node and node["enum"]:
            return node["enum"][0]

        if "const" in node:
            return node["const"]

        kind = node.get("type")
        if isinstance(kind, list):
            kind = next((item for item in kind if item != "null"), None)

        if kind == "object" or (kind is None and "properties" in node):
            result: dict[str, Any] = {}
            properties = node.get("properties") or {}
            required = set(node.get("required", []) or [])
            for key, sub in properties.items():
                if not isinstance(sub, dict):
                    continue
                # 必填一定产出；可空的可选字段（如 Disclosure | None）跳过 ——
                # 否则 Mock 会凭空造出"换主理告知"这类本不该出现的内容。
                if key not in required and _is_nullable(sub):
                    continue
                result[key] = build(sub)
            return result

        if kind == "array":
            return [build(node.get("items", {}))]

        if kind == "string":
            if node.get("format") == "date-time":
                return datetime.now(timezone.utc).isoformat()
            minimum_length = int(node.get("minLength") or 0)
            text = _PLACEHOLDER_TEXT
            while len(text) < minimum_length:
                text += "…"
            return text

        if kind == "integer":
            return int(node.get("minimum", 0))
        if kind == "number":
            return float(node.get("minimum", 0.0))
        if kind == "boolean":
            return False
        if kind == "null":
            return None
        return None

    return build(schema)


def _is_nullable(node: dict[str, Any]) -> bool:
    """判断一个字段 schema 是否允许 null。"""
    if node.get("type") == "null":
        return True
    if isinstance(node.get("type"), list) and "null" in node["type"]:
        return True
    for key in ("anyOf", "oneOf"):
        branches = node.get(key)
        if isinstance(branches, list) and any(
            isinstance(item, dict) and item.get("type") == "null" for item in branches
        ):
            return True
    return False


class LocalOrMockLLM(LLMGateway):
    """有模型用模型，没有模型用固定结果。"""

    def __init__(
        self, model: str = "local-mock", provider_env: str = "ZHIYIN_LLM_PROVIDER"
    ) -> None:
        self._model = model
        self._provider = os.getenv(provider_env, "").strip()

    @property
    def is_mock(self) -> bool:
        """当前是否为 Mock 模式。链路上的日志与 UI 应据此标注。"""
        return not self._provider

    async def chat(
        self,
        messages: list[LLMMessage],
        *,
        json_schema: Optional[dict[str, Any]] = None,
        temperature: float = 0.2,
        timeout_s: float = 60.0,
    ) -> LLMResult:
        if not self.is_mock:
            # TODO(替换点)：接真实模型（pami Assistant / 第三方）。约定：
            # - json_schema 非空时必须要求结构化输出；
            # - 失败时返回 degraded=True 的降级结果，不向上抛异常。
            raise NotImplementedError(
                "TODO(骨架): 真实模型分支尚未实现；如需 Mock，请清空 "
                f"ZHIYIN_LLM_PROVIDER（当前值：{self._provider}）"
            )

        structured = synthesize_from_schema(json_schema) if json_schema else None
        return LLMResult(
            text=(
                json.dumps(structured, ensure_ascii=False)
                if structured is not None
                else _PLACEHOLDER_TEXT
            ),
            structured=structured if isinstance(structured, dict) else None,
            model=f"{self._model}:schema-synth",
            usage={"mock": True},
            degraded=True,
        )


__all__ = ["LocalOrMockLLM", "synthesize_from_schema"]
