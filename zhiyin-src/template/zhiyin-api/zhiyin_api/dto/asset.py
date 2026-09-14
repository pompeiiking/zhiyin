"""资产与导出 DTO（FR-BLOCK-001）。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from zhiyin_business.published import AssetType


class AssetVersionView(BaseModel):
    """资产版本视图（R-API-005）。前端据此展示"v1→v2 的差异"。"""

    model_config = ConfigDict(extra="forbid")

    asset_type: AssetType
    asset_id: str
    version: int
    created_at: datetime
    depends_on_profile_keys: list[str] = Field(default_factory=list)
    diff_from_previous: Optional[str] = None


class ReportFullTextView(BaseModel):
    """完整报告页正文（只读资产视图，不承载实时对话）。"""

    model_config = ConfigDict(extra="forbid")

    report_id: str
    version: int
    generated_at: datetime
    toc: list[dict[str, str]] = Field(default_factory=list, description="左侧目录导航")
    sections: list[dict[str, Any]] = Field(
        default_factory=list, description="15 维全景 / 方案 / 行动计划 / 个人画像"
    )


class ExportRequest(BaseModel):
    """导出请求。"""

    model_config = ConfigDict(extra="forbid")

    asset_type: AssetType
    format: Literal["pdf", "docx"] = "pdf"


class ExportResultView(BaseModel):
    """导出结果。第一期 available 恒 False，仅预留入口。"""

    model_config = ConfigDict(extra="forbid")

    available: bool = False
    message: str = "第一期仅预留导出入口"
    object_key: Optional[str] = None
