import { defineStore } from 'pinia'

import type {
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
    /** 只读演示模式（暂未接入演示入口，默认关闭） */
    preview: false,
    /** 登录拦截前记录的目标：登录成功后继续 */
    pendingTaskCode: '',
    pendingRoute: '',
  }),

  getters: {
    isLoggedIn: (state) => state.identity.role != null && state.identity.role !== 'guest',
  },

  actions: {
    async loadBootstrap() {
      if (this.loaded) return
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
        this.featureFlags = data.feature_flags ?? {}
        this.copyBundle = data.copy_bundle ?? {}
        this.trustBlocks = data.trust_blocks ?? []
        this.banners = data.banners ?? []
        this.faqs = data.faqs ?? []
        this.error = ''
        this.loaded = true
      } catch (error) {
        this.error = error instanceof Error ? error.message : '启动数据加载失败'
        console.error('bootstrap 加载失败', error)
      } finally {
        this.loading = false
      }
    },
    openLogin(reason = '') {
      this.loginOpen = true
      this.loginReason = reason
    },
    closeLogin() {
      this.loginOpen = false
    },
  },
})
