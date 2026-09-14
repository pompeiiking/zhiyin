import { defineStore } from 'pinia'

/**
 * 核心对话页状态（#screen-conv 三栏）。
 *
 * 三栏口径（前端设计文档 §4.2）：
 *   左栏 sessions    —— 并行任务会话（按"任务/环节"命名，不按 agent 名排布）
 *   中栏 turns       —— 当前主理对话 + 显式告知 + 行为引导
 *   右栏 pipeline    —— ①-⑤ 三态管线卡
 */
export const useConversationStore = defineStore('conversation', {
  state: () => ({
    sessions: [] as Array<Record<string, unknown>>,
    currentTaskId: null as string | null,
    turns: [] as Array<Record<string, unknown>>,
    pipeline: [] as Array<Record<string, unknown>>,
    /** 顶部主理徽章：现在是谁在帮我、依据什么 */
    badge: {} as Record<string, unknown>,
    /** 换主理 / 换理论 / 结论变化时的显式告知行 */
    disclosure: null as Record<string, unknown> | null,
    /** 行为引导（四选一），必须渲染出对应可点元素 */
    guide: null as Record<string, unknown> | null,
  }),

  actions: {
    async loadSessions() {
      // TODO(骨架): 调 listSessions()
      throw new Error('TODO(骨架): conversation.loadSessions 尚未实现')
    },
    async enterTask(taskCode: string) {
      // TODO(骨架): 调 enterTask()，切入 #screen-conv
      // 参数写进错误信息：骨架期就把接口形状固定住，实现时不会改成别的入参
      throw new Error(`TODO(骨架): conversation.enterTask 尚未实现（taskCode=${taskCode}）`)
    },
    async send(message: string) {
      // TODO(骨架): 调 sendMessage()，把 TurnResult 追加进 turns 并刷新 pipeline
      throw new Error(`TODO(骨架): conversation.send 尚未实现（message=${message}）`)
    },
    applyStageUncertain(clarifyQuestion: string) {
      // TODO(骨架): code=1006 时渲染澄清追问，不报错（ERROR_HANDLING 口径）
      throw new Error(
        `TODO(骨架): conversation.applyStageUncertain 尚未实现（clarifyQuestion=${clarifyQuestion}）`,
      )
    },
  },
})
