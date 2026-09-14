"""动态资源读取（agent_registry / theory_card / output_contract / task_entry）。

第一期允许实现为本地 JSON / YAML，但接口形状不变，统一标记 TODO(第二期) 接
pami 动态资源表。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from zhiyin_kernel.registry import (
    AgentDescriptor,
    OutputContractSpec,
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
    async def get_output_contract(self, contract_id: str) -> Optional[OutputContractSpec]:
        """读取产出契约 spec。"""

    @abstractmethod
    async def list_task_entries(self) -> list[TaskEntrySpec]:
        """读取首页任务入口清单（FR-HOME-001 动态文案）。"""
