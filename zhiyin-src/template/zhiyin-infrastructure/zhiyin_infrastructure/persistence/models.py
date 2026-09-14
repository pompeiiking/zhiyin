"""ORM 表清单。

本文件先固化「契约 → 表」的映射，DDL 与 ORM 类随后补齐。
表结构必须与 zhiyin_kernel 一一对应，不得出现契约之外的表。

**为什么表清单要写全**：《第一期技术架构文档》§6.2 要求"物理字段可简化，但业务
含义必须与 PRD 对齐"；《分层实现与接口设计》§三 要求"文案、任务、规则、提示词、
页面结构、通知模板等动态资源全部入库"，并明确"第一期可以只读这些表或使用默认数据，
但表结构应提前保留"。此前清单只有 21 张、缺 17+ 张动态资源表，等于把"动态资源入库"
这条验收口径悬空了。

分组：
  A 核心业务表（《第一期技术架构文档》§6.2）
  B 前端动态内容表（《分层实现与接口设计》§4.1，13 张）
  C 后端动态配置与规则表（同文档 §4.2，25 张，与 A 组去重后净增 22 张）

TODO(骨架): 按上表补齐 SQLAlchemy 模型。约束：
- 所有表带 created_at / updated_at；
- profile / asset_version / report / direction_plan / action_plan 带 version 列；
- behavior_log 只允许 INSERT，不提供 UPDATE 路径；
- 动态资源表统一带 code / status / version / sort_order / effective_at / expire_at
  （见《分层实现与接口设计》§3.2 统一配置模式）。

注意：本模块**不得**引用 `zhiyin_business` 的任何模型。日历这类要落库的数据形状
必须定义在 `zhiyin_kernel`，否则基础设施层会反向依赖业务层（§九 验收项 1）。
"""

from __future__ import annotations

# --------------------------------------------------------------------------
# A 核心业务表
# --------------------------------------------------------------------------

CORE_TABLES: dict[str, str] = {
    # 黑板与状态
    "user_account": "用户账号 ← contracts/identity.UserAccount",
    "auth_session": "登录会话 ← contracts/identity.AuthSession",
    "guest_session": "游客临时画像与已采集步骤（登录合并后清除）← contracts/identity.GuestSession",
    "task_session": "任务会话（可拆可续的载体）← contracts/blackboard.TaskSession",
    "profile": "画像主表（version 乐观锁）← contracts/blackboard.Profile",
    "profile_field": "画像字段活状态 ← contracts/blackboard.ProfileField",
    "profile_gap": "画像缺口 ← contracts/blackboard.ProfileGap",
    "conversation_memory": "会话记忆 ← contracts/blackboard.ConversationMemory",
    # 行为与跟踪
    "behavior_log": "行为日志（只追加）← contracts/blackboard.BehaviorLog",
    "track_event": "跟踪时间线 ← contracts/assets.TrackEvent",
    "achievement": "成就（只由行为日志驱动）← contracts/assets.Achievement",
    "key_calendar_node": "关键节点日历 ← contracts/assets.CalendarNode",
    "agent_call_log": "pami Assistant/RAG 调用审计",
    # 资产与版本
    "asset_version": "资产版本与影响面 ← contracts/blackboard.AssetVersion",
    "report": "15 维诊断报告 ← contracts/assets.Report",
    "report_dimension": "报告 15 维明细 ← contracts/assets.ReportDimensionItem",
    "direction_plan": "方向方案（主攻/平行/保底）← contracts/assets.DirectionPlan",
    "action_plan": "行动计划 ← contracts/assets.ActionPlan",
    "action_task": "行动任务 ← contracts/assets.ActionTask",
}

# --------------------------------------------------------------------------
# B 前端动态内容表（13）
# --------------------------------------------------------------------------

FRONTEND_DYNAMIC_TABLES: dict[str, str] = {
    "app_page": "页面定义",
    "app_page_section": "页面区块",
    "app_component": "组件定义",
    "app_component_prop": "组件属性配置",
    "app_route": "前端路由",
    "app_menu": "导航菜单",
    "app_task_entry": "首页任务入口",
    "app_task_option": "任务选项与路由规则",
    "app_copy": "文案",
    "app_copy_bundle": "文案包 / 多语言",
    "app_banner": "横幅与运营位",
    "app_trust_block": "信任背书块",
    "app_faq": "常见问题",
}

# --------------------------------------------------------------------------
# C 后端动态配置与规则表（25，其中 3 张与 A 组同一张表）
# --------------------------------------------------------------------------

BACKEND_DYNAMIC_TABLES: dict[str, str] = {
    "config_group": "配置分组",
    "config_item": "通用配置项",
    "feature_flag": "功能开关（此前硬编码在 Settings.feature_flags，已改为本地 JSON）",
    "enum_dict": "枚举字典",
    "i18n_resource": "多语言资源",
    "agent_registry": "智能体注册表 ← contracts/registry.AgentDescriptor",
    "theory_card": "理论卡 ← contracts/registry.TheoryCard",
    "output_contract": "智能体产出契约 ← contracts/registry.OutputContractSpec",
    "prompt_template": "提示词模板",
    "workflow_template": "工作流模板",
    "decision_rule": "意图/环节决策规则",
    "handoff_rule": "智能体交接规则",
    "event_rule": "事件路由规则",
    "schedule_rule": "主动调度规则",
    "notify_template": "通知模板",
    "knowledge_source": "知识源配置",
    "knowledge_category": "知识分类",
    "embedding_model_config": "嵌入模型配置",
    "vector_namespace_config": "向量命名空间配置",
    "object_bucket_config": "对象存储桶配置",
    "auth_provider_config": "鉴权提供方配置",
    "rate_limit_policy": "限流策略",
    "tenant_config": "租户级配置",
    "agent_app_key_mapping": "职引智能体 → pami 应用 APIKey 映射",
    "service_account_config": "知识库/权限同步 JWT 服务账号配置",
}

# `agent_registry` / `theory_card` / `output_contract` 同时属于 A 组，
# 建表时只建一次（《分层实现与接口设计》§4.2 备注）。
SHARED_WITH_CORE = ("agent_registry", "theory_card", "output_contract")

# 第一期由本地 JSON 承载、尚未建表的动态资源
# （LocalJsonRegistryRepository 与 LocalFeatureFlagStore 已能读，切表只换实现）。
LOCAL_JSON_BACKED = (
    "agent_registry",
    "theory_card",
    "output_contract",
    "app_task_entry",
    "feature_flag",
)

TABLE_INVENTORY: list[str] = sorted(
    set(CORE_TABLES) | set(FRONTEND_DYNAMIC_TABLES) | set(BACKEND_DYNAMIC_TABLES)
)

# 契约 → 表的反向索引，供 Repository 实现与评审对照。
CONTRACT_TO_TABLE: dict[str, str] = {
    value.split("←")[1].strip(): key
    for key, value in CORE_TABLES.items()
    if "←" in value
}

__all__ = [
    "BACKEND_DYNAMIC_TABLES",
    "CONTRACT_TO_TABLE",
    "CORE_TABLES",
    "FRONTEND_DYNAMIC_TABLES",
    "LOCAL_JSON_BACKED",
    "SHARED_WITH_CORE",
    "TABLE_INVENTORY",
]
