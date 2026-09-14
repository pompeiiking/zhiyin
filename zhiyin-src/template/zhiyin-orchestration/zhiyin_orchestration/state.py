"""StateStore 原语：共享状态读写与版本控制。

与黑板的关系：黑板是**业务语义**上的共享状态（画像 / 行为 / 会话 / 资产），
由业务层黑板服务持有；StateStore 是**通用**键值状态原语，供编排过程暂存。

第一期允许业务层不直接使用本原语，但接口必须保留（R-ORC-005）。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class StateRecord(BaseModel):
    """一条共享状态记录。"""

    model_config = ConfigDict(extra="forbid")

    key: str
    value: Any = None
    version: int = Field(default=1, description="写入一次 +1，用于识别更新冲突")
    updated_at: datetime


class StateStore(ABC):
    """共享状态 Port。"""

    @abstractmethod
    def read(self, key: str) -> Optional[StateRecord]:
        """读取状态。不存在返回 None。"""

    @abstractmethod
    def write(
        self, key: str, value: Any, *, expected_version: Optional[int] = None
    ) -> StateRecord:
        """写入状态。

        expected_version 非空且与当前版本不一致时抛 StateConflictError。
        """

    @abstractmethod
    def delete(self, key: str) -> None:
        """删除状态。"""
