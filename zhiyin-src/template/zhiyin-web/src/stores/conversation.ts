import { defineStore } from 'pinia'
import { enterTask as enterTaskApi, listSessions, sendMessage } from '@/api/endpoints'
import type { ConversationMessageView, ConversationTurnView, PipelineCardView, TaskSessionView } from '@/api/schema'

export const useConversationStore = defineStore('conversation', {
  state: () => ({
    sessions: [] as TaskSessionView[], currentTaskId: null as string | null,
    turns: [] as ConversationMessageView[], pipeline: [] as PipelineCardView[],
    badge: {} as Record<string, unknown>, disclosure: null as Record<string, unknown> | null,
    guide: null as Record<string, unknown> | null, loadingSessions: false, sending: false, error: '',
  }),
  getters: {
    currentSession: state => state.sessions.find(item => item.task_id === state.currentTaskId),
  },
  actions: {
    async loadSessions() {
      this.loadingSessions = true; this.error = ''
      try {
        const result = await listSessions()
        this.sessions = result.sessions ?? []
        this.currentTaskId = result.current_task_id ?? this.sessions[0]?.task_id ?? null
      } finally { this.loadingSessions = false }
    },
    async enterTask(taskCode: string) {
      const item = await enterTaskApi(taskCode)
      this.sessions = [item, ...this.sessions.filter(x => x.task_id !== item.task_id)]
      this.currentTaskId = item.task_id
      return item
    },
    selectSession(taskId: string) { this.currentTaskId = taskId },
    applyTurn(turn: ConversationTurnView) {
      this.currentTaskId = turn.task_id
      this.badge = turn.badge ?? {}
      this.disclosure = turn.disclosure ?? null
      this.guide = turn.guide ?? null
      this.pipeline = turn.pipeline_cards ?? []
      this.turns.push(...(turn.messages ?? []))
    },
    async send(message: string) {
      const text = message.trim()
      if (!text || !this.currentTaskId || this.sending) return
      this.sending = true; this.error = ''
      this.turns.push({ role: 'user', text, created_at: new Date().toISOString() })
      try {
        const turn = await sendMessage(this.currentTaskId, text, crypto.randomUUID())
        this.applyTurn(turn)
      } catch (error) {
        this.turns.pop()
        throw error
      } finally { this.sending = false }
    },
    applyStageUncertain(clarifyQuestion: string) {
      this.guide = { kind: 'question', text: clarifyQuestion, question: clarifyQuestion }
    },
  },
})
