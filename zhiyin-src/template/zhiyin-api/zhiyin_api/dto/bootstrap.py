"""启动装配类 DTO（R-API-001）。

/app/bootstrap 一次返回菜单、路由、任务入口、文案与功能开关，
让前端启动只请求一次即可渲染首页——因此任务文案与功能开关变更不需要前端发版。
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from zhiyin_business.published import LoopStage


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


class MenuView(BaseModel):
    """顶层导航项。仅"首页 / 核心对话页 / 智能工作台"三条主线。"""

    model_config = ConfigDict(extra="forbid")

    key: str
    label: str
    route: str
    visible: bool = True


class RouteView(BaseModel):
    """前端路由。"""

    model_config = ConfigDict(extra="forbid")

    path: str
    page_code: str = Field(description="页面锚点口径，如 screen-home / screen-conv")
    require_login: bool = False


class BootstrapView(BaseModel):
    """启动装配视图。"""

    model_config = ConfigDict(extra="forbid")

    app_name: str = "职引"
    menus: list[MenuView] = Field(default_factory=list)
    routes: list[RouteView] = Field(default_factory=list)
    task_entries: list[TaskEntryView] = Field(default_factory=list)
    trust_copy: str = Field(
        default="", description="信任区文案：每步都基于职业咨询成熟方法"
    )
    feature_flags: dict[str, bool] = Field(
        default_factory=dict, description="功能开关：导出/导师/演示等"
    )
    identity: dict[str, str] = Field(
        default_factory=dict, description="当前身份：role / nickname / avatar"
    )
