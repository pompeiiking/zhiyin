import { computed, type ComputedRef } from 'vue'

import { useSessionStore } from './session'

/**
 * 智能体小队（轴 C「能力与编排」的可见投影）。
 *
 * 口径来源（**唯一事实来源是后端 bootstrap**）：
 * - 名称 / 职责 / 理论包 / 工具 / 边界：`data/registry/agents.json`，
 *   由 `GET /app/bootstrap` 的 `agents` 下发（待决问题 D9）；
 * - 负责环节（`stageCodes`）：由后端用 `(agent_id, stage)` 的产出契约反推后下发，
 *   与核心对话页右栏管线卡同口径；空数组表示「全环节按需调用」；
 * - 环节中文名：文案包 `copies.json::stage.<code>.label`（**不在前端拼中文**）；
 * - 不主理任何环节时的说明：文案包 `agent.stage.none`。
 *
 * ⚠️ 这里**曾经硬编码**了五位智能体的完整定义，与 `agents.json` 靠人工保持一致。
 *    那违反《AGENTS.md》§8（智能体属动态资源，不得硬编码进 Vue/TS），而且两边
 *    一旦漂移没有任何守卫会红。现在整份定义来自 bootstrap，前端只派生展示字段。
 *
 * ⚠️ 这里**没有对话**：按《前端页面设计》§2.1，实时对话只发生在核心对话页。
 *    这里也**没有解析结论**：15 维结论文由报告正文下发。
 */
export interface AgentDefinition {
  /** 与 data/registry/agents.json 的 id 一致 */
  id: string
  /** 卡片序号（能力池顺序，非排班） */
  no: string
  name: string
  /** 头像字（取名称首字，避免自造图标） */
  shortName: string
  /** 一句话职责（bootstrap `agents[].role_summary`） */
  role: string
  /** 负责环节的中文名（文案包拼接）；不主理任何环节时为 `agent.stage.none` */
  stages: string
  /** 负责环节的 stage 键，与对话页管线卡一致；空数组表示「全环节按需调用」 */
  stageCodes: string[]
  /** 理论包中文名（后端已把理论卡 id 翻译好） */
  theories: string[]
  tools: string[]
  /** 不做什么（bootstrap `agents[].not_to_do`） */
  boundary: string
  /** 主题色类：契约不下发展示字段，前端按下标派生 */
  theme: string
}

/**
 * 卡片主题色。**刻意由前端按下标分配**：它是纯展示属性（决定卡片配色），
 * 不进契约——把配色写进动态资源只会让"改了 JSON 却看不到变化"更难排查。
 * 顺序固定，保证同一个智能体每次拿到的颜色一致。
 */
const THEMES = ['a-blue', 'a-green', 'a-amber', 'a-violet', 'a-slate']

/**
 * 能力池：由 bootstrap 的 `agents` 派生展示字段。
 *
 * 后端未下发（bootstrap 失败或旧后端）时返回空数组——**不回落到内置清单**：
 * 回落会让"接口没接通"看起来像"能力池正常"，正是本期要清掉的那类假象。
 */
export function useAgentCatalog(): ComputedRef<AgentDefinition[]> {
  const session = useSessionStore()
  return computed(() =>
    (session.agents ?? []).map((agent, index) => {
      const stageCodes = (agent.stages ?? []) as string[]
      const labels = stageCodes.map(
        (code) => session.copyBundle[`stage.${code}.label`] ?? code,
      )
      return {
        id: agent.id,
        no: String(index + 1).padStart(2, '0'),
        name: agent.name,
        shortName: agent.name.slice(0, 1),
        role: agent.role_summary ?? '',
        stages: labels.length
          ? labels.join(' · ')
          : (session.copyBundle['agent.stage.none'] ?? ''),
        stageCodes,
        theories: (agent.theories ?? []).map((theory) => theory.name),
        tools: agent.tools ?? [],
        boundary: (agent.not_to_do ?? []).join('、'),
        theme: THEMES[index % THEMES.length],
      }
    }),
  )
}

/** 按 id 取单个智能体；取不到返回 undefined（调用方按"没有这个智能体"处理）。 */
export function useAgentById(): (id: string) => AgentDefinition | undefined {
  const catalog = useAgentCatalog()
  return (id: string) => catalog.value.find((agent) => agent.id === id)
}
