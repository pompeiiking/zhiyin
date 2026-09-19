import { defineStore } from 'pinia'

import { useConversationStore } from './conversation'

/**
 * 智能体小队状态（轴 C「能力与编排」的可见投影）。
 *
 * 口径来源：
 * - 名称 / 职责 / 理论包 / 工具 / 边界：`data/registry/agents.json`（能力池，唯一事实来源）；
 * - 负责环节（stageCodes）：与核心对话页右栏管线卡的 stage 同口径（collect/diagnose/decide/act/review）；
 * - 「谁主理哪一环节」：PRD §3.3 智能体能力池；轴 C 对用户只露「当前是谁在帮我、为什么」；
 * - 建档完成阈值（覆盖率 80% 且置信度 ≥ 0.7）：`data/registry/policy_params.json::profile_collection`。
 *
 * ⚠️ 第一期前端是界面预览：本文件的智能体卡片、状态与 15 维解析结论**全部是演示数据**
 *    （界面用 MockBadge 标注），不写真实黑板。接口接入后应改为 bootstrap 下发能力池，
 *    解析由 `POST /app/conversation/message` 产出，本文件的演示分数随之删除。
 *
 * ⚠️ 这里**没有对话**：按《前端页面设计》§2.1，实时对话只发生在核心对话页（#screen-conv）。
 *    智能体小队与单智能体页只做能力与边界的可见化，召唤动作见本文件的 `summon`。
 */

/** 智能体在页面上的状态口径（与轴 B 五环节的进度一致，不做「能力展示」用途） */
export type AgentStatusTone = 'done' | 'active' | 'sync' | 'ondemand'

export interface AgentDefinition {
  /** 与 data/registry/agents.json 的 id 一致 */
  id: string
  /** 卡片序号（能力池顺序，非排班） */
  no: string
  name: string
  /** 头像字（取名称首字，避免自造图标） */
  shortName: string
  /** 一句话职责（来自 agents.json role_summary） */
  role: string
  /** 负责环节（PRD §五环） */
  stages: string
  /** 负责环节的 stage 键，与对话页管线卡一致；空数组表示「全环节按需调用」 */
  stageCodes: string[]
  /** 理论包（agents.json theory_packages 的中文标签） */
  theories: string[]
  tools: string[]
  /** 不做什么（agents.json not_to_do） */
  boundary: string
  status: string
  statusTone: AgentStatusTone
  /** 主题色类：每个智能体一个，用于卡片与详情页区分 */
  theme: string
}

export interface AgentDimension {
  name: string
  /** 0–100：越高越好；「决策风险」越低代表风险越高，见 analysisRisk 说明 */
  score: number
}

export interface AnalysisResult {
  /** 15 维逐项得分（演示数据） */
  dimensions: AgentDimension[]
  /** 综合匹配度（由匹配类维度均值算得，不写死） */
  matchScore: number
  /** 结论生成时间（展示用） */
  generatedAt: string
}

export type AnalysisStatus = 'idle' | 'running' | 'done'

/** 15 维名称与口径（与《职引-前端页面设计》引用的解析维度一致） */
export const DIMENSION_NAMES = [
  '专业基础',
  '通用能力',
  '技能匹配',
  '经历证据',
  '兴趣倾向',
  '职业价值观',
  '目标清晰度',
  '岗位认知',
  '行业认知',
  '竞争强度',
  '地域机会',
  '发展潜力',
  '路径可达性',
  '时间窗口',
  '决策风险',
] as const

/** 参与「综合匹配度」计算的匹配类维度 */
const MATCH_DIMENSIONS = [
  '专业基础',
  '通用能力',
  '技能匹配',
  '岗位认知',
  '目标清晰度',
  '地域机会',
  '路径可达性',
]

/** 演示用 15 维得分：与对话页 / 报告页的土木工程 · 结构设计演示画像保持同一套口径 */
const DEMO_SCORES: Record<string, number> = {
  专业基础: 88,
  通用能力: 82,
  技能匹配: 91,
  经历证据: 64,
  兴趣倾向: 62,
  职业价值观: 61,
  目标清晰度: 72,
  岗位认知: 74,
  行业认知: 69,
  竞争强度: 66,
  地域机会: 80,
  发展潜力: 84,
  路径可达性: 86,
  时间窗口: 78,
  决策风险: 42,
}

