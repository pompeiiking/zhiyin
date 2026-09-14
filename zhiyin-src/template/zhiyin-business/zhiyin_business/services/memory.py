"""会话记忆服务实现（**骨架**，方法体未实现）。

落位：`business/services/memory.py` —— 业务编排负责人。
依赖：`ConversationMemoryRepository`（无事件依赖，纯读写）。

本类是"可拆可续"的载体维护者：跨会话续接靠它把摘要与环节进度带回来。
摘要生成口径（多长、包含哪些字段）属业务规则，定稿前不要在此内联。
"""

from __future__ import annotations

from typing import Optional

from zhiyin_business.ports.blackboard import ConversationMemoryService
from zhiyin_data_sdk.repositories import ConversationMemoryRepository
from zhiyin_kernel.blackboard import ConversationMemory
from zhiyin_kernel.enums import LoopStage

_TODO = "TODO(骨架): ConversationMemoryService 未实现"


class DefaultConversationMemoryService(ConversationMemoryService):
    """会话记忆服务默认实现（骨架）。"""

    IMPLEMENTATION_STATUS = "skeleton"

    def __init__(self, memories: ConversationMemoryRepository) -> None:
        self._memories = memories

    async def get(self, user_id: str, task_id: str) -> Optional[ConversationMemory]:
        raise NotImplementedError(f"{_TODO}：读会话记忆")

    async def upsert(
        self,
        user_id: str,
        task_id: str,
        *,
        loop_stage: LoopStage,
        lead_agent: str,
        summary_delta: str = "",
    ) -> ConversationMemory:
        raise NotImplementedError(f"{_TODO}：写入 / 追加摘要片段")

    async def list_by_user(self, user_id: str) -> list[ConversationMemory]:
        raise NotImplementedError(f"{_TODO}：列出全部任务会话记忆（左栏会话列表）")


__all__ = ["DefaultConversationMemoryService"]
