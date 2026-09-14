"""API DTO 集合。

前端只依赖本包的模型；业务层模型变化由 `dto/mappers.py` 吸收，
避免"数据库字段变更影响前端"（R-API-007）。
"""

from zhiyin_api.dto.common import ApiResponse, ErrorCode
from zhiyin_api.dto.bootstrap import (
    BannerView,
    BootstrapView,
    FaqView,
    MenuView,
    RouteView,
    TaskEntryView,
    TrustBlockView,
)
from zhiyin_api.dto.conversation import (
    ConversationMessageView,
    ConversationTurnView,
    MessageRequest,
    PipelineCardView,
    SessionListView,
    TaskEnterRequest,
    TaskSessionView,
)
from zhiyin_api.dto.workspace import (
    DependencyEdgeView,
    ProfilePanelView,
    StagePanelView,
    WorkspacePageView,
)
from zhiyin_api.dto.asset import (
    AssetVersionView,
    ExportRequest,
    ExportResultView,
    ReportFullTextView,
)
from zhiyin_api.dto.track import TrackEventAck, TrackEventRequest

__all__ = [
    "ApiResponse",
    "ErrorCode",
    "BootstrapView",
    "BannerView",
    "FaqView",
    "MenuView",
    "RouteView",
    "TaskEntryView",
    "TrustBlockView",
    "ConversationMessageView",
    "ConversationTurnView",
    "MessageRequest",
    "PipelineCardView",
    "SessionListView",
    "TaskEnterRequest",
    "TaskSessionView",
    "DependencyEdgeView",
    "ProfilePanelView",
    "StagePanelView",
    "WorkspacePageView",
    "AssetVersionView",
    "ExportRequest",
    "ExportResultView",
    "ReportFullTextView",
    "TrackEventAck",
    "TrackEventRequest",
]
