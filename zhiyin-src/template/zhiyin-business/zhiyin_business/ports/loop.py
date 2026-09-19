"""五环节 Loop 状态机契约（可拆可续）。

可拆可续规则（PRD §3.2）：
- 首次进入或表达迷茫 → 走完整管线；
- 日常可从**任意环节**进入；
- 前序产出自动继承：不重复问、不整篇重生成；
- 环节进度跨会话持久化。

实现要求见 R-BIZ-004 / R-BIZ-005。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from zhiyin_kernel.blackboard import AssetVersion, TaskSession
from zhiyin_kernel.enums import LoopStage
from zhiyin_business.contracts.common import (
    AgentBadge,
    BehaviorEventDraft,
    BehaviorGuide,
    ConversationMessage,
    Disclosure,
)
from zhiyin_business.ports.blackboard import BlackboardView


class EntrySource(str, Enum):
    """进入来源。决定是否需要补跑前序环节。"""

    HOME_TASK = "home_task"      # 首页选任务
    FREE_CHAT = "free_chat"      # 直接开聊，编排器判定
    COACH_PUSH = "coach_push"    # 教练主动发起
    RESUME = "resume"            # 续接历史会话
    MENTOR = "mentor"            # 导师建议触发（P2）


class LoopEntry(BaseModel):
    """一次进入微循环的描述。"""

    model_config = ConfigDict(extra="forbid")

    user_id: str
    task_code: str
    stage: LoopStage = Field(description="本次进入的环节")
    lead_agent: str
    source: EntrySource = EntrySource.HOME_TASK


class LoopContext(BaseModel):
    """环节执行的上下文。

    前序资产通过 assets 自动继承（FR-ORCH-005）：进入 ③ 决策时，画像与报告
    已在上下文中，不需要重跑 ①②。
    """

    model_config = ConfigDict(extra="forbid")

    session: TaskSession
    stage: LoopStage
    lead_agent: str
    blackboard: BlackboardView
    inherited_assets: list[AssetVersion] = Field(
        default_factory=list, description="前序环节留下的资产，自动继承"
    )
    turn_index: int = Field(default=0, description="该会话内的轮次")
    scratch: dict[str, Any] = Field(
        default_factory=dict, description="环节内暂存，不落库"
    )


class LoopResult(BaseModel):
    """一个环节执行一轮的产出。

    注意：环节只产出"契约化的结果 + 要记的行为 + 要更新的资产"，
    真正的落库与事件发布由黑板服务统一完成，保证一致性。
    """

    model_config = ConfigDict(extra="forbid")

    stage: LoopStage
    output: dict[str, Any] = Field(
        description="环节产出契约的序列化结果，运行时必须是 CollectOutput 等之一"
    )
    badge: AgentBadge
    messages: list[ConversationMessage] = Field(default_factory=list)
    disclosure: Optional[Disclosure] = None
    guide: BehaviorGuide
    behavior_events: list[BehaviorEventDraft] = Field(default_factory=list)
    asset_versions: list[AssetVersion] = Field(default_factory=list)
    next_stage: Optional[LoopStage] = Field(
        default=None, description="非空表示本轮结束时需要交接"
    )
    next_stage_reason: str = ""
    model_degraded: bool = Field(
        default=False,
        description=(
            "模型层降级：产出虽然通过了契约校验，但模型自述走了降级"
            "（例如本地占位实现）。**成功路径也必须带上它**——"
            "此前只在失败路径把它塞进 output，成功路径直接丢弃，"
            "于是占位产出会被当真实资产落库且无人知晓"
        ),
    )


class LoopCoordinator(ABC):
    """五环节状态机 Port。

    IO 口径：本 Port 的全部方法都触碰 Repository / 黑板，因此一律是 `async`。
    纯内存的规则计算（如"下一环节是谁"）放在 `policies/` 或模块级纯函数里，
    保持同步、可单测。
    """

    @abstractmethod
    async def start(self, entry: LoopEntry) -> LoopContext:
        """从任意环节开始一次微循环。前序资产自动继承。"""

    @abstractmethod
    async def resume(self, user_id: str, task_id: str) -> LoopContext:
        """续接历史会话，沿用持久化的环节进度（FR-ORCH-005）。"""

    @abstractmethod
    async def run_stage(self, context: LoopContext, user_input: str) -> LoopResult:
        """执行当前环节的一轮。

        职责：调 AgentEngine 拿产出 → 用本环节契约校验 → 组装 LoopResult。
        落库由调用方（Orchestrator）统一完成。
        """

    # 这里原本还有一个 `advance(context, to_stage, lead_agent=None)`：只做
    # `sessions.update_stage` 并返回新上下文。2026-09-19 删除（待决问题 D3），原因：
    #
    # 1. **语义不完整**：一次真正的阶段变更必须同时做四件事——按 `policies/teaming.py`
    #    定主理、落库、写会话记忆、发 `loop_stage_changed`、并组好告知文案。
    #    `advance` 只做其中一件，于是它天然是"落库成功而事件失败"的不自洽入口；
    # 2. **与生产路径重复**：`DefaultOrchestrator._perform_handoff` 本来就直接调
    #    `sessions.update_stage`，两处各写一遍；
    # 3. **没有调用方**：全仓只有两处测试在调它，而冻结 Port 上半职责的方法正是
    #    本项目反复被"看起来有、实际没有"咬到的形态。
    #
    # **阶段变更的唯一入口是 `Orchestrator.handoff(user_id, task_id, to_stage, reason)`**——
    # 它已是冻结公开契约，且语义完整（主理、落库、记忆、事件、告知）。
    # 独立 Worker 或调度器要推进环节时，也走它。

