"""启动装配类 DTO（R-API-001）。

/app/bootstrap 一次返回菜单、路由、任务入口、文案与功能开关，
让前端启动只请求一次即可渲染首页——因此任务文案与功能开关变更不需要前端发版。

**这里不放任何默认文案。** 本文件是形状定义，不是文案仓库：应用名、定位语、
信任区、演示标注一律来自动态资源（`data/registry/copies.json` 等），
由 `zhiyin_api/dto/mappers.py` 填进来。此前 `app_name` / `trust_copy` 带默认字符串，
等于在代码里留了一份"影子文案"，改了 JSON 也不会生效。
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from zhiyin_kernel.enums import LoopStage


class TaskEntryView(BaseModel):
    """首页任务入口（FR-HOME-001）。文案必须用"用户自己的话"。"""

    model_config = ConfigDict(extra="forbid")

    code: str
    label: str
    target_stage: Optional[LoopStage] = Field(
        default=None, description="为空表示走「直接开聊」，由编排器判定入口"
    )
    lead_agent_name: Optional[str] = Field(default=None, description="开场主理展示名")
    sort_order: int = 0


class AgentTheoryView(BaseModel):
    """智能体持有的理论卡（id + 中文名）。

    只下发 id 与展示名：前端要显示的是"帕森斯 · 了解自我"这类中文名，而注册表里
    `theory_packages` 存的是理论卡 id。**翻译放后端**，否则前端只能硬编码映射，
    或把 `parsons_self` 直接显示给用户。
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str = Field(description="理论中文名，如 帕森斯 · 了解自我")


class AgentView(BaseModel):
    """能力池条目（智能体小队页 / 工作台使用）。

    口径（待决问题 D9）：
    - `stages` 由后端用 `(agent_id, stage)` 逐环节探测产出契约得出，
      **不在注册表里新增字段**，也不由前端猜；
    - `theories` 由后端把理论卡 id 翻成中文名；
    - `no` / `shortName` / `theme` 属纯展示，由前端按顺序与名称派生，不进契约。
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="稳定标识，取值见 AgentRole")
    name: str = Field(description="展示名，如 建档分析师")
    role_summary: str = Field(default="", description="一句话职责")
    stages: list[LoopStage] = Field(
        default_factory=list, description="负责的环节；空表示按需调用、不主理某一段"
    )
    theories: list[AgentTheoryView] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    not_to_do: list[str] = Field(default_factory=list, description="边界：不做什么")


class MenuView(BaseModel):
    """顶层导航项。仅"首页 / 核心对话页 / 智能工作台"三条主线。"""

    model_config = ConfigDict(extra="forbid")

    key: str
    label: str
    route: str
    visible: bool = True
    sort_order: int = 0


class RouteView(BaseModel):
    """前端路由。"""

    model_config = ConfigDict(extra="forbid")

    path: str
    page_code: str = Field(description="页面锚点口径，如 screen-home / screen-conv")
    require_login: bool = False
    sort_order: int = 0


class BannerView(BaseModel):
    """横幅 / 运营位（可上下线、可排序）。"""

    model_config = ConfigDict(extra="forbid")

    code: str
    title: str
    body: str = ""
    action_label: str = ""
    action_route: str = ""


class TrustBlockView(BaseModel):
    """信任背书块（FR-HOME-005）。只讲一条主线，可点开方法论示例。"""

    model_config = ConfigDict(extra="forbid")

    code: str
    title: str
    body: str = ""
    expandable_ref: str = Field(default="", description="可展开内容的引用键，空为纯文本")


class FaqView(BaseModel):
    """常见问题。"""

    model_config = ConfigDict(extra="forbid")

    code: str
    question: str
    answer: str


class BootstrapView(BaseModel):
    """启动装配视图。"""

    model_config = ConfigDict(extra="forbid")

    app_name: str = Field(
        default="", description="应用名，取自动态文案 app.name；为空表示文案包缺失"
    )
    menus: list[MenuView] = Field(default_factory=list)
    routes: list[RouteView] = Field(default_factory=list)
    task_entries: list[TaskEntryView] = Field(default_factory=list)
    copy_bundle: dict[str, str] = Field(
        default_factory=dict,
        description="文案包（key → text），前端按 key 取用，不从后端解析自然语言",
    )
    trust_blocks: list[TrustBlockView] = Field(
        default_factory=list, description="信任区：第一条为主线，其余为可展开示例"
    )
    banners: list[BannerView] = Field(default_factory=list, description="横幅 / 运营位")
    faqs: list[FaqView] = Field(default_factory=list, description="常见问题")
    feature_flags: dict[str, bool] = Field(
        default_factory=dict, description="功能开关：导出/导师/演示等"
    )
    agents: list[AgentView] = Field(
        default_factory=list,
        description="能力池：五位主理的展示名 / 职责 / 负责环节 / 理论 / 工具 / 边界",
    )
    identity: dict[str, str] = Field(
        default_factory=dict, description="当前身份：role / nickname / avatar"
    )
