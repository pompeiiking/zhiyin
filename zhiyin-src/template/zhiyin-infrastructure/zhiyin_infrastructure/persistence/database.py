"""数据库连接与事务实现。

第一期策略：单库单写，乐观锁用 version 列，不做分库分表。
"""

from __future__ import annotations

from contextlib import AbstractContextManager

from zhiyin_data_sdk.transaction import Transaction, TransactionManager


class SqlAlchemyTransactionManager(TransactionManager):
    """基于 SQLAlchemy Session 的事务管理。

    TODO(骨架): 实现 begin()，返回上下文管理器：
    正常退出 commit，异常 rollback。
    """

    def __init__(self, database_url: str, echo: bool = False) -> None:
        self._database_url = database_url
        self._echo = echo

    def begin(self) -> AbstractContextManager[Transaction]:
        raise NotImplementedError("TODO(骨架): SqlAlchemyTransactionManager.begin 尚未实现")
