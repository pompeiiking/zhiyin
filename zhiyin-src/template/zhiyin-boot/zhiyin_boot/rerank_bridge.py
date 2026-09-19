"""rerank 转换桥的进程入口（D7 ③）。

平台只会 `POST <endpointUrl>/rerank`，而两家上游都没有这个路径——本进程把该协议
翻译成上游原生 rerank，供平台侧注册的 rerank 模型指向。协议翻译本身在
`zhiyin_infrastructure.pami.rerank_bridge`（可单测），这里只做 HTTP 外壳。

用法：:

    python -m zhiyin_boot rerank-bridge            # 默认 0.0.0.0:8100

    POST /rerank    OpenAI 风格 rerank 请求 → OpenAI 风格 results
    GET  /healthz   存活检查

为什么用标准库 `http.server` 而不是再加一个 Web 框架：这条链路只是个协议转换器，
不承载业务、不暴露给公网、也不需要中间件栈；少一个依赖少一处维护面。

**不打印请求内容**：只打印字段名、文档条数与耗时——排障需要的是"形状对不对"，
而 query / 文档正文属于业务内容，不该进日志（《AGENTS.md》§10）。
密钥只从环境变量读，不打印。
"""

from __future__ import annotations

import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from zhiyin_data_sdk.errors import ValidationError
from zhiyin_infrastructure.pami.rerank_bridge import rerank

DEFAULT_PORT = 8100
DEFAULT_MODEL = "gte-rerank-v2"
MAX_BODY_BYTES = 2 * 1024 * 1024


def _config() -> dict[str, str]:
    return {
        "upstream_url": os.environ.get("ZHIYIN_RERANK_UPSTREAM_URL", "").strip()
        or "https://dashscope.aliyuncs.com",
        "api_key": os.environ.get("ZHIYIN_RERANK_UPSTREAM_API_KEY", "").strip(),
        "model": os.environ.get("ZHIYIN_RERANK_MODEL", "").strip() or DEFAULT_MODEL,
        "port": os.environ.get("ZHIYIN_RERANK_PORT", "").strip() or str(DEFAULT_PORT),
        "path": os.environ.get("ZHIYIN_RERANK_PATH", "").strip() or "/rerank",
    }


class _Handler(BaseHTTPRequestHandler):
    server_version = "zhiyin-rerank-bridge"

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        """默认访问日志会把路径打出来；这里保持静默，改由我们自己按需打印。"""
        return

    def _send(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler 的命名约定
        if self.path.rstrip("/") in ("/healthz", ""):
            config = self._server_config()
            self._send(
                200,
                {
                    "status": "ok",
                    "upstream_configured": bool(config["upstream_url"]),
                    "key_configured": bool(config["api_key"]),
                    "model": config["model"],
                },
            )
            return
        self._send(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        config = self._server_config()
        if self.path.rstrip("/") != config["path"]:
            self._send(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0 or length > MAX_BODY_BYTES:
            self._send(400, {"error": "invalid body length"})
            return
        try:
            body = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send(400, {"error": "body must be json"})
            return
        if not isinstance(body, dict):
            self._send(400, {"error": "body must be a json object"})
            return

        started = time.perf_counter()
        try:
            import asyncio

            result = asyncio.run(
                rerank(
                    body,
                    base_url=config["upstream_url"],
                    api_key=config["api_key"],
                    default_model=config["model"],
                )
            )
        except ValidationError as exc:
            # 形状不对 → 4xx，并把**字段名**回给调用方，便于对齐协议（不含内容）
            print(
                f"[rerank-bridge] 请求形状不合法 keys={sorted(body.keys())} err={exc}",
                flush=True,
            )
            self._send(422, {"error": str(exc), "received_keys": sorted(body.keys())})
            return
        except Exception as exc:  # noqa: BLE001 - 任何上游/配置问题都要如实回报
            print(
                f"[rerank-bridge] 上游调用失败 type={type(exc).__name__}",
                flush=True,
            )
            self._send(502, {"error": f"{type(exc).__name__}: {exc}"})
            return

        elapsed = int((time.perf_counter() - started) * 1000)
        print(
            f"[rerank-bridge] ok keys={sorted(body.keys())} "
            f"results={len(result.get('results', []))} {elapsed}ms",
            flush=True,
        )
        self._send(200, result)

    def _server_config(self) -> dict[str, str]:
        return self.server.config  # type: ignore[attr-defined]


class _Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address: tuple[str, int], config: dict[str, str]) -> None:
        super().__init__(address, _Handler)
        self.config = config


def main(host: str = "0.0.0.0", port: int | None = None) -> int:
    config = _config()
    listen_port = port or int(config["port"])
    server = _Server((host, listen_port), config)
    print(
        f"[rerank-bridge] listening on {host}:{listen_port} "
        f"path={config['path']} model={config['model']} "
        f"upstream_configured={bool(config['upstream_url'])} "
        f"key_configured={bool(config['api_key'])}",
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:  # pragma: no cover - 手动停止
        pass
    finally:
        server.server_close()
    return 0


__all__ = ["main"]
