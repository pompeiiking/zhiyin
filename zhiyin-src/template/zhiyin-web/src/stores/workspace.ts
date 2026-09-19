import { defineStore } from 'pinia'
import { getWorkspace } from '@/api/endpoints'

/**
 * 智能工作台状态（#screen-wb，按 ①-⑤ 分层聚合）。
 *
 * 工作台不做实时对话，只展示"活资产"（前端设计文档 §4.3）。
 * 折叠状态 `collapsed` 在页面往返后保留，不随路由切换重置。
 */
export const useWorkspaceStore = defineStore('workspace', {
  // 初始状态一律为空：拿到后端数据前显示空态 / 加载态，不预置任何演示内容。
  state: () => ({
    loaded: false,
    loading: false,
    error: '',
    /** 轴 A 阶段定位：只由接口下发；接口没给就保持 null，由页面显示「待系统确认」 */
    axisAStage: null as string | null,
    profilePanel: null as Record<string, unknown> | null,
    reportPanel: null as Record<string, unknown> | null,
    planPanel: null as Record<string, unknown> | null,
    actionPanel: null as Record<string, unknown> | null,
    reviewPanel: null as Record<string, unknown> | null,
    coachMessages: [] as Array<Record<string, unknown>>,
    dependencies: [] as Array<Record<string, unknown>>,
    /** 功能块入口与静态数据：报告全文 / 导出 / 日历 / 成就 / 导师 */
    blocks: {} as Record<string, unknown>,
    /** 各层折叠状态，页面往返后保留 */
    collapsed: {} as Record<string, boolean>,
  }),

  actions: {
    async load() {
      if (this.loaded) return
      this.loaded = true
      this.loading = true
      try {
        const data = await getWorkspace()
        this.axisAStage = data.axis_a_stage ?? null
        this.profilePanel = (data.profile_panel as unknown as Record<string, unknown>) ?? null
        this.reportPanel = (data.report_panel as unknown as Record<string, unknown>) ?? null
        this.planPanel = (data.plan_panel as unknown as Record<string, unknown>) ?? null
        this.actionPanel = (data.action_panel as unknown as Record<string, unknown>) ?? null
        this.reviewPanel = (data.review_panel as unknown as Record<string, unknown>) ?? null
        this.coachMessages = (data.coach_messages as unknown as Array<Record<string, unknown>>) ?? []
        this.dependencies = (data.dependencies as unknown as Array<Record<string, unknown>>) ?? []
        this.blocks = (data.blocks as unknown as Record<string, unknown>) ?? {}
        this.error = ''
      } catch (err) {
        // 加载失败必须可见：保留空态并展示错误，不得用演示数据伪装成加载成功。
        this.error = err instanceof Error ? err.message : '工作台加载失败'
      } finally {
        this.loading = false
      }
    },
    toggleStage(stage: string) {
      this.collapsed[stage] = !this.collapsed[stage]
    },
  },
})
