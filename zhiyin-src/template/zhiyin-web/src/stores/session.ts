import { defineStore } from 'pinia'

import type {
  AgentView,
  BannerView,
  FaqView,
  MenuView,
  RouteView,
  TaskEntryView,
  TrustBlockView,
} from '@/api/schema'
import { getBootstrap } from '@/api/endpoints'

/** 进行中的 bootstrap 请求：App 挂载与路由守卫并发调用时共享同一 promise，避免重复请求与竞态 */
let inflightBootstrap: Promise<void> | null = null

/**
 * 会话级状态：身份 / 菜单路由 / 首页任务入口 / 功能开关 / 登录弹窗 / 游客拦截。
 *
 * 数据源全部来自 GET /app/bootstrap——任务文案与功能开关由后端下发，
 * 因此改文案不需要前端发版（R-API-001）。
 */
export const useSessionStore = defineStore('session', {
  state: () => ({
    loaded: false,
    /** bootstrap / 身份刷新加载中，供顶栏与登录弹窗占位 */
    loading: false,
    appName: '',
    identity: {} as Record<string, string>,
    menus: [] as MenuView[],
    routes: [] as RouteView[],
    taskEntries: [] as TaskEntryView[],
    /**
     * 能力池（五位主理的定义）：来自 bootstrap（D9），前端不再硬编码。
     * 展示字段（序号 / 头像字 / 主题色 / 环节中文名）由 `stores/agents.ts` 派生。
     */
    agents: [] as AgentView[],
    featureFlags: {} as Record<string, boolean>,
    /** 文案包（key → text）：组件不硬编码展示文案，一律按 key 取 */
    copyBundle: {} as Record<string, string>,
    /** 信任区：第一条为主线，其余为可展开示例 */
    trustBlocks: [] as TrustBlockView[],
    banners: [] as BannerView[],
    faqs: [] as FaqView[],
    /** 登录弹窗状态 */
    loginOpen: false,
    loginReason: '',
    /** bootstrap / 身份刷新失败时的错误信息 */
    error: '',
    /** 登录拦截前记录的目标：登录成功后继续 */
    pendingTaskCode: '',
    pendingRoute: '',
  }),

  getters: {
    isLoggedIn: (state) => state.identity.role != null && state.identity.role !== 'guest',
    /**
     * 兜底「直接开聊」入口（前端设计 §4.1：兜底入口常驻，由编排器判定入口）。
     *
     * 判定口径用 `target_stage == null` 而不是写死 `free_chat` 这个 code：
     * 任务入口属动态资源（《AGENTS.md》§8），哪一条是兜底由后端下发决定。
     */
    fallbackTaskEntry: (state) => state.taskEntries.find((entry) => entry.target_stage == null) ?? null,
  },

  actions: {
    /**
     * 加载启动数据。
     *
     * `force=true` 供登录弹窗的「已在其他入口登录？刷新身份」使用：`loaded` 表示
     * "本次会话已经拿到过启动数据"，若沿用缓存，用户在其他入口登录后再点刷新
     * 永远不会重新请求后端，按钮就失去了它唯一的作用。
     */
    async loadBootstrap(force = false) {
      if (this.loaded && !force) return
      if (!inflightBootstrap) {
        inflightBootstrap = this._fetchBootstrap().finally(() => {
          inflightBootstrap = null
        })
      }
      await inflightBootstrap
    },
    async _fetchBootstrap() {
      this.loading = true
      try {
        const data = await getBootstrap()

        this.appName = data.app_name ?? ''
        this.identity = data.identity ?? {}
        this.menus = data.menus ?? []
        this.routes = data.routes ?? []
        this.taskEntries = data.task_entries ?? []
        this.agents = data.agents ?? []
        this.featureFlags = data.feature_flags ?? {}
        this.copyBundle = data.copy_bundle ?? {}
        this.trustBlocks = data.trust_blocks ?? []
        this.banners = data.banners ?? []
        this.faqs = data.faqs ?? []
        this.error = ''
        this.loaded = true
      } catch (error) {
        // 加载失败必须可见：保持空状态并暴露错误，不注入任何演示 bootstrap。
        // 曾经这里会回退到一份内置演示数据，让"后端没起来"看起来像"页面正常"。
        this.error = error instanceof Error ? error.message : '启动数据加载失败'
      } finally {
        this.loading = false
      }
    },
    // 演示 bootstrap 已删除：接口失败时只暴露 error 并保持空状态。
    // 内置演示数据会让"后端没起来"看起来像"页面正常"，本期明确不允许保留。
    openLogin(reason = '') {
      this.loginOpen = true
      this.loginReason = reason
    },
    closeLogin() {
      this.loginOpen = false
    },
  },
})
