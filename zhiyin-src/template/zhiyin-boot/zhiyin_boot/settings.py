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

    # ---------- Redis（第一期直接接入，逻辑 DB 由 Infrastructure 固定映射） ----------
    redis_url: str = "redis://127.0.0.1:6379"
    redis_password: str = ""
    redis_ssl: bool = False
    redis_pool_size: int = 20
    redis_socket_timeout_s: float = 2.0

    # ---------- 能力开关：决定装配 local 还是 pami ----------
    use_pami_llm: bool = False
    use_pami_embedding: bool = False
    use_pami_search: bool = False
    use_pami_auth: bool = False
    use_mysql: bool = False
    use_pgvector: bool = False
    use_minio: bool = False

    # ---------- 占位实现的显式许可（默认拒绝，见待决问题 D1） ----------
    allow_placeholder_llm: bool = False
    """是否允许装配**占位模型**（`LocalOrMockLLM`）来提供服务。

    默认 False：既不接真实模型、又没有显式许可时，服务**拒绝启动**。
    理由：占位实现会产出结构合法但内容虚构的结果，此前漏配 `ZHIYIN_USE_PAMI_LLM`
    的环境会把这种产出当业务结果落库，而门禁、装配报告与界面**都不会报警**。
    写成显式开关而不是靠"env 名字"判断，是因为部署环境的 `ZHIYIN_ENV` 就是 `local`
    （见 `deploy/compose.yaml`），按环境名放行等于没有拦截。

    本地开发与 CI 需要占位实现时，显式设为 1。
    """

    # ---------- pami 接入 ----------
    pami_base_url: str = ""
    # 旧的通用 Key 仅为兼容已有环境；Agent / RAG 同时启用时必须分别配置。
    pami_api_key: str = ""
    pami_agent_api_key: str = ""
    pami_rag_api_key: str = ""
    pami_jwt_secret: str = ""
    pami_org_id: str = ""
    pami_embedding_model_id: str = ""
    pami_timeout_s: float = 60.0

    # ---------- M3 数据基础设施 ----------
    vector_database_url: str = ""
    search_rrf_k: int = 60
    minio_endpoint: str = ""
    minio_access_key: str = ""
    minio_secret_key: str = ""
    minio_bucket: str = "zhiyin-assets"
    minio_secure: bool = False

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
            redis_url=_env("ZHIYIN_REDIS_URL", "redis://127.0.0.1:6379"),
            redis_password=_env("ZHIYIN_REDIS_PASSWORD"),
            redis_ssl=_env_bool("ZHIYIN_REDIS_SSL"),
            redis_pool_size=int(_env("ZHIYIN_REDIS_POOL_SIZE", "20")),
            redis_socket_timeout_s=float(
                _env("ZHIYIN_REDIS_SOCKET_TIMEOUT_S", "2.0")
            ),
            use_pami_llm=_env_bool("ZHIYIN_USE_PAMI_LLM"),
        allow_placeholder_llm=_env_bool("ZHIYIN_ALLOW_PLACEHOLDER_LLM"),
            use_pami_embedding=_env_bool("ZHIYIN_USE_PAMI_EMBEDDING"),
            use_pami_search=_env_bool("ZHIYIN_USE_PAMI_SEARCH"),
            use_pami_auth=_env_bool("ZHIYIN_USE_PAMI_AUTH"),
            use_mysql=_env_bool("ZHIYIN_USE_MYSQL"),
            use_pgvector=_env_bool("ZHIYIN_USE_PGVECTOR"),
            use_minio=_env_bool("ZHIYIN_USE_MINIO"),
            pami_base_url=_env("ZHIYIN_PAMI_BASE_URL"),
            pami_api_key=_env("ZHIYIN_PAMI_API_KEY"),
            pami_agent_api_key=_env("ZHIYIN_PAMI_AGENT_API_KEY"),
            pami_rag_api_key=_env("ZHIYIN_PAMI_RAG_API_KEY"),
            pami_jwt_secret=_env("ZHIYIN_PAMI_JWT_SECRET"),
            pami_org_id=_env("ZHIYIN_PAMI_ORG_ID"),
            pami_embedding_model_id=_env("ZHIYIN_PAMI_EMBEDDING_MODEL_ID"),
            pami_timeout_s=float(_env("ZHIYIN_PAMI_TIMEOUT_S", "60")),
            vector_database_url=_env("ZHIYIN_VECTOR_DATABASE_URL"),
            search_rrf_k=int(_env("ZHIYIN_SEARCH_RRF_K", "60")),
            minio_endpoint=_env("ZHIYIN_MINIO_ENDPOINT"),
            minio_access_key=_env("ZHIYIN_MINIO_ACCESS_KEY"),
            minio_secret_key=_env("ZHIYIN_MINIO_SECRET_KEY"),
            minio_bucket=_env("ZHIYIN_MINIO_BUCKET", "zhiyin-assets"),
            minio_secure=_env_bool("ZHIYIN_MINIO_SECURE"),
            local_data_dir=_env("ZHIYIN_DATA_DIR", "data"),
            local_object_dir=_env("ZHIYIN_OBJECT_DIR", "data/objects"),
            local_registry_dir=_env("ZHIYIN_REGISTRY_DIR", "data/registry"),
            local_knowledge_dir=_env("ZHIYIN_KNOWLEDGE_DIR", "data/knowledge"),
        )
