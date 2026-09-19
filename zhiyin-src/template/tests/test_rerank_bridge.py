"""rerank 转换桥的协议测试（D7 ③）。

这条链路存在的原因：平台只会 `POST <endpointUrl>/rerank`，而两家上游都没有该
路径。所以本文件锁的是**协议翻译**：请求侧宽容解析、响应侧翻回 OpenAI 风格，
以及缺字段/上游异常时**显式失败**（不能静默返回空排序——那会让调用方以为
"没有相关文档"）。
"""

from __future__ import annotations

import httpx
import pytest

from zhiyin_data_sdk.errors import UnavailableError, ValidationError
from zhiyin_infrastructure.pami.rerank_bridge import (
    DASHSCOPE_RERANK_PATH,
    from_dashscope_response,
    parse_rerank_request,
    rerank,
    to_dashscope_payload,
)

DASHSCOPE_REPLY = {
    "output": {
        "results": [
            {"index": 1, "relevance_score": 0.91},
            {"index": 0, "relevance_score": 0.12},
        ]
    },
    "usage": {"total_tokens": 25},
}


def test_openai_style_request_is_parsed() -> None:
    translation = parse_rerank_request(
        {"model": "gte-rerank-v2", "query": "职业兴趣", "documents": ["甲", "乙"]},
        default_model="fallback",
    )
    assert translation.query == "职业兴趣"
    assert translation.documents == ["甲", "乙"]
    assert translation.model == "gte-rerank-v2"


def test_request_shape_is_tolerant_because_it_has_no_frozen_schema() -> None:
    """形状没有被冻结（平台文档就是 `additionalProperties: true`），所以要宽容。

    同时接受 `input.*`（DashScope 风格）、`texts`/`passages` 别名、以及
    `{"text": ...}` 形式的文档元素——否则真实调用方换个字段名就整条链路不通。
    """
    translation = parse_rerank_request(
        {
            "input": {"query": "三叶草", "documents": [{"text": "甲"}, "乙"]},
            "top_n": 1,
        },
        default_model="fallback",
    )
    assert translation.query == "三叶草"
    assert translation.documents == ["甲", "乙"]
    assert translation.model == "fallback"
    assert translation.top_n == 1

    alias = parse_rerank_request(
        {"question": "问题", "passages": ["丙"]}, default_model="fallback"
    )
    assert alias.query == "问题"
    assert alias.documents == ["丙"]


def test_missing_query_or_documents_fails_loudly() -> None:
    """缺字段必须显式失败：静默返回空排序 = 假装"没有相关文档"。"""
    with pytest.raises(ValidationError, match="query"):
        parse_rerank_request({"documents": ["甲"]}, default_model="m")
    with pytest.raises(ValidationError, match="documents"):
        parse_rerank_request({"query": "问"}, default_model="m")


def test_payload_and_response_are_translated_both_ways() -> None:
    translation = parse_rerank_request(
        {"query": "职业兴趣", "documents": ["甲", "乙"]}, default_model="m"
    )
    payload = to_dashscope_payload(translation)
    assert payload["input"] == {"query": "职业兴趣", "documents": ["甲", "乙"]}
    assert payload["parameters"]["return_documents"] is True

    result = from_dashscope_response(DASHSCOPE_REPLY, translation)
    assert [item["index"] for item in result["results"]] == [1, 0]
    assert result["results"][0]["relevance_score"] == pytest.approx(0.91)
    # 上游没回文档正文时用入参文档补齐，保证调用方拿得到原文
    assert result["results"][0]["document"]["text"] == "乙"


def test_out_of_range_index_falls_back_to_rank() -> None:
    """上游给了越界索引时不该整次作废——用结果序号兜底，并保留可排序的分数。"""
    translation = parse_rerank_request(
        {"query": "问", "documents": ["甲"]}, default_model="m"
    )
    result = from_dashscope_response(
        {"output": {"results": [{"index": 99, "relevance_score": 0.5}]}}, translation
    )
    assert result["results"][0]["index"] == 0


