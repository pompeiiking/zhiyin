"""核心对话页接口（FR-HOME-002 / FR-CONV / R-API-002 / R-API-003）。

调用链：Controller → Facade → Orchestrator.handle_message
（读黑板 → 环节判定 → 选主理 → 理论链产出 → 行为引导收尾）
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from zhiyin_api.dto.common import ApiResponse
from zhiyin_api.dto.conversation import (
    ConversationHistoryView,
    ConversationTurnView,
    MessageRequest,
    SessionListView,
    TaskEnterRequest,
    TaskSessionView,
)
from zhiyin_api.facade import get_facade

router = APIRouter(tags=["conversation"])


@router.get("/app/sessions", response_model=ApiResponse[SessionListView])
async def list_sessions(request: Request) -> ApiResponse[SessionListView]:
    """左栏会话列表（并行任务会话，按任务/环节命名）。"""
    facade = get_facade()
    user_id = await facade.resolve_user_id(request)
    return ApiResponse(data=await facade.list_sessions(user_id))


@router.post("/app/task/enter", response_model=ApiResponse[TaskSessionView])
async def enter_task(
    request: Request, body: TaskEnterRequest
) -> ApiResponse[TaskSessionView]:
    """从首页任务入口进入微循环。

    编排器判定目标环节与主理；已存在进行中的同一任务时执行"续接"而非重建。
    """
    facade = get_facade()
    user_id = await facade.resolve_user_id(request)
    return ApiResponse(data=await facade.enter_task(user_id, body))


@router.get(
    "/app/conversation/history",
    response_model=ApiResponse[ConversationHistoryView],
)
async def read_conversation_history(
    request: Request, task_id: str
) -> ApiResponse[ConversationHistoryView]:
    """读取某任务会话的既成事实：全部消息 + 所处环节 + 管线卡。

    刷新页面或切换会话时前端据此恢复对话流与环节进度；未知会话（404）与
    不属于当前用户的会话（403）都显式失败，不用空历史冒充成功。
    """
    facade = get_facade()
    user_id = await facade.resolve_user_id(request)
    return ApiResponse(data=await facade.read_conversation_history(user_id, task_id))


@router.post("/app/conversation/message", response_model=ApiResponse[ConversationTurnView])
async def send_message(
    request: Request, body: MessageRequest
) -> ApiResponse[ConversationTurnView]:
    """发送一轮消息，返回最短结论 + 显式告知 + 行为引导 + 管线卡。"""
    facade = get_facade()
    user_id = await facade.resolve_user_id(request)
    return ApiResponse(data=await facade.send_message(user_id, body))
