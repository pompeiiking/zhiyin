"""工作台聚合服务实现（**骨架**，方法体未实现）。

落位：`business/services/workspace.py` —— 业务编排负责人。
依赖：读侧聚合（Profile / Asset / Memory / Behavior 的 Port）。

读写路径分离（《目标架构设计》§5.5）的读侧：**本类不写任何状态、不发任何事件**。
允许轻微陈旧，允许 `asyncio.gather` 并发聚合 + 部分失败降级；不得在此做写侧重算。
"""

from __future__ import annotations

from zhiyin_business.ports.blackboard import (
    AssetService,
    BehaviorService,
    ConversationMemoryService,
    ProfileService,
)
from zhiyin_business.ports.workspace import StagePanel, WorkspaceService, WorkspaceView

_TODO = "TODO(骨架): WorkspaceService 未实现"


class DefaultWorkspaceService(WorkspaceService):
    """工作台聚合默认实现（骨架）。"""

    IMPLEMENTATION_STATUS = "skeleton"

    def __init__(
        self,
        *,
        profiles: ProfileService,
        assets: AssetService,
        memories: ConversationMemoryService,
        behaviors: BehaviorService,
    ) -> None:
        self._profiles = profiles
        self._assets = assets
        self._memories = memories
        self._behaviors = behaviors

    async def build_view(self, user_id: str) -> WorkspaceView:
        raise NotImplementedError(f"{_TODO}：按 ①-⑤ 聚合成 WorkspaceView（只读，不写状态）")

    async def list_sessions_summary(self, user_id: str) -> list[StagePanel]:
        raise NotImplementedError(f"{_TODO}：列出各任务会话的环节进度")


__all__ = ["DefaultWorkspaceService"]