/** 解析过程（②诊断环节的推理步骤，用于进度呈现） */
export const ANALYSIS_STEPS = [
  { title: '校验画像完整度', detail: '关键字段覆盖与置信度是否达到解析门槛' },
  { title: '拆解 15 个维度', detail: '按匹配、证据、机会、风险四组拆成可比较维度' },
  { title: '交叉比对岗位要求', detail: '对照学职平台岗位要求库逐项比对' },
  { title: '定位差距与机会', detail: '标出待补证据、可用机会与时间窗口' },
  { title: '生成结论与依据', detail: '产出方向建议、依据与风险提示' },
] as const

export const agentCatalog: AgentDefinition[] = [
  {
    id: 'profile_analyst',
    no: '01',
    name: '建档分析师',
    shortName: '建',
    role: '把零散信息沉淀成带置信度与缺口的结构化画像',
    stages: '① 采集建模',
    stageCodes: ['collect'],
    theories: ['帕森斯 · 了解自我', '霍兰德 RIASEC', '能力三核', '舒伯 · 阶段角色', '职业锚 · 价值取向'],
    tools: ['访谈话术', '画像字段 schema', '测评解释'],
    boundary: '不替用户下判断',
    status: '已完成',
    statusTone: 'done',
    theme: 'a-blue',
  },
  {
    id: 'career_advisor',
    no: '02',
    name: '职业顾问',
    shortName: '顾',
    role: '画像与目标要求对齐，给出诊断、差距与可撤回的方向选择',
    stages: '② 诊断 · ③ 决策',
    stageCodes: ['diagnose', 'decide'],
    theories: ['帕森斯 · 匹配', 'CD · 发展状态', '三叶草', 'CASVE 决策循环', '决策平衡单'],
    tools: ['职业库', '岗位要求', '差距算法', '方案生成'],
    boundary: '不替用户执行',
    status: '解析已完成',
    statusTone: 'done',
    theme: 'a-green',
  },
  {
    id: 'path_planner',
    no: '03',
    name: '路径规划师',
    shortName: '规',
    role: '把选择拆成带日历、今天就能勾掉的行动',
    stages: '④ 行动',
    stageCodes: ['act'],
    theories: ['SMART 目标', '执行意图 if-then', '计划性偶发'],
    tools: ['节点日历', '窗口模板', '任务拆解'],
    boundary: '不评判方向对错',
    status: '进行中',
    statusTone: 'active',
    theme: 'a-amber',
  },
  {
    id: 'companion_coach',
    no: '04',
    name: '陪伴教练',
    shortName: '陪',
    role: '盯执行、给反馈、触发再入环',
    stages: '⑤ 复盘 · 主动干预',
    stageCodes: ['review'],
    theories: ['舒伯 · 发展观', '班杜拉 · 自我效能', '计划性偶发'],
    tools: ['行为日志', '节律', '提醒通道', '成就体系'],
    boundary: '不越界代产出诊断或方案',
    status: '持续运行',
    statusTone: 'sync',
    theme: 'a-violet',
  },
  {
    id: 'info_scout',
    no: '05',
    name: '信息侦查员',
    shortName: '侦',
    role: '按需供给外部事实，不参与结论',
    stages: '全环节按需调用',
    stageCodes: [],
    theories: [],
    tools: ['学职平台库', '岗位 JD', '行情', '时间窗口'],
    boundary: '不与用户闲聊、不给建议',
    status: '同步中',
    statusTone: 'sync',
    theme: 'a-slate',
  },
]

function buildDemoAnalysis(): AnalysisResult {
  const dimensions = DIMENSION_NAMES.map((name) => ({ name, score: DEMO_SCORES[name] ?? 60 }))
  const matched = dimensions.filter((item) => MATCH_DIMENSIONS.includes(item.name))
  const matchScore = Math.round(matched.reduce((sum, item) => sum + item.score, 0) / matched.length)
  return { dimensions, matchScore, generatedAt: '刚刚' }
}

let progressTimer: number | undefined

