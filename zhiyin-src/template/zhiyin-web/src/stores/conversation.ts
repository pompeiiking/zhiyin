import { defineStore } from 'pinia'

import type { ConversationHistoryView, ConversationTurnView, SessionListView } from '@/api/schema'
import {
  enterTask as enterTaskApi,
  getConversationHistory,
  listSessions,
  sendMessage,
} from '@/api/endpoints'
import { useSessionStore } from './session'

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
      if (!this.currentTaskId) {
        // §4.1 兜底「直接开聊」常驻：从首页之外直接进对话页时，第一条消息要先为它建好兜底任务，
        // 否则这里永远只报"缺少当前任务"——对话页对非首页入口等于不可用。
        const fallback = useSessionStore().fallbackTaskEntry
        if (!fallback) throw new Error('缺少当前任务')
        await this.enterTask(fallback.code)
      }
      const taskId = this.currentTaskId
      if (!taskId) throw new Error('缺少当前任务')
      this.turns.push({ role: 'user', content: message })
      const turn = await sendMessage(taskId, message)
      this.applyTurn(turn)
      return turn
    },

    /**
     * 切换左栏当前会话。
     *
     * 中栏 turns / 徽章 / 告知 / 行为引导与右栏管线卡都只属于被选中的那个会话，
     * 切换时先清空再从后端读回该会话的既成事实（`GET /app/conversation/history`），
     * 否则会把上一个任务的结论显示成当前任务的历史。
     */
    async selectSession(taskId: string) {
      if (taskId === this.currentTaskId) return
      this.currentTaskId = taskId
      this.clearTurnState()
      await this.loadHistory(taskId)
    },

    /**
     * 读取某任务会话的既成事实，恢复中栏对话流与右栏环节进度。
     *
     * 刷新页面、切换会话、续接任务都走这里：气泡与管线卡来自后端落库的消息，
     * 不是前端凭记忆重建。读不到时如实说明，不退回空态假装"这段对话本来就没有内容"。
     */
    async loadHistory(taskId: string) {
      try {
        const history = (await getConversationHistory(taskId)) as ConversationHistoryView
        // 加载期间用户已经切走：丢弃这次结果，不覆盖新会话的视图。
        if (history.task_id !== this.currentTaskId) return
        this.turns = (history.messages ?? []).map((message) => ({
          role: message.role,
          content: message.text,
          // 历史可能跨过交接，气泡按当时的主理显示；没有名字时留空，由组件回落中性称呼。
          author: message.agent_name ?? undefined,
          theory: message.theory_refs?.[0] ?? null,
        }))
        this.pipeline = (history.pipeline_cards ?? []) as unknown as Array<
          Record<string, unknown>
        >
        const badge = history.badge as unknown as Record<string, unknown> | undefined
        this.badge = badge && Object.keys(badge).length ? badge : null
        // 告知行与行为引导属于"上一轮刚发生的事"，历史接口不带这两项：
        // 置空表示"本轮尚无新告知/新引导"，不拿历史文案顶替。
        this.disclosure = null
        this.guide = null
      } catch (error) {
        if (taskId !== this.currentTaskId) return
        this.clearTurnState()
        this.turns.push({
          role: 'system',
          content: `这段会话的历史没有读到：${error instanceof Error ? error.message : '未知错误'}。请稍后重试。`,
        })
      }
    },

    /** 清空中栏与右栏的会话私有视图（切换/加载失败时用）。 */
    clearTurnState() {
      this.turns = []
      this.pipeline = []
      this.badge = null
      this.disclosure = null
      this.guide = null
    },

    /** 把一轮 ConversationTurnView 落地到中栏 turns + 右栏 pipeline + 顶栏徽章。 */
    applyTurn(turn: ConversationTurnView) {
      for (const message of turn.messages ?? []) {
        this.turns.push({
          role: message.role,
          content: message.text,
          // 与历史口径一致：气泡按说话的主理显示名字，缺名字时由组件回落中性称呼。
          author: message.agent_name ?? undefined,
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
