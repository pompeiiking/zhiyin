/**
 * 生成类型的取值别名（唯一取用处）。
 *
 * `types.ts` 是 `npm run gen:api` 的生成物（会被整份覆盖，禁止手改），
 * OpenAPI 把每个 DTO 放在 `components["schemas"][<DTO 名>]` 下，直接写这个路径
 * 又长又容易拼错。本文件把它收敛成一组可读别名：
 *
 *     import type { BootstrapView } from './schema'
 *
 * 好处：后端 DTO 改名时，前端在 `npm run typecheck` 就会报错，而不是运行时才发现
 * "字段没了"——这正是"字段口径靠代码保证、不靠人沟通"的落点。
 */

import type { components } from './types'

type Schemas = components['schemas']

/** 统一错误码（与后端 zhiyin_api/dto/common.py::ErrorCode 同源，由 OpenAPI 生成） */
export type BackendErrorCode = Schemas['ErrorCode']

/** 资产类型（与后端 zhiyin_kernel/enums.py::AssetType 同源，由 OpenAPI 生成） */
export type AssetTypeValue = Schemas['AssetType']

// ---------- 启动装配（app_controller） ----------

export type BootstrapView = Schemas['BootstrapView']
export type MenuView = Schemas['MenuView']
export type RouteView = Schemas['RouteView']
export type TaskEntryView = Schemas['TaskEntryView']
export type TrustBlockView = Schemas['TrustBlockView']
export type BannerView = Schemas['BannerView']
export type FaqView = Schemas['FaqView']
/** 能力池条目（D9）：含负责环节与理论中文名，供 agents store 派生展示字段 */
export type AgentView = Schemas['AgentView']
export type AgentTheoryView = Schemas['AgentTheoryView']

// ---------- 会话与对话（conversation_controller） ----------

export type SessionListView = Schemas['SessionListView']
export type TaskSessionView = Schemas['TaskSessionView']
export type TaskEnterRequest = Schemas['TaskEnterRequest']
export type MessageRequest = Schemas['MessageRequest']
export type ConversationTurnView = Schemas['ConversationTurnView']
export type ConversationMessageView = Schemas['ConversationMessageView']
export type PipelineCardView = Schemas['PipelineCardView']

// ---------- 工作台（workspace_controller） ----------

export type WorkspacePageView = Schemas['WorkspacePageView']
export type ProfilePanelView = Schemas['ProfilePanelView']
export type StagePanelView = Schemas['StagePanelView']
export type LoopStage = Schemas['LoopStage']

// ---------- 资产（asset_controller） ----------

export type AssetVersionView = Schemas['AssetVersionView']
export type ReportFullTextView = Schemas['ReportFullTextView']
export type ExportRequest = Schemas['ExportRequest']
export type ExportResultView = Schemas['ExportResultView']

// ---------- 埋点（track_controller） ----------

export type TrackEventRequest = Schemas['TrackEventRequest']
export type TrackEventAck = Schemas['TrackEventAck']
