"""埋点上报 DTO（决策 14：后端派生为主 + 前端上报为辅）。

只有 `data/registry/track_events.json` 里 `channel=frontend` 的纯体验型事件
才允许经 `POST /app/track` 上报；`channel=backend` 的事件由后端行为/接口派生，
不应从这里入站——实现校验时按此拒绝，避免一条事件被记两次或归属错乱。
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class TrackEventRequest(BaseModel):
    """一次前端埋点上报。"""

    model_config = ConfigDict(extra="forbid")

    event: str = Field(description="事件名，来自 data/registry/track_events.json")
    payload: dict[str, Any] = Field(default_factory=dict, description="事件属性")
    client_event_id: Optional[str] = Field(
        default=None, description="前端幂等键，用于去重"
    )


class TrackEventAck(BaseModel):
    """上报确认。第一期只确认接收，不返回处理详情。"""

    model_config = ConfigDict(extra="forbid")

    accepted: bool = True
    event: str


__all__ = ["TrackEventAck", "TrackEventRequest"]
