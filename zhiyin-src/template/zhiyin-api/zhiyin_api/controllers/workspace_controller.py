"""智能工作台接口（FR-WB / R-API-004）。

按 ①-⑤ 聚合返回活资产，不做实时对话。
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from zhiyin_api.dto.common import ApiResponse
from zhiyin_api.dto.workspace import WorkspacePageView
from zhiyin_api.facade import get_facade

router = APIRouter(tags=["workspace"])


@router.get("/app/workspace", response_model=ApiResponse[WorkspacePageView])
async def get_workspace(request: Request) -> ApiResponse[WorkspacePageView]:
    """工作台聚合视图：画像 / 报告 / 方案 / 计划 / 跟踪 + 功能块。

    进入工作台属于持久化行为，游客在此处被登录拦截（PRD §5.3）。
    """
    facade = get_facade()
    user_id = await facade.resolve_user_id(request)
    return ApiResponse(data=await facade.get_workspace(user_id))
