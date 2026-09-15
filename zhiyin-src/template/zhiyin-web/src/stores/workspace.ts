import { defineStore } from 'pinia'

import type { components } from '@/api/types'
import { getWorkspace } from '@/api/endpoints'

type ProfilePanelView = components['schemas']['ProfilePanelView']
type StagePanelView = components['schemas']['StagePanelView']
type DependencyEdgeView = components['schemas']['DependencyEdgeView']

/**
 * 智能工作台状态（#screen-wb，按 ①-⑤ 分层聚合）。
 *
 * 工作台不做实时对话，只展示"活资产"（前端设计文档 §4.3）。
 */
export const useWorkspaceStore = defineStore('workspace', {
  state: () => ({
    loaded: false,
    profilePanel: null as ProfilePanelView | null,
    reportPanel: null as StagePanelView | null,
    planPanel: null as StagePanelView | null,
    actionPanel: null as StagePanelView | null,
    reviewPanel: null as StagePanelView | null,
    coachMessages: [] as Array<Record<string, unknown>>,
    dependencies: [] as DependencyEdgeView[],
    /** 功能块入口与静态数据：报告全文 / 导出 / 日历 / 成就 / 导师 / 演示 */
    blocks: {} as Record<string, unknown>,
    /** 轴 A 阶段定位（后台推断，用户可纠正） */
    axisAStage: null as string | null,
    /** 各层折叠状态，页面往返后保留 */
    collapsed: {} as Record<string, boolean>,
  }),

  actions: {
    async load() {
      const data = await getWorkspace()

      this.profilePanel = data.profile_panel ?? null
      this.reportPanel = data.report_panel ?? null
      this.planPanel = data.plan_panel ?? null
      this.actionPanel = data.action_panel ?? null
      this.reviewPanel = data.review_panel ?? null
      this.coachMessages = data.coach_messages ?? []
      this.dependencies = data.dependencies ?? []
      this.blocks = data.blocks ?? {}
      this.axisAStage = data.axis_a_stage ?? null
      this.loaded = true
    },
    toggleStage(stage: string) {
      this.collapsed[stage] = !this.collapsed[stage]
    },
  },
})
