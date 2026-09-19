import { useSessionStore } from '@/stores/session'
import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

/**
 * 路由与页面锚点口径。
 *
 * 锚点取自《前端页面设计 v1.0》§2.2，是全站唯一口径：
 *   #screen-home 首页 / #screen-auth 登录 / #screen-conv 核心对话页
 *   #screen-agents 智能体小队 / #screen-subagent 单智能体对话页
 *   #screen-wb 智能工作台 / #screen-report 完整报告页
 *
 * #screen-agents 与 #screen-subagent 是功能块（§2.1、§4.7–4.8），不进顶层导航：
 * 建档完成 → ②诊断产出 15 维解析 → 由用户挑选一位看它的职责与边界，再回核心对话页由它接手。
 * 智能体小队与单智能体页都不做实时对话；实时交互只发生在核心对话页。
 * 原型里的 #screen-mentor（导师工作台）属 PRD 的 P2 路线，仍不纳入第一期路由。
 */
export const PAGE_ANCHORS = {
  home: 'screen-home',
  auth: 'screen-auth',
  conversation: 'screen-conv',
  agents: 'screen-agents',
  agentDetail: 'screen-subagent',
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
    meta: { anchor: PAGE_ANCHORS.conversation, requireLogin: false },
  },
  {
    path: '/agents',
    name: 'agents',
    component: () => import('@/pages/AgentsPage.vue'),
    meta: { anchor: PAGE_ANCHORS.agents, requireLogin: false },
  },
  {
    path: '/agents/:agentId',
    name: 'agentDetail',
    component: () => import('@/pages/AgentDetailPage.vue'),
    meta: { anchor: PAGE_ANCHORS.agentDetail, requireLogin: false },
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

// 取消受保护导航并打开弹窗，当前组件保持挂载。初次直达回首页承载弹窗。
router.beforeEach(async (to, from) => {
  const session = useSessionStore()
  if (!to.meta.requireLogin) return true
  if (!session.loaded) await session.loadBootstrap()
  if (session.isLoggedIn) return true
  // 演示阶段（preview=true，后端未接入）先放开登录拦截，方便直接看报告 / 工作台整体。
  if (session.preview) return true
  session.pendingRoute = to.fullPath
  session.pendingTaskCode = ''
  session.openLogin('登录后继续，当前页面与输入会保留。')
  return from.matched.length ? false : { name: 'home', replace: true }
})

export default router
