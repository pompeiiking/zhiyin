"""事务契约。

对应 R-SDK-002：黑板写入（画像 / 行为日志 / 资产版本）必须能原子提交。
第一期实现为"单线程事务 + 数据库约束"，不做分布式锁与冲突重试。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import AbstractContextManager


class Transaction(ABC):
    """一次事务句柄。"""

    @abstractmethod
    def commit(self) -> None:
        """提交事务。"""

    @abstractmethod
    def rollback(self) -> None:
        """回滚事务。"""


class TransactionManager(ABC):
    """事务管理器。

    使用方式由实现决定，但语义固定为：退出上下文即提交，异常即回滚。
    """

    @abstractmethod
    def begin(self) -> AbstractContextManager[Transaction]:
        """开启一个事务上下文。"""
