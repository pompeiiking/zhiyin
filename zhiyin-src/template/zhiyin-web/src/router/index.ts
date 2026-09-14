import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

/**
 * 路由与页面锚点口径。
 *
 * 锚点取自《前端页面设计 v1.0》§2.2，是全站唯一口径：
 *   #screen-home 首页 / #screen-auth 登录 / #screen-conv 核心对话页
 *   #screen-wb 智能工作台 / #screen-report 完整报告页
 *
 * 原型里另有 #screen-subagent 与 #screen-mentor，属 PRD v2.0 未定义的扩展页，
 * 不纳入第一期路由。
 */
export const PAGE_ANCHORS = {
  home: 'screen-home',
  auth: 'screen-auth',
  conversation: 'screen-conv',
  workspace: 'screen-wb',
  report: 'screen-report',
} as const

export const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'home',
    component: () => import('@/pages/HomePage.vue'),
    meta: { anchor: PAGE_ANCHORS.home, requireLogin: false },
  },
  {
    path: '/auth',
    name: 'auth',
    component: () => import('@/pages/AuthPage.vue'),
    meta: { anchor: PAGE_ANCHORS.auth, requireLogin: false },
  },
  {
    path: '/conv',
    name: 'conversation',
    component: () => import('@/pages/ConversationPage.vue'),
    meta: { anchor: PAGE_ANCHORS.conversation, requireLogin: true },
  },
  {
    path: '/wb',
    name: 'workspace',
    component: () => import('@/pages/WorkspacePage.vue'),
    meta: { anchor: PAGE_ANCHORS.workspace, requireLogin: true },
  },
  {
    path: '/report',
    name: 'report',
    component: () => import('@/pages/ReportPage.vue'),
    meta: { anchor: PAGE_ANCHORS.report, requireLogin: true },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// TODO(骨架): 登录守卫。未登录访问 requireLogin 页面时拉起登录 Modal，
// 而不是直接跳走——页面往返不销毁已生成资产（§3.2 返回与恢复）。
export default router
