"""动态资源读取（agent_registry / theory_card / output_contract / task_entry /
policy_params）。

第一期允许实现为本地 JSON / YAML，但接口形状不变，统一标记 TODO(第二期) 接
pami 动态资源表。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from zhiyin_kernel.enums import LoopStage
from zhiyin_kernel.registry import (
    AgentDescriptor,
    OutputContractSpec,
    PolicyParamSet,
    TaskEntrySpec,
    TheoryCard,
)


class RegistryRepository(ABC):
    """动态资源 Repository。"""

    @abstractmethod
    async def get_agent(self, agent_id: str) -> Optional[AgentDescriptor]:
        """读取智能体描述。"""

    @abstractmethod
    async def list_agents(self) -> list[AgentDescriptor]:
        """列出全部智能体。"""

    @abstractmethod
    async def get_theory_card(self, theory_id: str) -> Optional[TheoryCard]:
        """读取理论卡。"""

    @abstractmethod
    async def list_theory_cards(self, theory_ids: Optional[list[str]] = None) -> list[TheoryCard]:
        """批量读取理论卡，用于理论标签展开。"""

    @abstractmethod
    async def get_output_contract(
        self, agent_id: str, stage: LoopStage
    ) -> Optional[OutputContractSpec]:
        """按 `(agent_id, stage)` 读取产出契约。

        查找键是这一对，不是契约 id：一个智能体可以承担多个环节
        （职业顾问同时负责 ②诊断 与 ③决策），按 id 查会表达不出这种情形，
        也会让"哪个契约属于哪个环节"变成隐式约定。实现方必须按该键索引。
        """

    @abstractmethod
    async def list_task_entries(self) -> list[TaskEntrySpec]:
        """读取首页任务入口清单（FR-HOME-001 动态文案）。"""

    @abstractmethod
    async def get_policy_params(self, code: str) -> Optional[PolicyParamSet]:
        """读取业务规则的参数集（阈值 / 冷却期 / 打扰上限等）。

        规则实现在 `zhiyin_business/policies/`，参数一律来自动态资源；
        读不到时实现方返回 None（由调用方决定回落口径），不要静默造默认值。
        """
