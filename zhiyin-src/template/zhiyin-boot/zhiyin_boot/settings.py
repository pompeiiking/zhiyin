"""启动配置。

第一期全部走环境变量，不引入配置中心。
"""

from __future__ import annotations

import os
from dataclasses import dataclass


def _env(key: str, default: str = "") -> str:
    return os.getenv(key, default).strip()


def _env_bool(key: str, default: bool = False) -> bool:
    raw = _env(key)
    if not raw:
        return default
    return raw.lower() in {"1", "true", "yes", "on"}


@dataclass
class Settings:
    """运行配置。"""

    # ---------- 应用 ----------
    app_name: str = "职引"
    env: str = "local"                     # local / dev / prod
    api_prefix: str = "/api/v1"

    # ---------- 数据库 ----------
    database_url: str = ""                 # 为空则使用内存实现
    db_echo: bool = False

    # ---------- 能力开关：决定装配 local 还是 pami ----------
    use_pami_llm: bool = False
    use_pami_knowledge: bool = False
    use_pami_auth: bool = False
    use_mysql: bool = False

    # ---------- pami 接入 ----------
    pami_base_url: str = ""
    pami_api_key: str = ""
    pami_jwt_secret: str = ""

    # ---------- 本地实现参数 ----------
    local_data_dir: str = "data"
    local_object_dir: str = "data/objects"
    local_registry_dir: str = "data/registry"
    local_knowledge_dir: str = "data/knowledge"

    # ---------- 调度 ----------
    # 只放**运行节奏**（多久扫一次），不放**规则参数**（停几天算停滞）。
    # 规则参数走动态资源：data/registry/policy_params.json（见 PolicyParamSet）。
    stall_check_interval_s: float = 3600.0
    # Worker 轮询间隔。同进程部署时每个 Worker 按该间隔跑一轮；独立部署
    # （python -m zhiyin_boot worker <name>）时同样使用这个值。
    worker_interval_s: float = 60.0

    # ---------- 功能开关 ----------
    # 注意：功能开关属于**动态资源**（《分层实现与接口设计》§3.1），
    # 不在这里存值，而是由 LocalFeatureFlagStore 读 data/registry/feature_flags.json。
    # 禁止再往本类里加文案 / 开关 / 规则类常量。

    @classmethod
    def from_env(cls) -> "Settings":
        """从环境变量构造配置。"""
        return cls(
            env=_env("ZHIYIN_ENV", "local"),
            database_url=_env("ZHIYIN_DATABASE_URL"),
            db_echo=_env_bool("ZHIYIN_DB_ECHO"),
            use_pami_llm=_env_bool("ZHIYIN_USE_PAMI_LLM"),
            use_pami_knowledge=_env_bool("ZHIYIN_USE_PAMI_KNOWLEDGE"),
            use_pami_auth=_env_bool("ZHIYIN_USE_PAMI_AUTH"),
            use_mysql=_env_bool("ZHIYIN_USE_MYSQL"),
            pami_base_url=_env("ZHIYIN_PAMI_BASE_URL"),
            pami_api_key=_env("ZHIYIN_PAMI_API_KEY"),
            pami_jwt_secret=_env("ZHIYIN_PAMI_JWT_SECRET"),
            local_data_dir=_env("ZHIYIN_DATA_DIR", "data"),
            local_object_dir=_env("ZHIYIN_OBJECT_DIR", "data/objects"),
            local_registry_dir=_env("ZHIYIN_REGISTRY_DIR", "data/registry"),
            local_knowledge_dir=_env("ZHIYIN_KNOWLEDGE_DIR", "data/knowledge"),
        )
