"""Notifier 原语：统一推送出口。

**契约分工**：本模块是语义契约（推送内容由业务层组织，本层只负责投递）；
通道差异由 zhiyin-data-sdk 的 `NotifyGateway` 承担，第一期落本地消息表 + 日志
（LocalNotify），后续替换 SSE / WS / 短信 / 邮件时业务层不感知。
第一期默认实现见 `zhiyin_orchestration.impl.GatewayNotifier`。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class NotifyMessage(BaseModel):
    """一条待投递的通知。"""

    model_config = ConfigDict(extra="forbid")

    user_id: str
    title: str
    body: str = ""
    channel: str = Field(default="in_app", description="通道标识，取值由业务层给定")
    action: Optional[dict[str, Any]] = Field(
        default=None, description="可点动作，如跳转对话页继续"
    )
    related_task_id: Optional[str] = None
    trace_id: Optional[str] = None


class NotifyDelivery(BaseModel):
    """投递结果。"""

    model_config = ConfigDict(extra="forbid")

    message_id: str
    channel: str
    delivered: bool = False


class Notifier(ABC):
    """通知 Port。"""

    @abstractmethod
    async def push(self, message: NotifyMessage) -> NotifyDelivery:
        """投递通知。"""
