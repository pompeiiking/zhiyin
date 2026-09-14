"""资产与导出接口（FR-BLOCK-001 / R-API-005）。

资产接口必须返回版本与 diff，前端据此展示"因更新 X，v1→v2 的差异"。
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from zhiyin_api.dto.asset import (
    AssetVersionView,
    ExportRequest,
    ExportResultView,
    ReportFullTextView,
)
from zhiyin_api.dto.common import ApiResponse
from zhiyin_api.facade import get_facade
from zhiyin_kernel.enums import AssetType

router = APIRouter(tags=["asset"])


@router.get(
    "/app/assets/{asset_type}/versions",
    response_model=ApiResponse[list[AssetVersionView]],
)
async def list_asset_versions(
    request: Request, asset_type: AssetType
) -> ApiResponse[list[AssetVersionView]]:
    """资产历史版本列表，含 depends_on 与 diff。"""
    facade = get_facade()
    user_id = await facade.resolve_user_id(request)
    return ApiResponse(data=facade.list_asset_versions(user_id, asset_type))


@router.get("/app/report/full-text", response_model=ApiResponse[ReportFullTextView])
async def get_report_full_text(
    request: Request, version: int | None = None
) -> ApiResponse[ReportFullTextView]:
    """完整报告页正文。只读资产版本，不重新生成。"""
    facade = get_facade()
    user_id = await facade.resolve_user_id(request)
    return ApiResponse(data=facade.get_report_full_text(user_id, version))


@router.post("/app/assets/export", response_model=ApiResponse[ExportResultView])
async def export_asset(
    request: Request, body: ExportRequest
) -> ApiResponse[ExportResultView]:
    """导出资产。第一期仅预留入口，available 恒 False。"""
    facade = get_facade()
    user_id = await facade.resolve_user_id(request)
    return ApiResponse(data=await facade.export_asset(user_id, body))
