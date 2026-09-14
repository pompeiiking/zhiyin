"""应用工厂。

第一期约定（R-API-001）：前端启动只请求一次 `/app/bootstrap` 即可渲染首页，
因此这里只做"挂载路由 + 统一错误信封 + 健康检查"，不承载业务装配 ——
具体实现的装配由 `zhiyin-boot.wire_application()` 完成。
"""

from __future__ import annotations

from typing import Any, Iterable, Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from zhiyin_api.controllers import ROUTERS
from zhiyin_api.dto.common import ApiResponse, ErrorCode
from zhiyin_api.runtime import get_runtime

DEFAULT_TITLE = "职引 API"
DEFAULT_VERSION = "0.1.0"


def create_app(
    *,
    title: str = DEFAULT_TITLE,
    version: str = DEFAULT_VERSION,
    routers: Optional[Iterable[Any]] = None,
    lifespan: Optional[Any] = None,
) -> FastAPI:
    """构造 ASGI 应用。

    `routers` 可覆盖，便于单测只挂载需要的路由；默认挂载 `controllers.ROUTERS`。
    """
    app = FastAPI(title=title, version=version, lifespan=lifespan)

    for router in routers if routers is not None else ROUTERS:
        app.include_router(router)

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

    @app.get("/healthz", tags=["ops"], summary="装配健康检查")
    async def healthz() -> dict[str, Any]:
        report = get_runtime()
        return {"status": "ok" if report.healthy else "degraded", "assembly": report.to_dict()}


__all__ = ["create_app"]
