import { defineStore } from 'pinia'

/**
 * 会话级状态：身份 / 菜单路由 / 首页任务入口 / 功能开关。
 *
 * 数据源全部来自 GET /app/bootstrap——任务文案与功能开关由后端下发，
 * 因此改文案不需要前端发版（R-API-001）。
 *
 * 字段与后端 `zhiyin_api/dto/bootstrap.py::BootstrapView` 一一对应；
 * 后端加字段时这里同步加，不要在组件里另存副本（口径只允许一处）。
 */
export const useSessionStore = defineStore('session', {
  state: () => ({
    loaded: false,
    identity: {} as Record<string, string>,
    menus: [] as Array<Record<string, unknown>>,
    routes: [] as Array<Record<string, unknown>>,
    taskEntries: [] as Array<Record<string, unknown>>,
    featureFlags: {} as Record<string, boolean>,
    /** 文案包（key → text）：组件不硬编码展示文案，一律按 key 取 */
    copyBundle: {} as Record<string, string>,
    /** 信任区：第一条为主线，其余为可展开示例 */
    trustBlocks: [] as Array<Record<string, unknown>>,
    banners: [] as Array<Record<string, unknown>>,
    faqs: [] as Array<Record<string, unknown>>,
  }),

  getters: {
    isLoggedIn: (state) => state.identity?.role != null && state.identity.role !== 'guest',
  },

  actions: {
    async loadBootstrap() {
      // TODO(骨架): 调 getBootstrap()，填充 identity / menus / routes /
      // taskEntries / featureFlags / copyBundle / trustBlocks / banners / faqs
      throw new Error('TODO(骨架): session.loadBootstrap 尚未实现')
    },
  },
})
