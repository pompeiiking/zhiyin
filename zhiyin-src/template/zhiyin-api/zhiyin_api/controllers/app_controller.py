"""启动与身份入口（R-API-001 / R-API-008）。

第一期鉴权为"默认通过"：由 Facade 注入的 AuthGateway 返回本地演示用户，
后续替换真实鉴权时本文件不需要改动。
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from zhiyin_api.dto.bootstrap import BootstrapView
from zhiyin_api.dto.common import ApiResponse
from zhiyin_api.facade import get_facade

router = APIRouter(tags=["app"])


@router.get("/app/bootstrap", response_model=ApiResponse[BootstrapView])
async def bootstrap(request: Request) -> ApiResponse[BootstrapView]:
    """启动装配：菜单 / 路由 / 任务入口 / 文案 / 功能开关。

    前端启动只请求一次即可渲染首页。
    """
    facade = get_facade()
    user_id = await facade.resolve_user_id(request)
    return ApiResponse(data=await facade.bootstrap(user_id))