export const useAgentsStore = defineStore('agents', {
  state: () => ({
    /** 解析（②诊断）状态：建档完成后在对话页中栏生成 */
    analysis: null as AnalysisResult | null,
    analysisStatus: 'idle' as AnalysisStatus,
    analysisProgress: 0,
    analysisStepIndex: 0,
  }),

  getters: {
    agentById: () => (id: string) => agentCatalog.find((agent) => agent.id === id),
    /** 解析结论分组：由 15 维得分推导，不在组件里另写一套阈值 */
    analysisGroups: (state) => {
      const dimensions = state.analysis?.dimensions ?? []
      return {
        strong: dimensions.filter((item) => item.score >= 80).map((item) => item.name),
        option: dimensions.filter((item) => item.score >= 70 && item.score < 80).map((item) => item.name),
        gap: dimensions.filter((item) => item.score >= 60 && item.score < 70).map((item) => item.name),
        risk: dimensions.filter((item) => item.score < 60).map((item) => item.name),
      }
    },
  },

  actions: {
    /**
     * 无副作用的演示初始化：报告页 / 智能体页直接读 15 维结论时，若尚未生成则补一份演示值。
     * 与 `startAnalysis` 区分——这里不改对话页的交接告知与管线状态，只保证结论可读。
     */
    ensureDemoAnalysis() {
      if (this.analysis) return
      this.analysis = buildDemoAnalysis()
      this.analysisStatus = 'done'
      this.analysisProgress = 100
      this.analysisStepIndex = ANALYSIS_STEPS.length - 1
    },
    /** 建档完成 → 生成 15 维解析，并把「换主理」写进对话页的显式告知行 */
    startAnalysis() {
      if (this.analysisStatus === 'running') return
      this.analysisStatus = 'running'
      this.analysisProgress = 0
      this.analysisStepIndex = 0
      window.clearInterval(progressTimer)
      progressTimer = window.setInterval(() => {
        if (this.analysisProgress >= 96) return
        this.analysisProgress = Math.min(96, this.analysisProgress + (this.analysisProgress < 70 ? 3 : 1))
        const index = ANALYSIS_STEPS.findIndex((_step, stepIndex) => {
          const end = ((stepIndex + 1) / ANALYSIS_STEPS.length) * 100
          return this.analysisProgress <= end
        })
        this.analysisStepIndex = index === -1 ? ANALYSIS_STEPS.length - 1 : index
      }, 90)
      window.setTimeout(() => {
        window.clearInterval(progressTimer)
        progressTimer = undefined
        this.analysis = buildDemoAnalysis()
        this.analysisProgress = 100
        this.analysisStepIndex = ANALYSIS_STEPS.length - 1
        this.analysisStatus = 'done'
        const conversation = useConversationStore()
        conversation.disclosure = {
          message: '主理由「建档分析师」交接给「职业顾问」：画像已达解析门槛，②诊断已产出 15 维解析。',
        }
        // 右栏管线同步前进：② 落产出，③ 等待用户确认方向（不自动替用户做决策）
        const pipeline = conversation.pipeline as Array<Record<string, unknown>>
        if (pipeline.length >= 3) {
          pipeline[1] = {
            ...pipeline[1],
            status: 'done',
            active: false,
            current_output: { 解析结果: '15 维已完成', 综合匹配: `${this.analysis?.matchScore ?? 0}%` },
          }
          pipeline[2] = { ...pipeline[2], active: true }
        }
      }, 1800)
    },

    /**
     * 召唤某位智能体接手当前微循环（单智能体页 / 智能体小队的唯一「动作」）。
     *
     * 只做两件事：换主理徽章 + 写换主理显式告知行（§2.3 第 2 条）。
     * 不产生新资产、不改结论、不在这里发起对话——跳转由页面负责（回核心对话页）。
     */
    summon(id: string) {
      const agent = agentCatalog.find((item) => item.id === id)
      if (!agent) return
      const conversation = useConversationStore()
      conversation.badge = {
        name: agent.name,
        role_summary: `${agent.role} · 负责${agent.stages}`,
        theory_refs: agent.theories.map((name) => ({ name })),
      }
      conversation.disclosure = {
        message: `以下由「${agent.name}」接手，负责${agent.stages}；依据${
          agent.theories.length ? agent.theories.slice(0, 3).join(' / ') : '外部事实供给（只给事实，不参与结论）'
        }。结论仍写回同一份画像与资产，不另起一套。`,
      }
    },

    /** 关闭演示：解析回到未生成，告知行一并撤下（不留下与状态不符的文案） */
    resetAnalysis() {
      window.clearInterval(progressTimer)
      progressTimer = undefined
      this.analysis = null
      this.analysisStatus = 'idle'
      this.analysisProgress = 0
      this.analysisStepIndex = 0
    },
  },
})