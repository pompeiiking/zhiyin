"""zhiyin-api · 前端 / BFF 接入层。

职责（R-API-001 ~ R-API-008）：
- Controller 只做参数接收、格式校验、结果返回；
- DTO Mapper 负责 API DTO 与业务 DTO 的转换；
- Application Facade 调用业务层服务并组装 View DTO；
- 本层不写业务规则，不直接访问数据库、模型、知识库。

约束：**只允许依赖 zhiyin-business**（§4.5.1 / §九 验收项 1）。
领域取值（环节、资产类型、任务状态等）一律从 `zhiyin_business.published`
（业务层对外发布面）取，禁止直接 import `zhiyin_data_sdk` —— 否则依赖图会出现
跨层直连。DTO 不得直接暴露数据库实体。
"""

__all__ = ["dto", "controllers", "facade"]
