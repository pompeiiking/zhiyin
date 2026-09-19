import { request } from './client'
import type {
  AssetTypeValue,
  AssetVersionView,
  BootstrapView,
  ConversationHistoryView,
  ConversationTurnView,
  ExportRequest,
  ExportResultView,
  MessageRequest,
  ReportFullTextView,
  SessionListView,
  TaskEnterRequest,
  TaskSessionView,
  TrackEventAck,
  TrackEventRequest,
  WorkspacePageView,
} from './schema'

/**
 * 对接面 I1：前端 ↔ BFF 的全部接口清单。
 *
 * 每个函数一一对应 zhiyin-api 的一个 Controller 方法。这份清单就是前后端之间的
 * 契约：后端加接口，这里加函数；后端改字段，npm run gen:api 后类型会报错。
 *
 * 返回类型来自 `src/api/types.ts`（后端 OpenAPI 生成物）经 `schema.ts` 收敛的别名：
 * `npm run gen:api` 从入库快照 `../contracts/openapi.json` 生成，**不需要后端在跑**。
 * 快照与后端代码的一致性由 `tests/test_api_contract.py` 守，前端类型与快照的一致性
 * 由 CI 的 `npm run check:api` 守——因此这里的 url 与字段都不可能悄悄过期。
 */

// ---------- 启动装配（app_controller） ----------

/** GET /app/bootstrap */
export const getBootstrap = () => request<BootstrapView>({ url: '/app/bootstrap', method: 'GET' })

// ---------- 会话与对话（conversation_controller） ----------

/** GET /app/sessions —— 左栏会话列表 */
export const listSessions = () => request<SessionListView>({ url: '/app/sessions', method: 'GET' })

/** POST /app/task/enter —— 从首页任务入口进入微循环 */
export const enterTask = (taskCode: string) =>
  request<TaskSessionView>({
    url: '/app/task/enter',
    method: 'POST',
    data: { task_code: taskCode } satisfies TaskEnterRequest,
  })

/** POST /app/conversation/message —— 一轮对话 */
export const sendMessage = (taskId: string, message: string, clientMsgId?: string) =>
  request<ConversationTurnView>({
    url: '/app/conversation/message',
    method: 'POST',
    data: { task_id: taskId, message, client_msg_id: clientMsgId } satisfies MessageRequest,
  })

/** GET /app/conversation/history —— 某任务会话的既成事实（刷新/切会话恢复对话流与环节进度） */
export const getConversationHistory = (taskId: string) =>
  request<ConversationHistoryView>({
    url: '/app/conversation/history',
    method: 'GET',
    params: { task_id: taskId },
  })

// ---------- 工作台（workspace_controller） ----------

/** GET /app/workspace —— 工作台聚合视图 */
export const getWorkspace = () =>
  request<WorkspacePageView>({ url: '/app/workspace', method: 'GET' })

// ---------- 资产（asset_controller） ----------

/** GET /app/assets/{asset_type}/versions —— 资产历史版本与 diff */
export const listAssetVersions = (assetType: AssetTypeValue) =>
  request<AssetVersionView[]>({ url: `/app/assets/${assetType}/versions`, method: 'GET' })

/** GET /app/report/full-text —— 完整报告页正文 */
export const getReportFullText = (version?: number) =>
  request<ReportFullTextView>({
    url: '/app/report/full-text',
    method: 'GET',
    params: { version },
  })

/** POST /app/assets/export —— 导出（第一期占位） */
export const exportAsset = (assetType: AssetTypeValue, format: 'pdf' | 'docx' = 'pdf') =>
  request<ExportResultView>({
    url: '/app/assets/export',
    method: 'POST',
    data: { asset_type: assetType, format } satisfies ExportRequest,
  })

// ---------- 埋点（track_controller） ----------

/** POST /app/track —— 前端体验型埋点（纯后端派生的事件不要报，见 track_events.json） */
export const trackEvent = (
  event: string,
  payload: Record<string, unknown> = {},
  clientEventId?: string,
) =>
  request<TrackEventAck>({
    url: '/app/track',
    method: 'POST',
    data: { event, payload, client_event_id: clientEventId } satisfies TrackEventRequest,
  })
