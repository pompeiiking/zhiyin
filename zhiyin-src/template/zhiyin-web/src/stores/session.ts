import { defineStore } from 'pinia'

/**
 * 会话级状态：身份 / 菜单路由 / 首页任务入口 / 功能开关。
 *
 * 数据源全部来自 GET /app/bootstrap——任务文案与功能开关由后端下发，
 * 因此改文案不需要前端发版（R-API-001）。
 */
export const useSessionStore = defineStore('session', {
  state: () => ({
    loaded: false,
    identity: {} as Record<string, string>,
    menus: [] as Array<Record<string, unknown>>,
    taskEntries: [] as Array<Record<string, unknown>>,
    featureFlags: {} as Record<string, boolean>,
    trustCopy: '',
  }),

  getters: {
    isLoggedIn: (state) => state.identity?.role != null && state.identity.role !== 'guest',
  },

  actions: {
    async loadBootstrap() {
      // TODO(骨架): 调 getBootstrap()，填充 identity / menus / taskEntries / featureFlags
      throw new Error('TODO(骨架): session.loadBootstrap 尚未实现')
    },
  },
})
