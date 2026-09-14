"""受限裸查询逃生口。

为什么需要它，以及为什么必须"受限"
----------------------------------
ORM / Repository 覆盖不了聚合查询（工作台的一次性多表聚合、报表统计）。
没有逃生口时，实现者只有两个选择：把 SQL 塞进业务层（越层），或者放弃优化。
因此在 SDK 里显式开一个口子，但把它**限定在基础设施层内部**：

- 只有 `zhiyin_infrastructure` 的 Repository / Worker 实现可以 import 本模块；
- `zhiyin_business` 与 `zhiyin_orchestration` **禁止** import（由
  `tests/test_architecture.py::test_raw_query_is_infra_only` 守卫）；
- 返回一律是原始行字典，不得在本层组装领域模型 —— 领域模型由 Repository 负责。

这条规则让"偶发的高性能查询"有合法去处，同时保证业务层看不到 SQL。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Mapping, Optional, Sequence, Union

Params = Optional[Union[Sequence[Any], Mapping[str, Any]]]


class RawQueryGateway(ABC):
    """受限直接查询 Port（仅基础设施层使用）。"""

    @abstractmethod
    async def fetch_all(self, sql: str, params: Params = None) -> list[dict[str, Any]]:
        """执行查询并返回行字典列表。"""

    @abstractmethod
    async def fetch_one(self, sql: str, params: Params = None) -> Optional[dict[str, Any]]:
        """执行查询并返回首行；无结果返回 None。"""

    @abstractmethod
    async def execute(self, sql: str, params: Params = None) -> int:
        """执行写语句，返回受影响行数。必须由调用方负责事务边界。"""

    @abstractmethod
    async def execute_many(self, sql: str, rows: Sequence[Sequence[Any]]) -> int:
        """批量执行同一条语句，返回累计受影响行数。"""


__all__ = ["Params", "RawQueryGateway"]
