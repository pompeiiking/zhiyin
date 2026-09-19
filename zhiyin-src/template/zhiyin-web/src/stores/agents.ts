import { defineStore } from 'pinia'

/**
 * 智能体小队状态（轴 C「能力与编排」的可见投影）。
 *
 * 口径来源：
 * - 名称 / 职责 / 理论包 / 工具 / 边界：`data/registry/agents.json`（能力池，唯一事实来源）；
 * - 负责环节（stageCodes）：与核心对话页右栏管线卡的 stage 同口径（collect/diagnose/decide/act/review）；
 * - 「谁主理哪一环节」：PRD §3.3 智能体能力池；轴 C 对用户只露「当前是谁在帮我、为什么」；
 * - 建档完成阈值（覆盖率 80% 且置信度 ≥ 0.7）：`data/registry/policy_params.json::profile_collection`。
 *
 * ⚠️ 这里**没有对话**：按《前端页面设计》§2.1，实时对话只发生在核心对话页（#screen-conv）。
 *    智能体小队与单智能体页只做能力与边界的可见化。
 *
 * ⚠️ 这里**也没有解析结论**。曾经存在的「15 维演示分数」是展示层臆造：
 *    后端报告只下发维度名 / 标签 / 结论 / 证据，没有任何 0-100 分值，
 *    合成出来的分数会与真实报告互相矛盾。解析结论一律读报告正文。
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

export const useAgentsStore = defineStore('agents', {
  // 本 store 只保留能力池的查询入口。
  // 15 维解析结论**不在这里**：它属于②诊断的真实产出，由报告正文
  // （`GET /app/report/full-text` 的 sections）下发。此前这里有一份按固定分数
  // 合成的"解析结果"，会与后端报告互相矛盾，且是纯粹的展示层臆造数据。
  state: () => ({}),

  getters: {
    agentById: () => (id: string) => agentCatalog.find((agent) => agent.id === id),
  },
})