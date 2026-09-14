"""埋点上报接口（决策 14：前端通道只负责纯体验型事件）。

调用链：Controller → Facade.track_event（校验事件归属 + 落库口径待实现）。
本文件只接参数、包信封，不写任何事件归属判断。
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from zhiyin_api.dto.common import ApiResponse
from zhiyin_api.dto.track import TrackEventAck, TrackEventRequest
from zhiyin_api.facade import get_facade

router = APIRouter(tags=["track"])


@router.post("/app/track", response_model=ApiResponse[TrackEventAck])
async def track_event(
    request: Request, body: TrackEventRequest
) -> ApiResponse[TrackEventAck]:
    """前端上报一条埋点事件。"""
    facade = get_facade()
    user_id = await facade.resolve_user_id(request)
    return ApiResponse(data=await facade.track_event(user_id, body))


__all__ = ["router"]
