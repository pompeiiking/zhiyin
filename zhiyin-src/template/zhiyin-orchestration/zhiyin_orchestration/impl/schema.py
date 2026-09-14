"""产出契约的极简 JSON Schema 校验（R-ORC-002）。

只覆盖第一期产出契约会用到的关键字，零外部依赖：
$ref/$defs、type / required / properties / items / enum /
minimum / maximum / minLength / additionalProperties。
遇到不认识的关键字会**忽略而不是误报**，避免"校验器比契约更严格"。
"""

from __future__ import annotations

from typing import Any

_TYPE_MAP: dict[str, tuple[type, ...]] = {
    "object": (dict,),
    "array": (list, tuple),
    "string": (str,),
    "integer": (int,),
    "number": (int, float),
    "boolean": (bool,),
    "null": (type(None),),
}


def validate_schema(schema: dict[str, Any], value: Any, path: str = "$") -> list[str]:
    """校验一个值是否符合给定的 JSON Schema，返回错误列表（空列表 = 合法）。"""
    if not isinstance(schema, dict):
        return []
    return _validate(schema, value, path, defs=schema.get("$defs") or {})


def _validate(
    schema: dict[str, Any],
    value: Any,
    path: str,
    *,
    defs: dict[str, Any],
) -> list[str]:
    errors: list[str] = []

    reference = schema.get("$ref")
    if isinstance(reference, str):
        target = defs.get(reference.rsplit("/", 1)[-1])
        if not isinstance(target, dict):
            return [f"{path}: 无法解析 $ref {reference}"]
        return _validate(target, value, path, defs=defs)

    expected_type = schema.get("type")
    if isinstance(expected_type, str):
        allowed = _TYPE_MAP.get(expected_type)
        if allowed is not None:
            # bool 是 int 的子类，单独挡掉以免 True 通过 integer 校验。
            is_bool_mismatch = expected_type in {"integer", "number"} and isinstance(value, bool)
            if is_bool_mismatch or not isinstance(value, allowed):
                errors.append(f"{path}: 期望 {expected_type}，实际 {type(value).__name__}")
                return errors

    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: 取值不在枚举 {schema['enum']} 内")

    if isinstance(value, dict):
        for key in schema.get("required", []) or []:
            if key not in value:
                errors.append(f"{path}: 缺少必填字段 {key}")
        properties = schema.get("properties") or {}
        for key, sub_schema in properties.items():
            if key in value and isinstance(sub_schema, dict):
                errors.extend(_validate(sub_schema, value[key], f"{path}.{key}", defs=defs))
        if schema.get("additionalProperties") is False:
            for key in value:
                if key not in properties:
                    errors.append(f"{path}: 出现契约外字段 {key}")

    if isinstance(value, (list, tuple)) and isinstance(schema.get("items"), dict):
        for index, item in enumerate(value):
            errors.extend(_validate(schema["items"], item, f"{path}[{index}]", defs=defs))

    if isinstance(value, str) and "minLength" in schema and len(value) < schema["minLength"]:
        errors.append(f"{path}: 长度小于 minLength={schema['minLength']}")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: 小于 minimum={schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path}: 大于 maximum={schema['maximum']}")

    return errors


__all__ = ["validate_schema"]
