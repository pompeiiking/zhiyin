"""会话记忆读写与查询（conversation_memory）。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from zhiyin_kernel.blackboard import ConversationMemory


class ConversationMemoryRepository(ABC):
    """会话记忆 Repository。用于跨会话续接与摘要注入提示词。"""

    @abstractmethod
    async def get(self, user_id: str, task_id: str) -> Optional[ConversationMemory]:
        """按用户 + 任务读取会话记忆。"""

    @abstractmethod
    async def upsert(self, memory: ConversationMemory) -> ConversationMemory:
        """写入 / 更新会话记忆。"""

    @abstractmethod
    async def list_by_user(self, user_id: str) -> list[ConversationMemory]:
        """列出该用户全部任务会话记忆，用于左栏会话列表。"""

    @abstractmethod
    async def delete(self, user_id: str, task_id: str) -> None:
        """删除会话记忆。"""
