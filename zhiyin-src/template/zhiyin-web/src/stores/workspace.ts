import { defineStore } from 'pinia'

/**
 * 智能工作台状态（#screen-wb，按 ①-⑤ 分层聚合）。
 *
 * 工作台不做实时对话，只展示"活资产"（前端设计文档 §4.3）。
 */
export const useWorkspaceStore = defineStore('workspace', {
  state: () => ({
    loaded: false,
    profilePanel: null as Record<string, unknown> | null,
    reportPanel: null as Record<string, unknown> | null,
    planPanel: null as Record<string, unknown> | null,
    actionPanel: null as Record<string, unknown> | null,
    reviewPanel: null as Record<string, unknown> | null,
    coachMessages: [] as Array<Record<string, unknown>>,
    dependencies: [] as Array<Record<string, unknown>>,
    /** 功能块入口与静态数据：报告全文 / 导出 / 日历 / 成就 / 导师 / 演示 */
    blocks: {} as Record<string, unknown>,
    /** 各层折叠状态，页面往返后保留 */
    collapsed: {} as Record<string, boolean>,
  }),

  actions: {
    async load() {
      // TODO(骨架): 调 getWorkspace()，填充五层资产与功能块
      throw new Error('TODO(骨架): workspace.load 尚未实现')
    },
    toggleStage(stage: string) {
      this.collapsed[stage] = !this.collapsed[stage]
    },
  },
})
