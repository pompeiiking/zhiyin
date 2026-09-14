"""动态资源契约。

对应《职引技术架构-分层详细设计》§八：智能体、理论卡、产出契约、任务入口
均入库为动态资源，可在不发布代码的情况下修改。

第一期允许把动态资源退化为本地 YAML / JSON 常量，但模型形状必须保持一致，
并统一标记 TODO。
"""

from __future__ import annotations

from typing import Any, Literal, Optional

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

    **唯一键是 `(agent_id, stage)`，不是 `id`。**
    原因：一个智能体可以承担多个环节（如职业顾问同时负责 ②诊断 与 ③决策），
    契约天然是"某智能体在某环节的产出"。此前把契约 id 挂在
    `AgentDescriptor.output_contract_id` 上，是"一个智能体一个契约"的 1:1 假设，
    直接导致 `oc_decide` 成为无人引用的孤儿契约——一旦有人按说明把 JSON Schema
    填进去，③决策就会拿②诊断的契约去校验。改为一对 (agent_id, stage) 后，
    该假设不成立即无法表达，从形状上消除这个缺陷。

    `id` 保留为稳定标识（日志与溯源用），但**不得**用于查找。
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="稳定标识，仅用于日志与溯源，不用于查找")
    agent_id: str = Field(description="唯一键的一部分：产出该契约的智能体")
    stage: LoopStage = Field(description="唯一键的一部分：该契约所属环节")
    model_ref: str = Field(description="业务层契约模型的全限定名")
    json_schema: dict[str, Any] = Field(
        default_factory=dict, description="通用校验用 JSON Schema"
    )

    @property
    def key(self) -> tuple[str, str]:
        """查找键。实现方与守卫统一用它，避免各自拼键。"""
        return (self.agent_id, self.stage.value)


class AgentDescriptor(BaseModel):
    """智能体注册表条目（agent_registry）。

    理论包 / 工具 / 调用场合 / 边界全部配置化，对应 PRD §3.3 能力池定义。

    注意：这里**没有** `output_contract_id`。产出契约按 `(agent_id, stage)` 查，
    由 `OutputContractSpec` 持有；智能体不再声明"我拥有哪个契约"，因为一个智能体
    可以拥有多个环节的契约，单一字段无法表达。
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="稳定标识，取值见 AgentRole")
    name: str = Field(description="展示名，如 建档分析师")
    role_summary: str = Field(default="", description="一句话职责，用于显式告知")
    theory_packages: list[str] = Field(default_factory=list, description="拥有的理论卡 id")
    tools: list[str] = Field(default_factory=list, description="可用知识 / 工具")
    call_scenarios: list[str] = Field(default_factory=list, description="被调用的场合")
    not_to_do: list[str] = Field(default_factory=list, description="明确不做")
    status: AgentRuntimeStatus = AgentRuntimeStatus.ENABLED


class PolicyParamSet(BaseModel):
    """业务规则的**参数集**（动态资源）。

    业务规则本身是代码（`zhiyin_business/policies/`），但规则的**参数**
    （停滞阈值、冷却期、打扰上限、置信度阈值……）必须来自动态资源，不得写死。
    本类只承载"一个规则 code 对应一组参数"，**不解释参数含义**——含义由规则实现
    与文档约定，避免内核承载业务语义。

    `status` 用来如实表达定稿程度：`draft` 表示参数仍在业务评审中，
    实现者不得把它当成已确认口径。
    """

    model_config = ConfigDict(extra="forbid")

    code: str = Field(description="规则 code，如 intervention")
    value: dict[str, Any] = Field(default_factory=dict, description="参数键值对")
    status: Literal["draft", "confirmed"] = Field(
        default="draft", description="draft=待业务定稿；confirmed=已定稿"
    )
    note: str = Field(default="", description="为什么是这些值 / 还缺什么")


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


class TrackEventSpec(BaseModel):
    """埋点事件归属（动态资源，PRD §十一）。

    决策 14：**后端派生为主 + 前端上报为辅**。`channel=backend` 的事件由后端
    行为/接口推导，不进 `POST /app/track`；`channel=frontend` 的是纯体验型事件
    （点开告知、查看报告、比较方案、进入工作台等），由前端上报。
    """

    model_config = ConfigDict(extra="forbid")

    code: str = Field(description="事件名，PRD §十一 事件表的唯一键")
    channel: Literal["frontend", "backend"] = Field(
        description="frontend=前端上报；backend=后端派生，不接收入站上报"
    )
    note: str = Field(default="", description="触发时机与口径说明")
