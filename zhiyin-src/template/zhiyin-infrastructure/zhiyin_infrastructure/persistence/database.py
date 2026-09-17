"""SQLAlchemy 同步事务边界。

Data SDK 的事务契约是同步上下文管理器，因此这里使用 PyMySQL 驱动；异步裸查询
使用独立的 asyncmy 连接池，二者不会把驱动对象泄露给业务层。
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

from zhiyin_data_sdk.transaction import Transaction, TransactionManager


def _sync_url(database_url: str) -> str:
    value = database_url.strip()
    if value.startswith("mysql+asyncmy://"):
        return "mysql+pymysql://" + value.removeprefix("mysql+asyncmy://")
    if value.startswith("mysql://"):
        return "mysql+pymysql://" + value.removeprefix("mysql://")
    return value


class SqlAlchemyTransaction(Transaction):
    """不向上层暴露 SQLAlchemy Session 的事务句柄。"""

    def __init__(self, session: Any) -> None:
        self._session = session
        self._finished = False

    @property
    def session(self) -> Any:
        """仅供同属 Infrastructure 的 Repository 取得当前 Session。"""
        return self._session

    def commit(self) -> None:
        if not self._finished:
            self._session.commit()
            self._finished = True

    def rollback(self) -> None:
        if not self._finished:
            self._session.rollback()
            self._finished = True


class SqlAlchemyTransactionManager(TransactionManager):
    """正常退出提交、异常退出回滚，并始终释放 Session。"""

    IMPLEMENTATION_STATUS = "wired"

    def __init__(self, database_url: str, echo: bool = False) -> None:
        if not database_url.strip():
            raise ValueError("启用数据库事务时必须配置 database_url")
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        self._engine = create_engine(
            _sync_url(database_url), echo=echo, pool_pre_ping=True, future=True
        )
        self._session_factory = sessionmaker(
            bind=self._engine, expire_on_commit=False, future=True
        )

    @contextmanager
    def begin(self) -> Iterator[Transaction]:
        session = self._session_factory()
        transaction = SqlAlchemyTransaction(session)
        try:
            yield transaction
            transaction.commit()
        except BaseException:
            transaction.rollback()
            raise
        finally:
            session.close()

    def close(self) -> None:
        self._engine.dispose()


__all__ = ["SqlAlchemyTransaction", "SqlAlchemyTransactionManager"]
