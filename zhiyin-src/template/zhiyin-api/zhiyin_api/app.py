"""应用工厂。

第一期约定（R-API-001）：前端启动只请求一次 `/app/bootstrap` 即可渲染首页，
因此这里只做"挂载路由 + 统一错误信封 + 健康检查"，不承载业务装配 ——
具体实现的装配由 `zhiyin-boot.wire_application()` 完成。

⚠️ 接口前缀：**全站唯一收口在 `API_PREFIX`（`/api/v1`）**
-----------------------------------------------------------
版本段只在**这一个地方**拼接：`create_app` 把每个 router 统一挂到 `API_PREFIX` 下。
因此：

1. **Controller 里的路由不要写版本段。** 正确写法是 `@router.get("/app/bootstrap")`，
   最终对外是 `/api/v1/app/bootstrap`；写成 `"/api/v1/app/bootstrap"` 会变成
   `/api/v1/api/v1/app/bootstrap`，前端 404 而 OpenAPI 里看起来"有这条路由"。
2. **不要在别处再拼一次前缀。** 前端 baseURL、vite proxy、反向代理、网关都只做
   "原样转发"，不要再加 `/v1`；需要换版本时只改本文件的 `API_PREFIX` 一处。
3. **OpenAPI 与文档同前缀**（`{prefix}/openapi.json`、`{prefix}/docs`），
   所以 `npm run gen:api` 抓的就是真正对外的地址，不会生成一份对不上的类型。
4. **唯一例外是 `/healthz`**：运维探针不随 API 版本变化，故意留在版本命名空间之外。

该规则由 `tests/test_api_prefix.py` 守卫（路由声明里出现版本段即失败）。

⚠️ 请求上下文：**全站唯一的 trace id 生产者在这里挂载**
--------------------------------------------------------
`RequestContextMiddleware`（`zhiyin_api/context.py`）在此挂载，负责生成/沿用
`X-Trace-Id`、回写响应头、并让 `ApiResponse.trace_id` 有值。
换任何一层都不需要再生成一次 trace id；日志与前端按同一个 id 串联。
"""

from __future__ import annotations

from typing import Any, Iterable, Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from zhiyin_api.controllers import ROUTERS
from zhiyin_api.context import RequestContextMiddleware
from zhiyin_api.dto.common import ApiResponse, ErrorCode
from zhiyin_api.runtime import get_runtime

DEFAULT_TITLE = "职引 API"
DEFAULT_VERSION = "0.1.0"

API_PREFIX = "/api/v1"
"""唯一接口前缀。改版本只改这里，别在路由或前端里再拼一次。"""


def create_app(
    *,
    title: str = DEFAULT_TITLE,
    version: str = DEFAULT_VERSION,
    api_prefix: str = API_PREFIX,
    routers: Optional[Iterable[Any]] = None,
    lifespan: Optional[Any] = None,
) -> FastAPI:
    """构造 ASGI 应用。

    `routers` 可覆盖，便于单测只挂载需要的路由；默认挂载 `controllers.ROUTERS`。
    `api_prefix` 由启动方传入（boot 传 `Settings.api_prefix`），保证"配的值"与
    "实际挂载的值"是同一个；不传时回落到本模块的 `API_PREFIX`。
    """
    app = FastAPI(
        title=title,
        version=version,
        lifespan=lifespan,
        # 文档与 OpenAPI 跟着版本前缀走，前端 gen:api 抓到的就是对外地址。
        docs_url=f"{api_prefix}/docs",
        redoc_url=f"{api_prefix}/redoc",
        openapi_url=f"{api_prefix}/openapi.json",
    )

    for router in routers if routers is not None else ROUTERS:
        app.include_router(router, prefix=api_prefix)

    # trace id 的唯一生成点：任何进入应用的 HTTP 请求都会被包上上下文，
    # 因此信封里的 trace_id 不会是空字符串（守卫见 tests/test_request_context.py）。
    app.add_middleware(RequestContextMiddleware)

    _install_error_handlers(app)
    return app


def _install_error_handlers(app: FastAPI) -> None:
    """统一响应信封（R-API-006）。

    第一期业务服务与 Facade 尚未实现，接口会抛 FacadeNotConfiguredError。
    这里把它和其它未实现能力统一映射为 DEPENDENCY_UNAVAILABLE：
    §6.2 要求"外部能力失败时走默认通过或本地兜底，不中断核心调用链"，
    因此不返回 500，也不静默吞掉 —— 前端按错误码给弱提示。
    """
    from zhiyin_api.facade.facade import FacadeNotConfiguredError

    @app.exception_handler(FacadeNotConfiguredError)
    async def _facade_missing(_: Request, exc: FacadeNotConfiguredError) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content=ApiResponse[None](
                code=ErrorCode.DEPENDENCY_UNAVAILABLE, message=str(exc)
            ).model_dump(mode="json"),
        )

    @app.exception_handler(NotImplementedError)
    async def _not_implemented(_: Request, exc: NotImplementedError) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content=ApiResponse[None](
                code=ErrorCode.DEPENDENCY_UNAVAILABLE,
                message=f"该能力在第一期尚未实现：{exc}",
            ).model_dump(mode="json"),
        )

    @app.exception_handler(LookupError)
    async def _not_found(_: Request, exc: LookupError) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content=ApiResponse[None](
                code=ErrorCode.NOT_FOUND, message=str(exc)
            ).model_dump(mode="json"),
        )

    @app.exception_handler(PermissionError)
    async def _unauthorized(_: Request, exc: PermissionError) -> JSONResponse:
        return JSONResponse(
            status_code=401,
            content=ApiResponse[None](
                code=ErrorCode.UNAUTHORIZED, message=str(exc)
            ).model_dump(mode="json"),
        )

    # 唯一不带版本前缀的端点：运维探针不随 API 版本变化（见模块 docstring 第 4 条）。
    @app.get("/healthz", tags=["ops"], summary="装配健康检查")
    async def healthz() -> dict[str, Any]:
        report = get_runtime()
        # 占位实现（`placeholders` 非空）说明服务在对外提供**虚构内容**，
        # 即使没有 not_wired 也必须报 degraded——否则漏配环境看起来一切正常。
        ok = report.healthy and not report.serves_fabricated_content
        return {"status": "ok" if ok else "degraded", "assembly": report.to_dict()}


__all__ = ["create_app"]
