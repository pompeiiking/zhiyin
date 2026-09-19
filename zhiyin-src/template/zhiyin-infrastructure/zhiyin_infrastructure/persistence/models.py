"""M3 关系数据库 ORM 与完整表清单。

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

已落地的运行时聚合表由本模块的 SQLAlchemy 模型声明；其余动态资源表仍由
``TABLE_INVENTORY`` 固化名称并通过后续迁移逐步规范化。约束：
- 所有表带 created_at / updated_at；
- profile / asset_version / report / direction_plan / action_plan 带 version 列；
- behavior_log 只允许 INSERT，不提供 UPDATE 路径；
- 动态资源表统一带 code / status / version / sort_order / effective_at / expire_at
  （见《分层实现与接口设计》§3.2 统一配置模式）。

注意：本模块**不得**引用 `zhiyin_business` 的任何模型。日历这类要落库的数据形状
必须定义在 `zhiyin_kernel`，否则基础设施层会反向依赖业务层（§九 验收项 1）。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """职引关系库统一元数据。"""


class ProfileRow(Base):
    __tablename__ = "profile"

    user_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    profile_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class BehaviorLogRow(Base):
    __tablename__ = "behavior_log"

    sequence: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    __table_args__ = (Index("ix_behavior_user_time", "user_id", "occurred_at"),)


class ConversationMemoryRow(Base):
    __tablename__ = "conversation_memory"

    user_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    task_key: Mapped[str] = mapped_column(String(128), primary_key=True, default="")
    memory_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    last_active_at: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class ConversationMessageRow(Base):
    """对话消息（只追加）。按任务会话读历史时用 (task_id, created_at) 正序。

    `created_at` 存 ISO 字符串（与 `conversation_memory.last_active_at` 同一理由）：
    字符串在 UTC 统一格式下可直接按字典序排序，避免不同驱动返回裸 datetime 时
    出现带时区与不带时区混比的错误。
    """

    __tablename__ = "conversation_message"

    sequence: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    task_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[str] = mapped_column(String(40), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    __table_args__ = (Index("ix_conversation_message_task_time", "task_id", "created_at"),)


class AssetVersionRow(Base):
    __tablename__ = "asset_version"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    asset_type: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "asset_type", "version", name="uq_asset_version"),
        Index("ix_asset_latest", "user_id", "asset_type", "version"),
    )


class AssetContentRow(Base):
    __tablename__ = "asset_content"

    user_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    content_type: Mapped[str] = mapped_column(String(64), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    payload: Mapped[Any] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ReportHistoryRow(Base):
    __tablename__ = "report"

    user_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    # report_id 标识同一份报告资产，可跨版本复用；历史唯一键是 (user_id, version)。
    report_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class TaskSessionRow(Base):
    __tablename__ = "task_session"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    task_code: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class RegistryResourceRow(Base):
    __tablename__ = "registry_resource"

    kind: Mapped[str] = mapped_column(String(64), primary_key=True)
    resource_key: Mapped[str] = mapped_column(String(255), primary_key=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="enabled")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    bundle: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class UserAccountRow(Base):
    __tablename__ = "user_account"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    phone: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class AuthSessionRow(Base):
    __tablename__ = "auth_session"

    token: Mapped[str] = mapped_column(String(512), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class EmbedTaskRow(Base):
    __tablename__ = "embed_task"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    namespace: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    source_id: Mapped[str] = mapped_column(String(255), nullable=False)
    model: Mapped[str] = mapped_column(String(255), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    operation: Mapped[str] = mapped_column(String(16), nullable=False, default="upsert")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_retry_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_error: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "namespace", "source_id", "model", "content_hash", "operation",
            name="uq_embed_task_idempotency",
        ),
    )


class RetrievalLogRow(Base):
    __tablename__ = "retrieval_log"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    org_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    namespace: Mapped[str] = mapped_column(String(32), nullable=False)
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    top_k: Mapped[int] = mapped_column(Integer, nullable=False)
    source_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    degraded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    degraded_reason: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    """降级**原因**，让审计能区分"通道故障"与"命中被权威门挡掉"（D13 残留）。

    为什么单独一列而不是塞进 `degraded` 布尔：这两件事的处置动作不同——
    前者去查通道/平台，后者去查权威表有没有内容。只有布尔值时运维只能靠"有没有
    通道故障"反推，实测中确实卡过一次（真实对话里检索恒 0，查不出原因）。
    取值：`""`（未降级）/ `channels`（通道故障）/ `authority_drop`（命中被权威门丢）/
    `channels+authority_drop`（两者同时）。
    """
    query_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RetrievalDocumentRow(Base):
    """RAG 文档权威元数据与正文；向量库只保存可重建的检索副本。"""

    __tablename__ = "retrieval_document"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    namespace: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    source_id: Mapped[str] = mapped_column(String(255), nullable=False)
    org_id: Mapped[str] = mapped_column(String(128), nullable=False, default="", index=True)
    user_id: Mapped[str] = mapped_column(String(128), nullable=False, default="", index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="enabled")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    title: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str] = mapped_column(String(2048), nullable=False, default="")
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    effective_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expire_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "namespace", "source_id", "version", name="uq_retrieval_document_version"
        ),
        Index("ix_retrieval_document_scope", "namespace", "status", "org_id", "user_id"),
    )

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
    "conversation_message": "对话消息（只追加）← contracts/blackboard.ConversationMessage",
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
    "asset_content": "资产当前态聚合（报告/方向/行动计划正文）",
    "registry_resource": "动态资源统一读模型（由明确 kind 隔离）",
    "embed_task": "向量同步任务、重试与幂等记账",
    "retrieval_document": "RAG 权威文档、版本、权限、状态与时效回源",
    "retrieval_log": "检索通道、耗时和降级审计（只存查询哈希）",
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
    "AssetContentRow",
    "AssetVersionRow",
    "AuthSessionRow",
    "BACKEND_DYNAMIC_TABLES",
    "Base",
    "BehaviorLogRow",
    "CONTRACT_TO_TABLE",
    "ConversationMemoryRow",
    "ConversationMessageRow",
    "CORE_TABLES",
    "EmbedTaskRow",
    "FRONTEND_DYNAMIC_TABLES",
    "LOCAL_JSON_BACKED",
    "ProfileRow",
    "RegistryResourceRow",
    "ReportHistoryRow",
    "RetrievalLogRow",
    "RetrievalDocumentRow",
    "SHARED_WITH_CORE",
    "TABLE_INVENTORY",
    "TaskSessionRow",
    "UserAccountRow",
]
