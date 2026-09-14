"""zhiyin-infrastructure · 基础设施层。

职责：实现 data-sdk 定义的 Repository 与 Gateway 接口，包含三类实现：

- local/      第一期默认实现（本地 / Mock / Noop），保证系统能独立跑通；
- pami/       pami 平台真实适配器（模型 / 知识库 / RAG / 鉴权）；
- persistence/ MySQL 持久化与 ORM。

约束：本层实现接口，不得反向被上层 import；所有实现类必须只依赖接口。
"""

__all__ = ["local", "pami", "persistence"]
