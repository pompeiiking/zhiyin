import { defineStore } from 'pinia'

import type { ConversationTurnView, SessionListView } from '@/api/schema'
import { enterTask as enterTaskApi, listSessions, sendMessage } from '@/api/endpoints'

/**
 * 核心对话页状态（#screen-conv 三栏）。
 *
 * 三栏口径（前端设计文档 §4.2）：
 *   左栏 sessions    —— 并行任务会话（按"任务/环节"命名，不按 agent 名排布）
 *   中栏 turns       —— 当前主理对话 + 显式告知 + 行为引导
 *   右栏 pipeline    —— ①-⑤ 三态管线卡
 */
export const useConversationStore = defineStore('conversation', {
  state: () => ({
    // ⚠️ 临时演示数据（看完请还原为空数组 / null）：让空壳对话页有内容可看，非真实数据
    sessions: [
      { task_id: 'demo-task', task_name: '校招求职 · 找到适合我的方向', stage_label: '诊断环节', progress: 0.62 },
    ] as Array<Record<string, unknown>>,
    currentTaskId: 'demo-task' as string | null,
    turns: [
      { role: 'agent', content: '先问「学业」——你的学校、专业、年级和成绩排名是？', theory: { name: '帕森斯 · 了解自我', def: '把人（特质）与职业（要求）逐项匹配，先弄清「你是谁」再谈「适合什么」。', source: '1909 帕森斯特质因素理论' } },
      { role: 'user', content: '沈阳建筑大学，土木工程，大四，GPA 3.2，前 30%。' },
      { role: 'agent', content: '收到，已沉淀到「学业」维度。再聊聊你上手能用的工具和软件？', theory: { name: '能力三核 · 技能盘点', def: '把能力拆成知识、技能、才干三层，盘点你「上手能用的」与「还没被发现的」。', source: '新精英能力三核模型' } },
      { role: 'user', content: 'AutoCAD、PKPM、YJK 都熟练，做过两个课程设计。' },
      { role: 'agent', content: '很好，结构设计岗很看重这几项。你已经偏向「结构方向」，我们继续确认兴趣与价值观。', theory: { name: '霍兰德 · 职业兴趣', def: '用现实、研究、艺术、社会、企业、常规六类兴趣为偏好编码，找契合职业群。', source: '霍兰德职业兴趣理论' } },
      { role: 'agent', content: '诊断结论：主攻方向建议「结构设计」，备选「施工管理」。完整 15 维解析与证据已生成到右栏报告。', long: true, theory: { name: '能力三核 · 技能盘点', def: '把能力拆成知识、技能、才干三层。', source: '新精英能力三核模型' } },
      { role: 'coach', content: '你已经连续聊了 12 分钟，建议先保存当前进度，明天继续完善「职业兴趣」这一项。', action: '保存并收尾' },
    ] as Array<Record<string, unknown>>,
    pipeline: [
      { stage: 'collect', title: '采集 · 建立画像', status: 'done', active: false, current_output: { '覆盖度': '4 / 6', '已记录': '学业 / 技能 / 经历' }, theory_models: [{ name: '帕森斯', def: '把人（特质）与职业（要求）逐项匹配。', source: '1909 特质因素理论' }] },
      { stage: 'diagnose', title: '诊断 · 15 维解析', status: 'in_progress', active: true, current_output: { '当前进度': '进行 15 维逐项比对' }, theory_models: [{ name: '能力三核', def: '把能力拆成知识、技能、才干三层。', source: '能力三核模型' }] },
      { stage: 'decide', title: '决策 · 方向方案', status: 'empty', active: false },
      { stage: 'act', title: '行动 · 关键节点', status: 'empty', active: false },
      { stage: 'review', title: '复盘 · 持续校准', status: 'empty', active: false },
    ] as Array<Record<string, unknown>>,
    /** 顶部主理徽章：现在是谁在帮我、依据什么 */
    badge: { name: '职业顾问', role_summary: '建档分析师协作中 · 围绕同一份画像', theory_refs: [{ name: '帕森斯', def: '把人（特质）与职业（要求）逐项匹配。', source: '1909 特质因素理论' }, { name: '能力三核', def: '把能力拆成知识、技能、才干三层。', source: '能力三核模型' }] } as Record<string, unknown>,
    /** 右栏画像字段卡（ProfilePanelView）：层次化属性卡的演示数据 */
    profile: {
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
    } as Record<string, unknown>,
    /** 换主理 / 换理论 / 结论变化时的显式告知行（演示阶段不显示，真实换主理时才渲染） */
    disclosure: null as Record<string, unknown> | null,
    /** 行为引导（四选一），必须渲染出对应可点元素 */
    guide: { type: 'options', text: '先说说你在职业里最在意的三件事', options: ['薪资与成长空间', '工作生活平衡', '兴趣匹配与成就感'] } as Record<string, unknown> | null,
  }),

  actions: {
    /** 拉取左栏会话列表；后端未接入时保留演示数据，不抛错。 */
    async loadSessions() {
      try {
        const data = (await listSessions()) as SessionListView
        const sessions = (data.sessions ?? []).map((s) => ({ ...s }))
        if (sessions.length) {
          this.sessions = sessions
          this.currentTaskId = data.current_task_id ?? this.currentTaskId ?? sessions[0].task_id
        }
      } catch (error) {
        console.warn('会话列表加载失败，保留演示数据', error)
      }
    },

    /** 从任务入口进入微循环：写入会话并切换到当前任务（页面跳转由调用方处理）。 */
    async enterTask(taskCode: string) {
      const task = await enterTaskApi(taskCode)
      if (!task?.task_id) throw new Error('Missing task')
      const index = this.sessions.findIndex((s) => s.task_id === task.task_id)
      if (index < 0) this.sessions.push(task)
      else this.sessions[index] = task
      this.currentTaskId = task.task_id
      return task
    },

    /** 发送一轮用户消息，把返回的最短结论 / 告知 / 行为引导 / 管线卡写回三栏。 */
    async send(message: string) {
      if (!this.currentTaskId) throw new Error('缺少当前任务')
      this.turns.push({ role: 'user', content: message })
      const turn = await sendMessage(this.currentTaskId, message)
      this.applyTurn(turn)
      return turn
    },

    /** 环节判定不确定（ErrorCode 1006）：渲染澄清追问，不当作错误。 */
    applyStageUncertain(clarifyQuestion: string) {
      this.disclosure = { message: clarifyQuestion } as Record<string, unknown>
    },

    /** 把一轮 ConversationTurnView 落地到中栏 turns + 右栏 pipeline + 顶栏徽章。 */
    applyTurn(turn: ConversationTurnView) {
      for (const message of turn.messages ?? []) {
        this.turns.push({
          role: message.role,
          content: message.text,
          theory: message.theory_refs?.[0] ?? null,
        })
      }
      if (turn.badge) this.badge = turn.badge as unknown as Record<string, unknown>
      if (turn.pipeline_cards) {
        this.pipeline = turn.pipeline_cards as unknown as Array<Record<string, unknown>>
      }
      this.disclosure = (turn.disclosure as unknown as Record<string, unknown> | null) ?? null
      this.guide = (turn.guide as unknown as Record<string, unknown> | null) ?? null
    },
  },
})
