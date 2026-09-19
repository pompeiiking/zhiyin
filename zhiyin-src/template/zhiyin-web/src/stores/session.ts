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
import { agentCatalog } from './agents'

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
        console.error('bootstrap 加载失败，回退到演示数据', error)
        this._applyDemoBootstrap()
      } finally {
        this.loading = false
      }
    },
    /**
     * 无后端时的演示 bootstrap：内容与 data/registry/*.json 同值（第一期为只读界面演示）。
     *
     * 只在本方法里兜底，不写进真实数据源；`preview=true` 会让首页信任区与任务入口
     * 明确标注「演示数据」，且任务点击走只读提示而非请求后端。后端接入后这段不再触发。
     */
    _applyDemoBootstrap() {
      const leadAgentNames = new Map(agentCatalog.map((agent) => [agent.id, agent.name]))

      this.appName = '职引'
      this.identity = { nickname: '演示用户', role: 'guest', avatar: '' }
      this.preview = true

      this.menus = [
        { key: 'home', label: '首页', route: '/', visible: true, sort_order: 1 },
        { key: 'conversation', label: '核心对话页', route: '/conv', visible: true, sort_order: 2 },
        { key: 'workspace', label: '智能工作台', route: '/wb', visible: true, sort_order: 3 },
        { key: 'report', label: '完整报告页', route: '/report', visible: true, sort_order: 4 },
      ] as MenuView[]

      this.routes = [
        { page_code: 'screen-home', path: '/', require_login: false, sort_order: 1 },
        { page_code: 'screen-auth', path: '/auth', require_login: false, sort_order: 2 },
        { page_code: 'screen-conv', path: '/conv', require_login: false, sort_order: 3 },
        { page_code: 'screen-agents', path: '/agents', require_login: false, sort_order: 4 },
        { page_code: 'screen-subagent', path: '/agents/:agentId', require_login: false, sort_order: 5 },
        { page_code: 'screen-wb', path: '/wb', require_login: true, sort_order: 6 },
        { page_code: 'screen-report', path: '/report', require_login: true, sort_order: 7 },
      ] as RouteView[]

      this.taskEntries = [
        { code: 'confused', label: '还不太清楚自己适合什么', target_stage: 'collect', lead_agent_name: leadAgentNames.get('profile_analyst'), sort_order: 1 },
        { code: 'verify_direction', label: '想验证某方向行不行', target_stage: 'diagnose', lead_agent_name: leadAgentNames.get('career_advisor'), sort_order: 2 },
        { code: 'undecided', label: '几个方向拿不准', target_stage: 'decide', lead_agent_name: leadAgentNames.get('career_advisor'), sort_order: 3 },
        { code: 'how_to_act', label: '定了方向不知道怎么动', target_stage: 'act', lead_agent_name: leadAgentNames.get('path_planner'), sort_order: 4 },
        { code: 'stuck', label: '执行卡住了 / 没进展', target_stage: 'review', lead_agent_name: leadAgentNames.get('companion_coach'), sort_order: 5 },
        { code: 'review_due', label: '好久没管了 / 该复盘了', target_stage: 'review', lead_agent_name: leadAgentNames.get('companion_coach'), sort_order: 6 },
        { code: 'free_chat', label: '直接开聊', target_stage: null, lead_agent_name: null, sort_order: 7 },
      ] as TaskEntryView[]

      this.featureFlags = {
        report_full_text: true,
        export: false,
        calendar: true,
        achievements: true,
        mentor: false,
        demo: true,
      }

      this.copyBundle = {
        'app.name': '职引',
        'home.tagline': '用自己的话说清困惑，一步一步把方向走出来',
        'home.task_group_title': '你现在最想解决的是哪件事？',
        'conv.pipeline_title': '微循环管线',
        'wb.title': '智能工作台',
        'report.export_label': '导出',
        'demo.data_notice': '以下为演示数据，仅用于展示流程',
        'mock.source_notice': '本期为 Mock 产出，未接真实模型',
      }

      this.trustBlocks = [
        {
          code: 'primary_methodology',
          title: '你做的每一步，都基于职业咨询的成熟方法',
          body: '采集、诊断、决策、行动、复盘五步背后都有可查的咨询理论支撑，点开可以看到具体用了什么。',
          expandable_ref: 'methodology_example',
        },
        {
          code: 'methodology_example',
          title: '看一个方法论示例（脱敏）',
          body: '用一份脱敏的示例报告说明每一步分别用了哪套方法、产出了什么。',
          expandable_ref: 'demo_report',
        },
      ] as TrustBlockView[]

      this.banners = [
        {
          code: 'demo_entry',
          title: '先看一遍完整流程',
          body: '用脱敏演示数据走完首页 → 对话 → 工作台，不写真实黑板',
          action_label: '查看示例',
          action_route: '/wb',
        },
      ] as BannerView[]

      this.faqs = [
        { code: 'how_to_start', question: '我该从哪里开始？', answer: '从首页选一句最像你现在的处境的话，系统会判断该进哪个环节，并派对应的主理智能体先问你一个问题。' },
        { code: 'data_safety', question: '我填的信息会被怎么用？', answer: '本期只使用演示与脱敏数据，不接收真实手机号、简历等敏感信息；画像与行为数据仅用于生成你自己的报告、方案与计划。' },
        { code: 'can_resume', question: '中途退出会丢进度吗？', answer: '不会。每个任务会话记录当前环节与已产出资产，下次进入会从当前环节续接，不重复问已经确认过的信息。' },
        { code: 'why_handoff', question: '为什么有时候换了一个人在回答？', answer: '环节变化时主理会交接，产品规定换主理必须显式告知：你会先看到一行说明，讲清是谁接手、依据哪套方法、为什么。' },
      ] as FaqView[]

      this.loaded = true
      this.error = ''
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
