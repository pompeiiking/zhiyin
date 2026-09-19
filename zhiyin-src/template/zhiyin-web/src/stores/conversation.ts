import { defineStore } from 'pinia'

import type { ConversationTurnView, SessionListView } from '@/api/schema'
import { enterTask as enterTaskApi, listSessions, sendMessage } from '@/api/endpoints'

/**
 * 核心对话页状态（#screen-conv 三栏）。
 *
 * 三栏口径（前端设计文档 §4.2）：
 *   左栏 sessions    —— 并行任务会话（按"任务/环节"命名，不按 agent 名排布）
 *   中栏 turns       —— 当前主理对话 + 显式告知 + 行为引导
 *   右栏 pipeline    —— ①-⑤ 三态管线卡
 */
export const useConversationStore = defineStore('conversation', {
  // 初始状态一律为空：页面在拿到后端数据前显示空态，不预置任何演示内容。
  // 演示数据曾经让"接口没接通"看起来像"接口接通了"，是本期明确要清掉的东西。
  state: () => ({
    sessions: [] as Array<Record<string, unknown>>,
    currentTaskId: null as string | null,
    turns: [] as Array<Record<string, unknown>>,
    pipeline: [] as Array<Record<string, unknown>>,
    /** 顶部主理徽章：现在是谁在帮我、依据什么（只由真实一轮对话写入） */
    badge: null as Record<string, unknown> | null,
    /** 换主理 / 换理论 / 结论变化时的显式告知行；无变化时必须保持 null */
    disclosure: null as Record<string, unknown> | null,
    /** 行为引导（四选一），必须渲染出对应可点元素；只由真实一轮对话写入 */
    guide: null as Record<string, unknown> | null,
  }),

  actions: {
    /** 拉取左栏会话列表。加载失败即保持空列表并由调用方显示空态，不塞演示数据。 */
    async loadSessions() {
      const data = (await listSessions()) as SessionListView
      const sessions = (data.sessions ?? []).map((s) => ({ ...s }))
      this.sessions = sessions
      if (sessions.length) {
        this.currentTaskId = data.current_task_id ?? this.currentTaskId ?? sessions[0].task_id
      } else {
        this.currentTaskId = null
      }
    },

    /** 从任务入口进入微循环：写入会话并切换到当前任务（页面跳转由调用方处理）。 */
    async enterTask(taskCode: string) {
      const task = await enterTaskApi(taskCode)
      if (!task?.task_id) throw new Error('Missing task')
      const index = this.sessions.findIndex((s) => s.task_id === task.task_id)
      if (index < 0) this.sessions.push(task)
      else this.sessions[index] = task
      this.currentTaskId = task.task_id
      return task
    },

    /** 发送一轮用户消息，把返回的最短结论 / 告知 / 行为引导 / 管线卡写回三栏。 */
    async send(message: string) {
      if (!this.currentTaskId) throw new Error('缺少当前任务')
      this.turns.push({ role: 'user', content: message })
      const turn = await sendMessage(this.currentTaskId, message)
      this.applyTurn(turn)
      return turn
    },

    /** 环节判定不确定（ErrorCode 1006）：渲染澄清追问，不当作错误。 */
    applyStageUncertain(clarifyQuestion: string) {
      this.disclosure = { message: clarifyQuestion } as Record<string, unknown>
    },

    /** 把一轮 ConversationTurnView 落地到中栏 turns + 右栏 pipeline + 顶栏徽章。 */
    applyTurn(turn: ConversationTurnView) {
      for (const message of turn.messages ?? []) {
        this.turns.push({
          role: message.role,
          content: message.text,
          theory: message.theory_refs?.[0] ?? null,
        })
      }
      if (turn.badge) this.badge = turn.badge as unknown as Record<string, unknown>
      if (turn.pipeline_cards) {
        this.pipeline = turn.pipeline_cards as unknown as Array<Record<string, unknown>>
      }
      this.disclosure = (turn.disclosure as unknown as Record<string, unknown> | null) ?? null
      this.guide = (turn.guide as unknown as Record<string, unknown> | null) ?? null
    },
  },
})
