"""会话记忆服务实现。

落位：`business/services/memory.py`；第一期排期实现工位：后端-2（数据访问负责人）。
依赖：`ConversationMemoryRepository`（无事件依赖，纯读写）。

本类是"可拆可续"的载体维护者：跨会话续接靠它把摘要与环节进度带回来。
摘要生成口径（多长、包含哪些字段）属业务规则，定稿前不要在此内联。
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from zhiyin_business.ports.blackboard import ConversationMemoryService
from zhiyin_data_sdk.repositories import ConversationMemoryRepository
from zhiyin_kernel.blackboard import ConversationMemory
from zhiyin_kernel.enums import LoopStage

class DefaultConversationMemoryService(ConversationMemoryService):
    """会话记忆服务默认实现。"""

    IMPLEMENTATION_STATUS = "wired"

    def __init__(
        self,
        memories: ConversationMemoryRepository,
        *,
        max_summary_chars: int = 2_000,
    ) -> None:
        if max_summary_chars <= 0:
            raise ValueError("max_summary_chars 必须为正数")
        self._memories = memories
        self._max_summary_chars = max_summary_chars

    async def get(self, user_id: str, task_id: str) -> Optional[ConversationMemory]:
        return await self._memories.get(user_id, task_id)

    async def upsert(
        self,
        user_id: str,
        task_id: str,
        *,
        loop_stage: LoopStage,
        lead_agent: str,
        summary_delta: str = "",
    ) -> ConversationMemory:
        current = await self._memories.get(user_id, task_id)
        summary = current.summary if current is not None else ""
        delta = summary_delta.strip()
        # Orchestrator 传入的是“本轮已确认摘要”，这里负责稳定追加、去重与限长，
        # 避免把同一轮重试或完整聊天原文无限复制进长期记忆。
        fragments = [item for item in summary.splitlines() if item.strip()]
        if delta and (not fragments or fragments[-1] != delta):
            fragments.append(delta)
        summary = self._trim_summary(fragments)

        memory = ConversationMemory(
            id=current.id if current is not None else f"mem_{uuid4().hex[:12]}",
            user_id=user_id,
            task_id=task_id,
            loop_stage=loop_stage,
            lead_agent=lead_agent,
            summary=summary,
            last_active_at=datetime.now(timezone.utc),
        )
        return await self._memories.upsert(memory)

    async def list_by_user(self, user_id: str) -> list[ConversationMemory]:
        return await self._memories.list_by_user(user_id)

    def _trim_summary(self, fragments: list[str]) -> str:
        kept: list[str] = []
        size = 0
        for fragment in reversed(fragments):
            separator = 1 if kept else 0
            if size + separator + len(fragment) > self._max_summary_chars:
                if not kept:
                    kept.append(fragment[-self._max_summary_chars :])
                break
            kept.append(fragment)
            size += separator + len(fragment)
        return "\n".join(reversed(kept))


__all__ = ["DefaultConversationMemoryService"]
