"""动态资源读侧契约（业务侧）。

为什么需要这一层（与 `ports/identity.py` 同源的理由）
--------------------------------------------------
`/app/bootstrap`（R-API-001）要一次返回**菜单 / 路由 / 任务入口 / 文案 / 功能开关**，
这些数据全在动态资源里；而取数的契约（`RegistryRepository` / `FeatureFlagGateway`）
定义在 `zhiyin_data_sdk`，**api 层按依赖矩阵不许 import data_sdk**
（`tests/test_architecture.py::test_api_does_not_touch_data_sdk`）。

于是只有两条路：

1. 放宽矩阵，让 api 直连动态资源契约——把已收口的跨层直连重新打开；
2. 由业务层包出一个读侧 Port，api 只面对业务抽象 ← **已采用**

这与 `IdentityService` 是同一类问题的同一个解法：**api 与数据访问契约之间的通道
只允许在业务层开**。两条通道的分工是——

- `IdentityService`：我是谁（认证主体 → 本地用户记录补齐，属业务行为）；
- `RegistryService`：页面长什么样（原文/开关读取，不做组装、不写业务判断）。

边界（很重要）
-------------
- 本 Port **只读**，不提供任何写入动态资源的入口——配置写入属运营后台，不在本期范围；
- 本 Port **不组装页面视图**：返回的是内核形状（`MenuSpec` / `CopySpec` / …）。
  "拼成 `BootstrapView`"是 BFF 的翻译工作，放在 `zhiyin_api/dto/mappers.py`；
- 本 Port **不认识 HTTP**，也不认识任何 data_sdk 类型（参数与返回值必须能在
  `zhiyin_kernel` 里找到）。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from zhiyin_kernel.dynamic_content import (
    BannerSpec,
    FaqSpec,
    MenuSpec,
    RouteSpec,
    TrustBlockSpec,
)
from zhiyin_kernel.registry import AgentCapability, AgentDescriptor, TaskEntrySpec
from zhiyin_kernel.registry import TrackEventSpec


class RegistryService(ABC):
    """动态资源读侧服务（BFF 取数入口）。"""

    # ---------- 首页任务入口 ----------

    @abstractmethod
    async def list_task_entries(self) -> list[TaskEntrySpec]:
        """首页任务入口清单（FR-HOME-001），已按 sort_order 排序。

        文案与路由规则由动态资源下发，前端不得硬编码任务卡。
        """

    @abstractmethod
    async def get_agent(self, agent_id: str) -> Optional[AgentDescriptor]:
        """读取智能体描述，用于把 `agent_id` 翻成展示名。

        用途举例：任务入口的"开场主理"、左栏会话的主理名、顶栏徽章。
        取不到时调用方按"展示名回落为 agent_id"处理，**不要**静默编名字。
        """

    @abstractmethod
    async def list_agent_capabilities(self) -> list[AgentCapability]:
        """能力池（PRD §3.3 / FR-HOME）——读侧一次解析好，BFF 直接下发。

        存在理由：智能体小队页与工作台要展示"有哪几位主理、各自负责哪几段、依据
        哪些理论"，而这三样在注册表里的形态不同——智能体是定义；**负责的环节没有
        字段**，要由 `(agent_id, stage)` 的产出契约反推；理论包存的是 id，要翻成
        中文名。此前前端把整套定义**硬编码**在 `stores/agents.ts`，与注册表人工同步
        （违反《AGENTS.md》§8，且漂移无守卫可拦，待决问题 D9）。

        为什么是"一个聚合方法"而不是"`list_agents` + `list_theory_cards` + 让调用方
        自己拼"：反推环节、翻译理论名都是读侧翻译工作，散到 BFF 就会有两份口径；
        而且 `RegistryRepository` **没有** `list_output_contracts`，逐环节探测
        （`get_output_contract`）这件事只该发生在一处。
        """

    # ---------- 前端页面内容 ----------

    @abstractmethod
    async def list_menus(self) -> list[MenuSpec]:
        """顶层导航菜单（已过滤停用项、已排序）。"""

    @abstractmethod
    async def list_routes(self) -> list[RouteSpec]:
        """前端路由表。"""

    @abstractmethod
    async def get_copy_bundle(self, bundle: str = "zh-CN") -> dict[str, str]:
        """按文案包读取文案（key → text）。未配置时返回空 dict，由调用方决定回落。"""

    @abstractmethod
    async def list_banners(self) -> list[BannerSpec]:
        """横幅 / 运营位。"""

    @abstractmethod
    async def list_trust_blocks(self) -> list[TrustBlockSpec]:
        """信任背书块（首页"每步都基于职业咨询成熟方法"）。"""

    @abstractmethod
    async def list_faqs(self) -> list[FaqSpec]:
        """常见问题。"""

    # ---------- 埋点事件归属 ----------

    @abstractmethod
    async def list_track_events(self) -> list[TrackEventSpec]:
        """埋点事件归属表（后端派生 / 前端上报）。

        供 Facade 的 `POST /app/track` 实现校验：只有 `channel=frontend` 的事件
        允许从客户端上报，`channel=backend` 的应由后端自行派生。
        """

    # ---------- 功能开关 ----------

    @abstractmethod
    async def feature_flags(self) -> dict[str, bool]:
        """功能开关快照（报告全文 / 导出 / 日历 / 成就 / 导师 / 演示）。

        前端按开关决定功能块可见性；本方法只读，不改开关。
        """


__all__ = ["RegistryService"]
