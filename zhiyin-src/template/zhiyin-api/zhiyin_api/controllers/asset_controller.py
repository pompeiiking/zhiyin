"""资产与导出接口（FR-BLOCK-001 / R-API-005）。

资产接口必须返回版本与 diff，前端据此展示"因更新 X，v1→v2 的差异"。

写操作接口（FR-DIAG-004 / FR-DECIDE-003 / FR-ACT-004 / FR-BLOCK-002）
------------------------------------------------------------------
报告页读到产出之后，用户还要能做四件事：认领差距、选定方向、勾掉任务、把节点放进
日历。这四条各自独立成一个端点，是因为它们的**前置条件、幂等性与业务后果都不同**
（认领只标注不换版本、选方案有互斥与重选语义、勾任务有阶段归属、日历是 planner/coach
共同读写的对象），拼在一个批量端点里会让"哪一步成功了"变得不可判定。
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from zhiyin_api.dto.asset import (
    AssetVersionView,
    CalendarNodeRequest,
    CalendarNodeView,
    DecisionSelectionRequest,
    DecisionSelectionView,
    ExportRequest,
    ExportResultView,
    GapClaimRequest,
    GapClaimView,
    ReportFullTextView,
    TaskDoneRequest,
    TaskDoneView,
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
    return ApiResponse(data=await facade.list_asset_versions(user_id, asset_type))


@router.get("/app/report/full-text", response_model=ApiResponse[ReportFullTextView])
async def get_report_full_text(
    request: Request, version: int | None = None
) -> ApiResponse[ReportFullTextView]:
    """完整报告页正文。只读资产版本，不重新生成。"""
    facade = get_facade()
    user_id = await facade.resolve_user_id(request)
    return ApiResponse(data=await facade.get_report_full_text(user_id, version))


@router.post("/app/assets/export", response_model=ApiResponse[ExportResultView])
async def export_asset(
    request: Request, body: ExportRequest
) -> ApiResponse[ExportResultView]:
    """导出资产。第一期仅预留入口，available 恒 False。"""
    facade = get_facade()
    user_id = await facade.resolve_user_id(request)
    return ApiResponse(data=await facade.export_asset(user_id, body))


@router.post(
    "/app/assets/gap-claims",
    response_model=ApiResponse[GapClaimView],
)
async def claim_gap(
    request: Request, body: GapClaimRequest
) -> ApiResponse[GapClaimView]:
    """认领报告中的一条差距（FR-DIAG-004）。幂等，不产生新版本。"""
    facade = get_facade()
    user_id = await facade.resolve_user_id(request)
    return ApiResponse(data=await facade.claim_gap(user_id, body))


@router.post(
    "/app/assets/decision-selection",
    response_model=ApiResponse[DecisionSelectionView],
)
async def select_direction_plan(
    request: Request, body: DecisionSelectionRequest
) -> ApiResponse[DecisionSelectionView]:
    """选定方向方案（FR-DECIDE-003）。重选走同一端点，旧方案自动取消选中。"""
    facade = get_facade()
    user_id = await facade.resolve_user_id(request)
    return ApiResponse(data=await facade.select_direction_plan(user_id, body))


@router.post("/app/tasks/done", response_model=ApiResponse[TaskDoneView])
async def mark_task_done(
    request: Request, body: TaskDoneRequest
) -> ApiResponse[TaskDoneView]:
    """勾掉一条行动任务（FR-ACT-004）。幂等。"""
    facade = get_facade()
    user_id = await facade.resolve_user_id(request)
    return ApiResponse(data=await facade.mark_task_done(user_id, body))


@router.post("/app/calendar/nodes", response_model=ApiResponse[CalendarNodeView])
async def write_calendar_node(
    request: Request, body: CalendarNodeRequest
) -> ApiResponse[CalendarNodeView]:
    """把关键节点写入日历（FR-BLOCK-002）。规划师写入、教练读取。"""
    facade = get_facade()
    user_id = await facade.resolve_user_id(request)
    return ApiResponse(data=await facade.write_calendar_node(user_id, body))
