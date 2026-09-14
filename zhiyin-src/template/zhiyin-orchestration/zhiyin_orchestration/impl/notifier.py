"""通知投递实现。"""

from __future__ import annotations

from zhiyin_data_sdk.gateways.messaging import NotifyGateway
from zhiyin_orchestration.impl._shared import _to_channel
from zhiyin_orchestration.notify import Notifier, NotifyDelivery, NotifyMessage


class GatewayNotifier(Notifier):
    """把通知投递到 NotifyGateway 的实现（R-ORC-006）。"""

    def __init__(self, gateway: NotifyGateway) -> None:
        self._gateway = gateway

    async def push(self, message: NotifyMessage) -> NotifyDelivery:
        result = await self._gateway.push(
            message.user_id,
            title=message.title,
            body=message.body,
            channel=_to_channel(message.channel),
            action=message.action,
            related_task_id=message.related_task_id,
        )
        return NotifyDelivery(
            message_id=result.message_id,
            channel=result.channel.value,
            delivered=result.delivered,
        )


__all__ = ["GatewayNotifier"]
