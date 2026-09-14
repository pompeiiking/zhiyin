"""进程内共享状态实现，带乐观版本号。"""

from __future__ import annotations

from typing import Any, Optional

from zhiyin_orchestration.errors import StateConflictError
from zhiyin_orchestration.impl._shared import _utcnow
from zhiyin_orchestration.state import StateRecord, StateStore


class MemoryStateStore(StateStore):
    """进程内共享状态，带乐观版本号（R-ORC-005）。"""

    def __init__(self) -> None:
        self._records: dict[str, StateRecord] = {}

    def read(self, key: str) -> Optional[StateRecord]:
        record = self._records.get(key)
        return record.model_copy(deep=True) if record is not None else None

    def write(
        self, key: str, value: Any, *, expected_version: Optional[int] = None
    ) -> StateRecord:
        current = self._records.get(key)
        current_version = current.version if current is not None else 0
        if expected_version is not None and expected_version != current_version:
            raise StateConflictError(
                f"状态版本冲突：key={key} 期望 {expected_version}，实际 {current_version}",
                detail={"key": key, "expected": expected_version, "actual": current_version},
            )
        record = StateRecord(
            key=key, value=value, version=current_version + 1, updated_at=_utcnow()
        )
        self._records[key] = record
        return record.model_copy(deep=True)

    def delete(self, key: str) -> None:
        self._records.pop(key, None)

    def list_keys(self) -> list[str]:
        return sorted(self._records)


__all__ = ["MemoryStateStore"]
