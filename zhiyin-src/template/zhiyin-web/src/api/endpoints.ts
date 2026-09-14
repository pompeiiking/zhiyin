import { request } from './client'
import type { ApiTypes } from './types'

/**
 * 对接面 I1：前端 ↔ BFF 的全部接口清单。
 *
 * 每个函数一一对应 zhiyin-api 的一个 Controller 方法。这份清单就是前后端之间的
 * 契约：后端加接口，这里加函数；后端改字段，npm run gen:api 后类型会报错。
 *
 * 类型目前为占位（ApiTypes 为空），openapi-typescript 接入后逐个替换为生成类型。
 */

// ---------- 启动装配（app_controller） ----------

/** GET /app/bootstrap */
export const getBootstrap = () => request<ApiTypes>({ url: '/app/bootstrap', method: 'GET' })

// ---------- 会话与对话（conversation_controller） ----------

/** GET /app/sessions —— 左栏会话列表 */
export const listSessions = () => request<ApiTypes>({ url: '/app/sessions', method: 'GET' })

/** POST /app/task/enter —— 从首页任务入口进入微循环 */
export const enterTask = (taskCode: string) =>
  request<ApiTypes>({ url: '/app/task/enter', method: 'POST', data: { task_code: taskCode } })

/** POST /app/conversation/message —— 一轮对话 */
export const sendMessage = (taskId: string, message: string, clientMsgId?: string) =>
  request<ApiTypes>({
    url: '/app/conversation/message',
    method: 'POST',
    data: { task_id: taskId, message, client_msg_id: clientMsgId },
  })

// ---------- 工作台（workspace_controller） ----------

/** GET /app/workspace —— 工作台聚合视图 */
export const getWorkspace = () => request<ApiTypes>({ url: '/app/workspace', method: 'GET' })

// ---------- 资产（asset_controller） ----------

/** GET /app/assets/{asset_type}/versions —— 资产历史版本与 diff */
export const listAssetVersions = (assetType: string) =>
  request<ApiTypes>({ url: `/app/assets/${assetType}/versions`, method: 'GET' })

/** GET /app/report/full-text —— 完整报告页正文 */
export const getReportFullText = (version?: number) =>
  request<ApiTypes>({ url: '/app/report/full-text', method: 'GET', params: { version } })

/** POST /app/assets/export —— 导出（第一期占位） */
export const exportAsset = (assetType: string, format: 'pdf' | 'docx' = 'pdf') =>
  request<ApiTypes>({ url: '/app/assets/export', method: 'POST', data: { asset_type: assetType, format } })