def test_upstream_without_results_is_unavailable_not_empty() -> None:
    translation = parse_rerank_request(
        {"query": "问", "documents": ["甲"]}, default_model="m"
    )
    with pytest.raises(UnavailableError, match="results"):
        from_dashscope_response({"output": {}}, translation)


@pytest.mark.asyncio
async def test_rerank_calls_the_native_path_and_returns_openai_style() -> None:
    """完整翻译：请求打到 DashScope **原生**路径，响应翻回 OpenAI 风格。"""
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["auth"] = request.headers.get("Authorization")
        import json

        seen["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(200, json=DASHSCOPE_REPLY)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await rerank(
            {"query": "职业兴趣", "documents": ["甲", "乙"]},
            base_url="https://dashscope.aliyuncs.com",
            api_key="test-key",
            default_model="gte-rerank-v2",
            client=client,
        )

    assert seen["path"] == DASHSCOPE_RERANK_PATH
    assert seen["auth"] == "Bearer test-key"
    assert seen["body"]["model"] == "gte-rerank-v2"
    assert len(result["results"]) == 2


@pytest.mark.asyncio
async def test_upstream_http_error_is_reported_as_unavailable() -> None:
    """上游报错要变成明确的"不可用"，不能吞成一个空 results。"""

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="not found")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(UnavailableError, match="HTTP 404"):
            await rerank(
                {"query": "问", "documents": ["甲"]},
                base_url="https://example.invalid",
                api_key="k",
                default_model="m",
                client=client,
            )


def test_http_shell_routes_and_maps_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """HTTP 外壳：路由、健康检查与错误码。

    翻译层已有独立用例；这里只锁我自己写的进程外壳——地址对不对、失败时给的是
    4xx/5xx 而不是假成功，以及**形状不对时把它收到的字段名回给调用方**（排障时正是
    靠这个对齐协议，而平台文档对该请求体就是 `additionalProperties: true`）。
    """
    import json as _json
    import threading
    import urllib.error
    import urllib.request

    from zhiyin_boot import rerank_bridge as server_module

    async def fake_rerank(body, *, base_url, api_key, default_model, timeout_s=30.0):
        # 刻意模仿真实解析层的两个行为：缺 query 报 ValidationError、上游失败报
        # UnavailableError——这样测的是**外壳的错误映射**，而不是重新测一遍翻译。
        if "query" not in body:
            raise ValidationError("rerank 请求缺少 query", detail={"keys": sorted(body)})
        if body.get("query") == "boom":
            raise UnavailableError("上游炸了")
        return {"results": [{"index": 0, "relevance_score": 0.9}]}

    monkeypatch.setattr(server_module, "rerank", fake_rerank)
    server = server_module._Server(
        ("127.0.0.1", 0),
        {"upstream_url": "https://x", "api_key": "k", "model": "m", "port": "0",
         "path": "/rerank"},
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        with urllib.request.urlopen(base + "/healthz", timeout=5) as resp:
            health = _json.loads(resp.read().decode())
        assert health["status"] == "ok"

        def post(path: str, payload: dict) -> tuple[int, dict]:
            request = urllib.request.Request(
                base + path,
                data=_json.dumps(payload).encode(),
                method="POST",
                headers={"Content-Type": "application/json"},
            )
            try:
                with urllib.request.urlopen(request, timeout=5) as resp:
                    return resp.status, _json.loads(resp.read().decode())
            except urllib.error.HTTPError as exc:
                return exc.code, _json.loads(exc.read().decode())

        status, body = post("/rerank", {"query": "职业兴趣", "documents": ["甲"]})
        assert status == 200 and body["results"][0]["relevance_score"] == 0.9

        # 形状不对 → 422，并把收到的字段名带回去（不含内容）
        status, body = post("/rerank", {"wrong": 1})
        assert status == 422 and body["received_keys"] == ["wrong"]

        # 上游失败 → 502，不能假装成功
        status, _ = post("/rerank", {"query": "boom", "documents": ["甲"]})
        assert status == 502

        # 其它路径 → 404
        status, _ = post("/nope", {"query": "x", "documents": ["甲"]})
        assert status == 404
    finally:
        server.shutdown()
        server.server_close()
