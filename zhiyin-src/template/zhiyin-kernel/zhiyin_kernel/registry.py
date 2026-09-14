"""动态资源契约。

对应《职引技术架构-分层详细设计》§八：智能体、理论卡、产出契约、任务入口
均入库为动态资源，可在不发布代码的情况下修改。

第一期允许把动态资源退化为本地 YAML / JSON 常量，但模型形状必须保持一致，
并统一标记 TODO。
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from zhiyin_kernel.enums import (
    AgentRuntimeStatus,
    LoopStage,
)


class TheoryCard(BaseModel):
    """理论卡。智能体气泡上的理论标签点开后展示的内容。"""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str = Field(description="理论名，如 霍兰德 RIASEC")
    school: str = Field(default="", description="所属流派 / 出处")
    summary: str = Field(default="", description="给用户看的通俗说明")
    product_usage: str = Field(default="", description="在本产品里怎么被用")


class OutputContractSpec(BaseModel):
    """智能体产出契约。

    业务层持有 Pydantic 模型（zhiyin_business.contracts），编排层只持有本 spec
    并做通用校验，从而保证"编排层不含业务语义"（R-ORC-001）。
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    agent_id: str
    stage: LoopStage
    model_ref: str = Field(description="业务层契约模型的全限定名")
    json_schema: dict[str, Any] = Field(
        default_factory=dict, description="通用校验用 JSON Schema"
    )


class AgentDescriptor(BaseModel):
    """智能体注册表条目（agent_registry）。

    理论包 / 工具 / 调用场合 / 边界全部配置化，对应 PRD §3.3 能力池定义。
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="稳定标识，取值见 AgentRole")
    name: str = Field(description="展示名，如 建档分析师")
    role_summary: str = Field(default="", description="一句话职责，用于显式告知")
    theory_packages: list[str] = Field(default_factory=list, description="拥有的理论卡 id")
    tools: list[str] = Field(default_factory=list, description="可用知识 / 工具")
    call_scenarios: list[str] = Field(default_factory=list, description="被调用的场合")
    not_to_do: list[str] = Field(default_factory=list, description="明确不做")
    output_contract_id: Optional[str] = None
    status: AgentRuntimeStatus = AgentRuntimeStatus.ENABLED


class TaskEntrySpec(BaseModel):
    """首页任务入口（动态资源，FR-HOME-001）。"""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(description="任务 code，前端点击后回传")
    label: str = Field(description="用用户自己的话写的任务文案")
    target_stage: Optional[LoopStage] = Field(
        default=None, description="为空表示走编排器意图识别（直接开聊）"
    )
    lead_agent: Optional[str] = Field(default=None, description="该入口的默认主理")
    sort_order: int = 0
