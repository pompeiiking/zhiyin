import { defineStore } from 'pinia'
import { getWorkspace } from '@/api/endpoints'

/**
 * 智能工作台状态（#screen-wb，按 ①-⑤ 分层聚合）。
 *
 * 工作台不做实时对话，只展示"活资产"（前端设计文档 §4.3）。
 * 折叠状态 `collapsed` 在页面往返后保留，不随路由切换重置。
 */
export const useWorkspaceStore = defineStore('workspace', {
  state: () => ({
    loaded: false,
    error: '',
    /** 轴 A 阶段定位：系统推断的用户职业发展进程（隐性），前台只展示、可纠正，不做导航层级 */
    axisAStage: '冲刺行动期',
    axisABasis: '近 14 天完成 3 项行动任务，画像覆盖度 67%，整体置信度 78%',
    /** 轴 C 能力池：主理 / 协理 / 信息侦查员（点开为能力详情，不各自独占页面） */
    agents: [
      { id: 'career_advisor', name: '职业顾问', kind: '主理', summary: '诊断匹配 · 方向验证' },
      { id: 'profile_analyst', name: '建档分析师', kind: '协理', summary: '画像采集与补充' },
      { id: 'info_scout', name: '信息侦查员', kind: '按需调用', summary: '岗位与行情事实供给' },
    ] as Array<Record<string, unknown>>,
    // ⚠️ 临时演示数据（看完请还原为空）：让空壳工作台有内容可看，非真实数据
    profilePanel: {
      coverage: 0.67,
      overall_confidence: 0.78,
      updated_at: '今天 10:24',
      fields: [
        { group: '学业', name: '学校', value: '沈阳建筑大学', status: 'done' },
        { group: '学业', name: '专业', value: '土木工程', status: 'done' },
        { group: '学业', name: '年级', value: '大四', status: 'done' },
        { group: '学业', name: '成绩排名', value: '前 30%', status: 'done' },
        { group: '技能', name: '熟练工具', value: 'AutoCAD / PKPM / YJK', status: 'done' },
        { group: '技能', name: '课程设计', value: '2 个', status: 'done' },
        { group: '兴趣', name: '职业兴趣', value: '待采集', status: 'pending' },
        { group: '价值观', name: '价值排序', value: '待采集', status: 'pending' },
      ],
      gaps: [{ name: '职业兴趣' }, { name: '价值排序' }],
    } as Record<string, unknown> | null,
    reportPanel: {
      stage: 'diagnose',
      title: '诊断 · 15 维解析',
      version: 2,
      updated_at: '今天 11:02',
      evaluation: '主攻「结构设计」匹配度 82% · 备选「施工管理」',
      theory_models: [
        { name: '能力三核', abbr: '知识·技能·才干', def: '把能力拆成知识、技能、才干三层，区分「补得到」与「要换方向」。', source: '能力三核模型' },
        { name: '霍兰德', abbr: 'RIASEC', def: '用现实、研究、艺术、社会、企业、常规六类兴趣为偏好编码，找契合职业群。', source: '霍兰德职业兴趣理论' },
      ],
      diff: '因更新了「职业兴趣」维度，v1 → v2 匹配度从 76% 调整为 82%。',
    } as Record<string, unknown> | null,
    planPanel: {
      stage: 'decide',
      title: '决策 · 方向方案',
      version: 1,
      updated_at: '今天 11:20',
      evaluation: '主攻「结构设计」· 平行「施工管理」· 保底「BIM 建模」',
      theory_models: [
        { name: '决策平衡单', abbr: 'Decision Balance', def: '把每个选项在各维度上的得失摆出来，让取舍显性化。', source: '决策平衡单工具' },
      ],
      diff: null,
    } as Record<string, unknown> | null,
    actionPanel: {
      stage: 'act',
      title: '行动 · 关键节点',
      version: 1,
      updated_at: '今天 11:40',
      evaluation: '3 / 7 项任务已完成 · 下一个节点：9 月网申',
      theory_models: [
        { name: 'SMART 目标', abbr: 'SMART', def: '目标要具体、可衡量、可达成、有相关性、有时限。', source: '目标管理理论' },
      ],
      diff: null,
    } as Record<string, unknown> | null,
    reviewPanel: {
      stage: 'review',
      title: '复盘 · 持续校准',
      version: 1,
      updated_at: '昨天 20:15',
      evaluation: '本周已完成 1 次复盘 · 1 条提醒待处理',
      theory_models: [
        { name: '克朗波兹', abbr: '计划性偶发', def: '意外机会不是噪声，可以被有准备的人利用。', source: '生涯混沌论' },
      ],
      diff: null,
    } as Record<string, unknown> | null,
    coachMessages: [
      { reason: '停滞提醒', text: '你已 3 天未更新画像，把「职业兴趣」补上能让诊断更准。', action: '去补兴趣' },
      { reason: '节点提醒', text: '距离「结构设计岗」网申还有 7 天，建议先确认目标公司清单。', action: '查看节点' },
      { reason: '复盘邀请', text: '本周该做一次方向复盘，回顾进展并校准下一步。', action: '开始复盘' },
    ] as Array<Record<string, unknown>>,
    dependencies: [
      { from_asset: '个人画像', to_asset: '诊断报告', via_profile_keys: ['职业兴趣'] },
      { from_asset: '诊断报告', to_asset: '方向方案', via_profile_keys: ['匹配度'] },
      { from_asset: '方向方案', to_asset: '行动计划', via_profile_keys: ['目标方向'] },
      { from_asset: '行动计划', to_asset: '行为日志', via_profile_keys: [] },
    ] as Array<Record<string, unknown>>,
    /** 功能块入口与静态数据：报告全文 / 导出 / 日历 / 成就 / 导师 / 演示 */
    blocks: {} as Record<string, unknown>,
    /** 各层折叠状态，页面往返后保留 */
    collapsed: {} as Record<string, boolean>,
  }),

  actions: {
    async load() {
      if (this.loaded) return
      this.loaded = true
      try {
        const data = await getWorkspace()
        this.axisAStage = data.axis_a_stage ?? this.axisAStage
        this.profilePanel = (data.profile_panel as unknown as Record<string, unknown>) ?? this.profilePanel
        this.reportPanel = (data.report_panel as unknown as Record<string, unknown>) ?? this.reportPanel
        this.planPanel = (data.plan_panel as unknown as Record<string, unknown>) ?? this.planPanel
        this.actionPanel = (data.action_panel as unknown as Record<string, unknown>) ?? this.actionPanel
        this.reviewPanel = (data.review_panel as unknown as Record<string, unknown>) ?? this.reviewPanel
        this.coachMessages = (data.coach_messages as unknown as Array<Record<string, unknown>>) ?? this.coachMessages
        this.dependencies = (data.dependencies as unknown as Array<Record<string, unknown>>) ?? this.dependencies
        this.blocks = (data.blocks as unknown as Record<string, unknown>) ?? this.blocks
        this.error = ''
      } catch (err) {
        // 后端 Facade 未接入时保留演示数据，页面仍可评审；不静默伪装成已接真实数据。
        this.error = err instanceof Error ? err.message : '工作台加载失败'
        console.warn('工作台聚合视图加载失败，保留演示数据', err)
      }
    },
    toggleStage(stage: string) {
      this.collapsed[stage] = !this.collapsed[stage]
    },
  },
})
