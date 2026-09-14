"""请求上下文守卫：trace id 必须有生产者，而且只能有一个。

本轮实测的缺口
--------------
`ApiResponse.trace_id`（R-API-006 统一信封）与前端 `client.ts::ApiError.traceId`
都已把「链路追踪 id」当既有字段使用，M4 门禁的 manual 项也写着
「trace_id 端到端贯通（BFF 生成、日志与事件携带）」，但**全仓没有任何地方生成它**：
字段恒为空字符串，前端拿到空值、日志串不起一次请求。

这与上一轮修掉的 H1/H2/H3 同类——**契约齐备、链路上没有出口**。区别是它更隐蔽
（空字符串不报错，只让人误以为"这次没产生 trace"），所以这里用断言钉住三件事：

1. 有唯一生产者（`zhiyin_api/context.py`）且信封的默认值链到它；
2. 每个 HTTP 响应都带回 `X-Trace-Id`，上游合法值被沿用、不合法值被替换；
3. 业务 / 编排 / 数据 / 基础设施各层不得自己造 trace id（否则又会出现第二个口径）。
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from zhiyin_api.app import create_app
from zhiyin_api.context import (
    TRACE_HEADER,
    current_trace_id,
    normalize_trace_id,
)
from zhiyin_api.dto.common import ApiResponse

TEMPLATE_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIRS = (
    "zhiyin-api",
    "zhiyin-business",
    "zhiyin-orchestration",
    "zhiyin-data-sdk",
    "zhiyin-infrastructure",
)
CONTEXT_MODULE = TEMPLATE_ROOT / "zhiyin-api" / "zhiyin_api" / "context.py"
HEX32 = re.compile(r"^[0-9a-f]{32}$")


def test_envelope_trace_id_is_filled_by_the_context() -> None:
    """信封的 trace_id 必须由请求上下文兜底，而不是恒为空字符串。

    这条守的是"唯一生产者"：Controller / Facade / Mapper 都不该传 trace id，
    所以默认值必须来自 `current_trace_id`。断言默认值工厂的身份，而不是它的结果——
    否则任何返回空字符串的实现都能蒙混过关。
    """
    field = ApiResponse.model_fields["trace_id"]
    assert field.default_factory is current_trace_id, (
        "ApiResponse.trace_id 的默认值必须链到 zhiyin_api.context.current_trace_id；"
        "改成常量或手传参数都会让 trace 在生产链路上再次断掉"
    )
    # 不在请求上下文里时取不到值，返回空字符串（不抛异常，便于单测直接构造信封）
    assert current_trace_id() == ""


def test_no_other_layer_invents_trace_ids() -> None:
    """trace id 的生成与绑定只允许在 `api/context.py`（app.py 只挂载它）。

    生成点一旦多于一处，"日志里的 id"与"响应头里的 id"就会是两套，
    排查时最贵的那种不一致（都非空、但都不是同一个请求）。

    注意断言的是**生成/绑定函数**的调用点，不是 `uuid4()`：业务层用 uuid 造实体 id
    是正当的，禁掉它会把这条守卫变成噪音（那正是守卫失去价值的方式）。
    """
    allowed = {CONTEXT_MODULE, TEMPLATE_ROOT / "zhiyin-api" / "zhiyin_api" / "app.py"}
    offenders: list[str] = []
    for package in PACKAGE_DIRS:
        for source in sorted((TEMPLATE_ROOT / package).rglob("*.py")):
            if source in allowed:
                continue
            text = source.read_text(encoding="utf-8")
            for symbol in ("new_trace_id(", "bind_trace_id(", "normalize_trace_id("):
                if symbol in text:
                    offenders.append(f"{source.relative_to(TEMPLATE_ROOT)}: {symbol}")
    assert not offenders, (
        "trace id 只允许在 api/context.py 生成、由 app.py 挂载中间件，"
        "以下位置越权：\n  " + "\n  ".join(offenders)
    )
    assert CONTEXT_MODULE.is_file(), "context.py 是 trace id 的唯一生产者，不能删除"

    # 全仓只有一个 trace id 的 ContextVar 定义处（第二条上下文会出现两套口径）
    holders = [
        str(source.relative_to(TEMPLATE_ROOT))
        for package in PACKAGE_DIRS
        for source in sorted((TEMPLATE_ROOT / package).rglob("*.py"))
        if re.search(
            r"ContextVar\([^)]*[\"']zhiyin_trace_id[\"']",
            source.read_text(encoding="utf-8"),
        )
    ]
    assert holders == [str(CONTEXT_MODULE.relative_to(TEMPLATE_ROOT))], (
        f"trace id 的上下文只能定义一处，实际：{holders}"
    )


@pytest.mark.parametrize(
    "raw",
    [None, "", "   ", "bad id!", "a" * 65, "含中文的追踪号"],
)
def test_malformed_upstream_trace_id_is_replaced(raw: str | None) -> None:
    """上游值不合法时重新生成，不原样透传（否则响应头与日志会被污染）。"""
    assert HEX32.fullmatch(normalize_trace_id(raw))


def test_legal_upstream_trace_id_is_reused() -> None:
    """网关 / 前端 / 压测传入的合法 id 必须沿用，否则调用链会在 BFF 断成两截。"""
    assert normalize_trace_id("trace-ABC_123") == "trace-ABC_123"


def test_healthz_carries_a_fresh_trace_header_per_request() -> None:
    with TestClient(create_app()) as client:
        first = client.get("/healthz")
        second = client.get("/healthz")

    assert first.status_code == 200
    first_id = first.headers[TRACE_HEADER]
    second_id = second.headers[TRACE_HEADER]
    assert HEX32.fullmatch(first_id), f"响应头 {TRACE_HEADER} 必须是 32 位 hex"
    assert first_id != second_id, "两次请求应是两个 trace id，不能复用同一条"


def test_upstream_trace_id_is_echoed() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/healthz", headers={TRACE_HEADER: "caller-supplied-id"})
    assert response.headers[TRACE_HEADER] == "caller-supplied-id"


def test_error_envelope_reuses_the_response_trace_id() -> None:
    """降级响应（未装配 Facade → 503）也必须带回同一个 trace id。

    这条是端到端口径的机械落点：**响应头里的 id == 信封里的 id**。
    第一期所有业务接口都走这条降级路径，所以它同时代表了联调期的排查能力。
    """
    with TestClient(create_app()) as client:
        response = client.get("/api/v1/app/bootstrap")

    assert response.status_code == 503
    body = response.json()
    assert body["trace_id"], "信封 trace_id 不得为空——这正是本轮修掉的静默空值"
    assert body["trace_id"] == response.headers[TRACE_HEADER]
