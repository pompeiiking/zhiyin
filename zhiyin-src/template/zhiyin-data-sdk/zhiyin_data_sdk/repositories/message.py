"""对话消息读写契约。

消息只追加：对话流是用户与主理之间的既成事实，历史必须如实可读，
因此这里不提供修改与删除路径（与行为日志同一口径）。
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from zhiyin_kernel.blackboard import ConversationMessage


class ConversationMessageRepository(ABC):
    """按任务会话保存与读取对话消息。"""

    @abstractmethod
    async def append(self, task_id: str, message: ConversationMessage) -> ConversationMessage:
        """追加一条消息，返回落库后的形状（`created_at` 由实现补齐）。"""

    @abstractmethod
    async def list_by_task(self, task_id: str) -> list[ConversationMessage]:
        """按时间正序返回某个任务会话的全部消息（最早的在前）。"""
